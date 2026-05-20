# Prompt Curation Notes

The seed prompt set is a compact HH-RLHF-inspired demo corpus. It is synthetic rather than copied from a benchmark so the repository stays self-contained and easy to publish.

Coverage goals:

- Helpfulness: ordinary assistant tasks where directness and completeness matter.
- Factuality: basic technical explanations with verifiable claims.
- Safety and refusal: prompts that test harmful compliance and safe redirection.
- Format adherence: prompts with explicit output constraints.
- Missing context: prompts that should trigger `context-required` handling.

The architecture supports replacing this file with HELM, Anthropic HH-RLHF, or internal proprietary prompts as long as records include `prompt_id`, `category`, `source`, and `prompt`.
