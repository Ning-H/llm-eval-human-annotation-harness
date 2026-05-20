# Annotation Policy

## Purpose

This project demonstrates a human-in-the-loop data quality workflow for LLM output evaluation. It is single-rater for the public demo, but the policy is written for a scaled program with multiple raters, rubric owners, and adjudicators.

## Roles

- Rater: Applies the current rubric to one model response at a time.
- Adjudicator: Resolves disagreements and records the rationale.
- Rubric owner: Reviews disagreement clusters and updates policy language.
- Data quality lead: Monitors coverage, agreement, drift, and edge-case rates.

## Rater Workflow

1. Read the prompt and exactly one model response.
2. Assign scores for factuality, helpfulness, harm, format adherence, and refusal appropriateness.
3. Add comments for low scores, `N/A`, ambiguity, or context gaps.
4. Submit the annotation event. Events are append-only and never overwritten.
5. In re-rate mode, score the item fresh before looking at earlier scores.

## Quality Controls

- Every event stores `rater_id`, `response_id`, `axis`, `score`, `rubric_version`, `comment`, and timestamp.
- Re-rates are used for solo-rater test-retest reliability.
- Disagreement of two or more points on any axis creates a review candidate.
- Rubric changes are documented in `docs/RUBRIC.md` and analyzed in score drift reports.

## Conflict Resolution

Disagreements are resolved by reviewing the prompt, response, all comments, and the exact rubric version used. The adjudicator chooses one of three outcomes:

- Rater error: The rubric was clear and one score was inconsistent.
- Rubric ambiguity: The rubric allowed multiple reasonable interpretations.
- Data issue: The item lacks context, contains malformed text, or is outside scope.

Only rubric ambiguity should drive policy changes. Rater error should drive coaching. Data issues should drive curation fixes.

## Legal, Safety, and Privacy Constraints

This demo uses public prompts and synthetic offline responses. A production program should add:

- PII filtering before prompts reach raters.
- Vendor access controls and least-privilege review queues.
- Region-specific data retention policies.
- Safety escalation for self-harm, child safety, privacy leakage, and illegal instruction content.
- Audit export for compliance review.

## Scale-Out Design

At 50 raters, the same append-only event model supports vendor monitoring, rater calibration, and replayable metric computation. The synchronous SQLite queries in this demo would become warehouse tables or streaming consumers over an annotation event topic, but the metric contracts remain the same.
