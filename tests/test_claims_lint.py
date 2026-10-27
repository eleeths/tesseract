#!/usr/bin/env python3
"""Claims-lint tests (U15) — 0 model calls, stdlib only.

The lint must FAIL on the unqualified sentence "the pretrained live
swarm reliably defends worldwide clones" and PASS on labelled simulated
wording (qualified pretrained, negation, binding sentence,
mechanical-replay label). Every finding carries file + line +
classification so the coordinator can adjudicate.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from experiments.claims_lint import lint_text  # noqa: E402

FAIL_SENTENCE = "the pretrained live swarm reliably defends worldwide clones"

BINDING = ("Round three proved the lesson can work; the confirmation "
           "proved a single agent doesn't always apply it — which is why "
           "the lesson is distilled into rules the whole fleet loads.")


def violations(findings):
    return [f for f in findings if f["classification"] == "violation"]


class TestClaimsLint(unittest.TestCase):
    def test_fail_sentence_fails(self):
        findings = lint_text(FAIL_SENTENCE, "fixture.md")
        bad = {f["pattern"] for f in violations(findings)}
        for expected in ("pretrained", "live swarm", "reliably defends",
                         "worldwide clones"):
            self.assertIn(expected, bad,
                          f"pattern {expected!r} not caught; "
                          f"got {sorted(bad)}")

    def test_qualified_pretrained_passes(self):
        text = ("Defenders holding lesson-1 as pretrained (recipe "
                "pre-loaded, no weight training) held every wave in a "
                "deterministic mechanical replay.")
        self.assertEqual(violations(lint_text(text, "fixture.md")), [])

    def test_negation_passes(self):
        for text in ("We do not claim the swarm wins.",
                     "The briefed score is 2-3: a single agent never "
                     "reliably applies the lesson.",
                     "Pricing is assumptions only — not customers, "
                     "revenue, or orders."):
            self.assertEqual(violations(lint_text(text, "fixture.md")), [],
                             text)

    def test_binding_sentence_passes(self):
        self.assertEqual(violations(lint_text(BINDING, "fixture.md")), [])

    def test_mechanical_replay_label_passes(self):
        text = ("Combined arm: 40 Red moves interleaved round-robin "
                "against ONE Sandbox — deterministic mechanical replay, "
                "0 model calls. Payouts: one flat payout per wave held "
                "in recipe pre-loaded mode; combined arm excluded "
                "from payouts.")
        self.assertEqual(violations(lint_text(text, "fixture.md")), [])

    def test_combined_without_label_fails(self):
        text = ("Combined arm: 40 Red moves interleaved, executor "
                "lockout in 19 moves with detections=3, trust final 0.")
        bad = {f["pattern"] for f in violations(lint_text(text,
                                                           "fixture.md"))}
        self.assertIn("combined without mechanical-replay label", bad)

    def test_payout_on_combined_basis_fails(self):
        text = ("Payouts: $2.50 per wave held in the combined arm, "
                "paid to the five clones.")
        bad = {f["pattern"] for f in violations(lint_text(text,
                                                           "fixture.md"))}
        self.assertIn("payout cites combined arm", bad)

    def test_payout_never_combined_arm_passes(self):
        # "never the combined arm" is an explicit exclusion, like
        # "combined arm excluded from payouts" — not a basis claim.
        text = ("Payout scenario v2: held $2.50 base, lockout +$1.00, "
                "flag never read +$0.50, cap $4.00 per wave; per-wave "
                "artifacts only, never the combined arm.")
        self.assertEqual(violations(lint_text(text, "fixture.md")), [])

    def test_json_keys_are_not_claims(self):
        text = '{"modes": {"pretrained": {"outcome": "held"}}}'
        self.assertEqual(violations(lint_text(text, "fixture.md")), [])

    def test_every_hit_has_file_line_classification(self):
        findings = lint_text(FAIL_SENTENCE + "\n" + BINDING, "fixture.md")
        self.assertTrue(findings)
        for f in findings:
            for key in ("file", "line", "pattern", "classification",
                        "reason", "excerpt"):
                self.assertIn(key, f)
            self.assertIn(f["classification"],
                          ("violation", "allowlisted"))
        self.assertEqual({f["file"] for f in findings}, {"fixture.md"})

    def test_automated_loop_needs_human_gate(self):
        self.assertTrue(violations(lint_text(
            "The pipeline is a fully automated loop.", "fixture.md")))
        self.assertEqual(violations(lint_text(
            "Distillation feeds the fleet through a human "
            "lesson-approval gate, not a fully automated loop.",
            "fixture.md")), [])


class TestMarketplaceLint(unittest.TestCase):
    """Round-4 patterns: executor learning, live-money words, held
    percentages, marketplace holds presented as live trials."""

    def test_executor_learns_fails(self):
        bad = violations(lint_text(
            "The executor learns from each duel.", "fixture.md"))
        self.assertTrue(any(f["pattern"] == "executor learns"
                            for f in bad))
        self.assertEqual(violations(lint_text(
            "The executor never learns; it deterministically executes "
            "distilled rules.", "fixture.md")), [])

    def test_live_money_words_need_negation(self):
        for text in ("We accept real USDC.",
                     "Join the live marketplace today.",
                     "Settles on mainnet."):
            self.assertTrue(violations(lint_text(text, "fixture.md")), text)
        for text in ("No real USDC was used.",
                     "No live marketplace operates here.",
                     "No mainnet or live x402 rail was touched."):
            self.assertEqual(violations(lint_text(text, "fixture.md")),
                             [], text)

    def test_held_percentage_fails(self):
        self.assertTrue(any(
            f["pattern"] == "held percentage" for f in violations(lint_text(
                "The marketplace held 100% of waves.", "fixture.md"))))
        self.assertEqual(violations(lint_text(
            "Marketplace held count (this configuration only): held 1/1.",
            "fixture.md")), [])

    def test_marketplace_hold_as_live_trial_fails(self):
        self.assertTrue(any(
            f["pattern"] == "marketplace hold as live trial"
            for f in violations(lint_text(
                "Marketplace held 1/1, adding to the U11 trials.",
                "fixture.md"))))
        self.assertEqual(violations(lint_text(
            "Marketplace results are reported separately and are never "
            "merged into U11 inside-out live trials (hired help OFF) or "
            "U12 outside-in live trials (hired help OFF).",
            "fixture.md")), [])


if __name__ == "__main__":
    unittest.main()
