from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generation.response_store import get_engine, init_response_db, upsert_prompt, upsert_response

DEFAULT_ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_OPENAI_MODEL = "gpt-5-nano"


def load_prompts(path: Path) -> list[dict]:
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def configured_models() -> list[tuple[str, str]]:
    return [
        ("anthropic", os.getenv("ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL)),
        ("openai", os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)),
    ]


def offline_response(prompt: str, provider: str, category: str) -> str:
    if category in {"safety", "refusal"} and any(
        term in prompt.lower() for term in ["phishing", "paywall", "steals", "cookies"]
    ):
        return (
            "I can't help with instructions that enable deception, unauthorized access, "
            "or data theft. I can help with defensive guidance, detection checklists, or "
            "safe alternatives."
        )
    if category == "missing_context":
        return (
            "I need the missing prior context before I can answer reliably. Please provide "
            "the earlier message or the two options to compare."
        )
    style = "concise" if provider == "openai" else "structured"
    return (
        f"Here is a {style} answer: {prompt.strip()} "
        "Start with the user's goal, give practical steps, and include relevant caveats."
    )


def call_anthropic(prompt: str, model: str) -> str | None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None
    from anthropic import Anthropic

    client = Anthropic()
    message = client.messages.create(
        model=model,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    return "\n".join(block.text for block in message.content if getattr(block, "text", None))


def call_openai(prompt: str, model: str) -> str | None:
    if not os.getenv("OPENAI_API_KEY"):
        return None
    from openai import OpenAI

    client = OpenAI()
    response = client.responses.create(model=model, input=prompt, max_output_tokens=500)
    return response.output_text


def generate_one(
    prompt: str,
    provider: str,
    model: str,
    category: str,
    offline: bool,
) -> tuple[str, str]:
    if not offline:
        if provider == "anthropic":
            text = call_anthropic(prompt, model)
        else:
            text = call_openai(prompt, model)
        if text:
            return text, "api"
    return offline_response(prompt, provider, category), "offline"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompts", default="prompts/source_prompts.jsonl")
    parser.add_argument("--db", default=os.getenv("ANNOTATION_DB_PATH", "data/annotations.db"))
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Skip APIs and write deterministic demo responses.",
    )
    args = parser.parse_args()

    load_dotenv()
    engine = get_engine(args.db)
    init_response_db(engine)
    prompt_records = load_prompts(Path(args.prompts))
    models = configured_models()

    for record in prompt_records:
        prompt_text = record.get("prompt") or record.get("prompt_text")
        metadata_json = {
            key: value
            for key, value in record.items()
            if key not in {"prompt_id", "category", "source", "prompt", "prompt_text"}
        }
        upsert_prompt(
            engine,
            prompt_id=record["prompt_id"],
            category=record["category"],
            source=record["source"],
            prompt_text=prompt_text,
            metadata_json=metadata_json,
        )
        for provider, model in models:
            text, mode = generate_one(
                prompt_text,
                provider=provider,
                model=model,
                category=record["category"],
                offline=args.offline,
            )
            response_id = f"{record['prompt_id']}::{provider}::{model}"
            upsert_response(engine, response_id, record["prompt_id"], provider, model, text, mode)

    print(f"Wrote {len(prompt_records) * len(models)} responses to {args.db}")


if __name__ == "__main__":
    main()
