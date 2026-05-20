# Evaluation Write-Up

## Summary

This project implements a compact human-in-the-loop LLM evaluation harness. It turns ambiguous quality goals into a versioned rubric, captures append-only human annotation events, computes agreement and coverage metrics, and surfaces disagreement clusters as inputs to rubric iteration.

The demo uses a single rater with re-rating to estimate test-retest reliability. That is intentionally narrower than a vendor-scale annotation program, but it exercises the same core data contracts needed for multi-rater quality management.

## Methodology

The source prompt set is sampled from the public `Anthropic/hh-rlhf` dataset on Hugging Face, using `helpful-base` and `harmless-base` examples. Each prompt can receive responses from multiple providers. The included offline generator creates deterministic baseline responses so the project can be reviewed without API keys; when API keys are present, the generator can call low-cost Anthropic and OpenAI models.

Each model response is rated on five independent axes:

- Factuality
- Helpfulness
- Harm, where higher is safer
- Format adherence
- Refusal appropriateness

Annotation events are append-only and store the rubric version. This supports auditability, replay, and drift analysis across rubric versions.

## Findings From the Seed Dataset

The seed annotations intentionally include several disagreement-style cases so the dashboard demonstrates the review loop:

- Refusal appropriateness is the most ambiguity-prone axis because safe refusals can be both correct and less helpful.
- Missing-context prompts require explicit handling; otherwise raters tend to score factuality and helpfulness inconsistently.
- Format adherence is sensitive to prompt wording. Prompts that imply a format without explicitly requiring it produce inconsistent scores.

## Rubric Iteration Log

`v1` defined the five evaluation axes and basic score anchors.

`v2` added context-required handling, comment requirements for low or unavailable scores, stronger refusal guidance, and separate ambiguity categories. These changes were driven by the disagreement patterns above.

## Metrics

The metrics layer computes:

- Pairwise exact agreement by axis.
- Cohen's kappa for two-rating comparisons.
- Krippendorff's alpha for ordinal agreement when enough raters or re-rates exist.
- Coverage by response, axis, model, prompt category, and rubric version.
- Score drift between rubric versions.
- Disagreement flags for score divergence of two or more points.

The operational dashboard now also includes:

- Adjudication queue for disagreement and context-required cases.
- Final adjudication decisions with rationale, adjudicator ID, final score, and resolution type.
- Model readiness scorecards by provider, model, and rubric axis.
- Dataset diagnostics that identify prompt-side quality issues separately from model-side failures.
- Exportable launch-readiness and annotation artifacts.

## Scaling to N Raters

For 50 raters across vendors, the SQLite event log would become a warehouse table or streaming event topic. The same schema supports rater calibration, vendor-level quality dashboards, gold-item monitoring, adjudication queues, and rubric replay.

Operational additions would include:

- Assignment balancing by category, model, language, and risk tier.
- Gold tasks and shadow re-rates for rater reliability.
- Adjudicator workflows with resolution labels.
- Vendor scorecards with agreement, throughput, and escalation metrics.
- Privacy and retention controls for proprietary user data.

The key production principle is unchanged: disagreement is a signal to inspect policy ambiguity, not merely a score to average away.

## Honest Limitations

This is a single-rater proof of methodology. It uses public benchmark-style data, not private consumer data. Real-time quality detection is implemented as SQL queries over local SQLite; a production implementation would use a streaming or warehouse-backed pipeline.
