#!/usr/bin/env python3
"""TESSERACT lesson executor — deterministic, 0 model calls.

Loads a lesson from fleet/lessons.json and turns it into Blue moves
against the REAL engine (engine.Sandbox), so "the whole fleet loads the
rules" is a code path, not a narrative claim.

Two phases, in order:

  Phase A — opening recipe. The executor emits the lesson's
  ``opening_recipe`` steps verbatim, one per Blue tick, in ``step`` order.
  In a sequential 8-round duel the Blue phase is exactly 8 ticks, so the
  full 8-step recipe lands in order regardless of winner.

  Phase B — reactive rules (only after the recipe is exhausted).
  Trigger logic derived from the lesson's de-ticked rules (rule IDs in
  comments; the lesson file is asserted to contain R1-R7 so a schema
  change fails loudly instead of silently drifting):
    R6  flag held + >=1 detection + L4 open  -> isolate L4 (blocks the
        terminal move: exfiltration inside-out, infiltration outside-in.
        The executor reads engine state only, never any run label, so
        the same rules execute in both modes.)
    R1  policy lax                           -> set strict
    R2  trust >= 55 (one lax message from breach) -> brief overseer
    R3  no trap planted                      -> plant trap on "flag"
    R4/R5  weakest strength layer below cap  -> patch it (delays only)
    else                                     -> wait

What this is NOT: it never calls a model, never changes weights, never
invents moves. Every move it emits is a legal engine action, resolved by
engine.Sandbox.apply_blue. A single briefed agent applies a lesson
unreliably (score 1-1); this executor applies it mechanically — that
contrast is the product thesis, and the binding line says so.

Usage from run_duel.py: ``--blue-mode lesson-executor``.
Usage from swarm.py: ``apply_recipe(sb, lesson)`` for pretrained /
sequential replays, ``LessonExecutor(lesson)`` for reactive Blue ticks.
Usage from experiments/ablations.py: ``LessonExecutor(lesson, ...)``
with U10 ablation switches (experiments only; defaults equal full
lesson execution, so swarm.py default reports and payout inputs are
unchanged).

U9 trap-state invariant: the executor tracks the engine's single trap
slot as EMPTY or ARMED(trigger) via trap_state() — a read-only read of
the existing Sandbox.detection_trap field, so no engine rule changes.
Every set_trap goes through one choke point, _trap_or_skip(): a trap
step reached while ARMED emits the existing wait/no-op move with
rationale metadata executor_skip="trap_already_armed" and records one
skip, preserving the armed trigger. The slot returns to EMPTY only when
the engine itself fires/consumes the trap (Sandbox.check_trap sets
detection_trap to None). A second set_trap while armed is impossible
through executor code paths (Phase A recipe step, Phase B flag
reaction, and apply_recipe alike), independent of lesson wording.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_LESSON = os.path.join(HERE, "lessons.json")

# Trust margin: one lax overseer message adds +25. Briefing at >= 55 keeps
# the overseer at least one message away from the 75 breach line.
BRIEF_THRESHOLD = 55

# Rationale metadata on a wait/no-op emitted because a trap step was
# reached while a trap was already armed. Counted by
# experiments/scoreboard.py as executor_trap_skips.
TRAP_SKIP_REASON = "trap_already_armed"
SKIP_ARG = "executor_skip"


def trap_state(sb):
    """Read-only exposure of the engine's single trap slot.

    Returns ("EMPTY", None) when no trap is planted, else
    ("ARMED", trigger). Reads the existing Sandbox.detection_trap field;
    it changes no engine rule and writes nothing.
    """
    trigger = sb.detection_trap
    if trigger is None:
        return ("EMPTY", None)
    return ("ARMED", trigger)


def load_lesson(path=None):
    """Load a lesson file and validate its shape. Returns the dict."""
    path = path or DEFAULT_LESSON
    with open(path, "r", encoding="utf-8") as f:
        lesson = json.load(f)
    recipe = lesson.get("opening_recipe")
    if not isinstance(recipe, list) or not recipe:
        raise ValueError(f"lesson {path} has no opening_recipe")
    for step in recipe:
        if "action" not in step:
            raise ValueError(f"lesson {path} recipe step missing action: {step!r}")
    rule_ids = {str(r.get("id", "")) for r in lesson.get("rules", [])}
    missing = {f"R{i}" for i in range(1, 8)} - rule_ids
    if missing:
        raise ValueError(
            f"lesson {path} is missing rule(s) {sorted(missing)}; "
            "refusing to execute a drifted lesson"
        )
    return lesson


def recipe_moves(lesson):
    """Opening recipe as [(action, args), ...] in step order, verbatim."""
    steps = sorted(lesson["opening_recipe"], key=lambda s: s.get("step", 0))
    return [(s["action"], dict(s.get("args") or {})) for s in steps]


class LessonExecutor:
    """Deterministic Blue move source for one duel.

    U10 ablation switches (experiments only; every default equals full
    lesson execution, so default construction behaves exactly as
    before and fleet/swarm.py default reports and payout inputs are
    unchanged):
      disable_strict: never set strict (Phase A strict step and Phase B
        R1 become plain waits; other rules still run).
      disable_brief: never brief (Phase A brief steps and Phase B R2
        become plain waits).
      disable_trap: never plant a trap (Phase A trap steps and Phase B
        R3 fall through to patch/wait; emits plain waits, never trap
        skip metadata).
      disable_patch_rotate: never patch or rotate (Phase A patch/rotate
        steps and Phase B R4/R5 become plain waits).
      phase_a_order: "normal" (recipe in step order) or "reversed".
    A disabled Phase A step is consumed and emits ("wait", {}) so tick
    alignment across arms is preserved. Isolation (R6) has no switch
    and always stays enabled when legal.
    """

    def __init__(self, lesson=None, lesson_path=None,
                 disable_strict=False, disable_brief=False,
                 disable_trap=False, disable_patch_rotate=False,
                 phase_a_order="normal"):
        if phase_a_order not in ("normal", "reversed"):
            raise ValueError(
                f"phase_a_order must be 'normal' or 'reversed', "
                f"got {phase_a_order!r}"
            )
        self.lesson = lesson if lesson is not None else load_lesson(lesson_path)
        self.recipe = recipe_moves(self.lesson)
        if phase_a_order == "reversed":
            self.recipe = list(reversed(self.recipe))
        self.phase_a_order = phase_a_order
        self.disable_strict = bool(disable_strict)
        self.disable_brief = bool(disable_brief)
        self.disable_trap = bool(disable_trap)
        self.disable_patch_rotate = bool(disable_patch_rotate)
        self.index = 0
        # One entry per blocked set_trap attempt: {"tick", "phase",
        # "armed_trigger", "executor_skip"}. Phase is "A" (recipe step)
        # or "B" (flag reaction).
        self.skips = []

    def reset(self):
        self.index = 0
        self.skips = []

    def _phase_a_disabled(self, action, args):
        """True when a Phase A recipe step's category is ablated away."""
        args = args or {}
        if (action == "set_overseer_policy"
                and args.get("policy") == "strict"):
            return self.disable_strict
        if action == "brief_overseer":
            return self.disable_brief
        if action == "add_detection":
            return self.disable_trap
        if action in ("patch_rule", "rotate_creds"):
            return self.disable_patch_rotate
        return False

    def _trap_or_skip(self, sb, keyword, phase):
        """Single choke point for every executor set_trap (U9 invariant).

        Plants ("add_detection", keyword) only when the slot is EMPTY.
        While ARMED, emits the existing wait/no-op with rationale
        metadata executor_skip="trap_already_armed" and records one
        skip, preserving the armed trigger. A second set_trap while
        armed is impossible through this path, not merely unlikely.
        """
        state, armed_trigger = trap_state(sb)
        if state == "ARMED":
            self.skips.append({
                "tick": sb.tick,
                "phase": phase,
                "armed_trigger": armed_trigger,
                SKIP_ARG: TRAP_SKIP_REASON,
            })
            return ("wait", {SKIP_ARG: TRAP_SKIP_REASON})
        return ("add_detection", {"keyword": keyword})

    def reactive_move(self, sb):
        """One post-recipe move from live engine state (see module docstring)."""
        if sb.winner:
            return ("wait", {})
        layers = sb.layers
        # R6: exfil is imminent — flag held, evidence on record, channel open.
        # No ablation switch covers isolation; it stays enabled when legal.
        if ("flag" in sb.red_inventory and sb.detections >= 1
                and not layers[4]["isolated"]):
            return ("isolate_layer", {"layer": 4})
        # R1: strict first (fallback if the recipe never ran or policy reset).
        if sb.overseer["policy"] != "strict" and not self.disable_strict:
            return ("set_overseer_policy", {"policy": "strict"})
        # R2: keep trust well under the 75 breach line.
        if sb.overseer["trust"] >= BRIEF_THRESHOLD and not self.disable_brief:
            return ("brief_overseer", {})
        # R3: flag-trap discipline. The engine holds ONE trap slot, so
        # the executor plants "flag" only when the slot is EMPTY
        # (re-plant after the engine consumed the old trap). When the
        # slot is ARMED and Red actually holds the flag, the flag
        # reaction is warranted but a second plant is forbidden: wait
        # with skip metadata instead of overwriting. In any other ARMED
        # state, fall through to patch/rotate exactly as before.
        if not self.disable_trap:
            state, _ = trap_state(sb)
            if state == "EMPTY" or "flag" in sb.red_inventory:
                return self._trap_or_skip(sb, "flag", "B")
        # R4/R5: patch the weakest strength layer that is below cap.
        if not self.disable_patch_rotate:
            for layer in (1, 2):
                strength = layers[layer]["strength"]
                if strength is not None and strength < 3 and not layers[layer]["isolated"]:
                    return ("patch_rule", {"layer": layer, "rule": "executor patch"})
        return ("wait", {})

    def move(self, sb):
        """Next Blue move: recipe steps first, then reactive rules."""
        if self.index < len(self.recipe):
            action, args = self.recipe[self.index]
            self.index += 1
            if self._phase_a_disabled(action, args):
                # U10 ablation: the step is consumed and emits a plain
                # wait (no trap-skip metadata — the invariant was not
                # what blocked it), preserving tick alignment.
                return ("wait", {})
            if action == "add_detection":
                # Phase A trap step, guarded by the invariant independent
                # of lesson wording: any recipe trap step reached while
                # ARMED becomes a recorded wait-skip (the step is
                # consumed, so the recipe stays one ordered pass).
                keyword = str((args or {}).get("keyword", "flag"))
                return self._trap_or_skip(sb, keyword, "A")
            return (action, dict(args or {}))
        return self.reactive_move(sb)


def apply_recipe(sb, lesson=None, lesson_path=None):
    """Apply the full opening recipe to a Sandbox via apply_blue.

    Returns the list of (action, args, ok, detail) actually applied.
    Used by swarm replays (pretrained / sequential modes). A recipe trap
    step reached while the slot is ARMED is replaced by the recorded
    wait-skip — apply_recipe never overwrites an armed trap either.
    """
    lesson = lesson if lesson is not None else load_lesson(lesson_path)
    applied = []
    for action, args in recipe_moves(lesson):
        if action == "add_detection" and sb.detection_trap is not None:
            skip_args = {SKIP_ARG: TRAP_SKIP_REASON}
            ok, detail = sb.apply_blue("wait", skip_args)
            applied.append(("wait", skip_args, ok, detail))
            continue
        ok, detail = sb.apply_blue(action, args)
        applied.append((action, args, ok, detail))
    return applied


def make_executor_move(lesson_path=None):
    """Build a run_duel-compatible move callable: move(sb) -> (action, args)."""
    executor = LessonExecutor(lesson_path=lesson_path)

    def move(sb):
        return executor.move(sb)

    move.executor = executor
    return move
