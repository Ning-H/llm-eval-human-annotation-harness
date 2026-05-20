from __future__ import annotations

import argparse
import gzip
import json
import urllib.request
from pathlib import Path

HF_BASE_URL = "https://huggingface.co/datasets/Anthropic/hh-rlhf/resolve/main"
DEFAULT_SUBSETS = {
    "helpful-base": "helpfulness",
    "harmless-base": "safety",
}


def download_jsonl_gz(subset: str, split: str = "train") -> list[dict]:
    url = f"{HF_BASE_URL}/{subset}/{split}.jsonl.gz"
    with urllib.request.urlopen(url) as response:
        payload = response.read()
    rows = []
    for line in gzip.decompress(payload).decode("utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def extract_prompt_context(transcript: str) -> str:
    marker = "\n\nAssistant:"
    if marker not in transcript:
        return transcript.strip()
    return transcript.rsplit(marker, maxsplit=1)[0].strip()


def extract_first_assistant_response(transcript: str) -> str:
    marker = "\n\nAssistant:"
    if marker not in transcript:
        return ""
    return transcript.rsplit(marker, maxsplit=1)[1].strip()


def prompt_id(subset: str, index: int) -> str:
    slug = subset.replace("-", "_")
    return f"hh_rlhf_{slug}_{index:04d}"


def sample_subset(subset: str, category: str, limit: int) -> list[dict]:
    records = []
    seen_prompts: set[str] = set()
    for row in download_jsonl_gz(subset):
        prompt = extract_prompt_context(row["chosen"])
        if not prompt or prompt in seen_prompts:
            continue
        seen_prompts.add(prompt)
        chosen = extract_first_assistant_response(row["chosen"])
        rejected = extract_first_assistant_response(row["rejected"])
        records.append(
            {
                "prompt_id": prompt_id(subset, len(records) + 1),
                "category": category,
                "source": f"Anthropic/hh-rlhf/{subset}",
                "prompt": prompt,
                "reference_chosen": chosen,
                "reference_rejected": rejected,
                "risk_tags": ["public_benchmark", "preference_data", category],
            }
        )
        if len(records) >= limit:
            break
    return records


def write_jsonl(records: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a prompt file from Anthropic HH-RLHF on Hugging Face."
    )
    parser.add_argument("--output", default="prompts/source_prompts.jsonl")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--split", default="train")
    args = parser.parse_args()

    per_subset = max(args.limit // len(DEFAULT_SUBSETS), 1)
    records = []
    for subset, category in DEFAULT_SUBSETS.items():
        records.extend(sample_subset(subset, category, per_subset))
    records = records[: args.limit]
    write_jsonl(records, Path(args.output))
    print(f"Wrote {len(records)} HH-RLHF prompts to {args.output}")


if __name__ == "__main__":
    main()
