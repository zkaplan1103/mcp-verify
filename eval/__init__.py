"""Evaluation harness for the verify engine's hallucination detection.

Measures precision, recall, F1, and a confusion matrix over a labeled set of
cases: drafts built from sentences that are either grounded in the source or
planted (unsupported). This benchmark is the detector's credibility — it travels
with the package but does not ship in the wheel.
"""
