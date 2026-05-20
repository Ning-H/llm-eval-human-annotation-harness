# Prompt Curation Notes

The default prompt file is generated from the public
`Anthropic/hh-rlhf` dataset on Hugging Face. The ingestion script samples
from:

- `helpful-base`
- `harmless-base`

The source records include chosen/rejected assistant responses. For this
project, the model-evaluation input is the conversation context up to the
final assistant turn. The chosen/rejected responses are retained as metadata
so the project can later export preference pairs or compare fresh model
outputs against public reference answers.

Regenerate the prompt file with:

```bash
python ingestion/load_hh_rlhf.py --limit 50 --output prompts/source_prompts.jsonl
```

Each JSONL row includes:

- `prompt_id`
- `category`
- `source`
- `prompt`
- `reference_chosen`
- `reference_rejected`
- `risk_tags`

This keeps the demo public, reproducible, and closer to a real evaluation
workflow than synthetic prompts.
