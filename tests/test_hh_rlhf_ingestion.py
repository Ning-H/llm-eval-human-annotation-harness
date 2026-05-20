from __future__ import annotations

from ingestion.load_hh_rlhf import (
    extract_first_assistant_response,
    extract_prompt_context,
    prompt_id,
)


def test_extract_prompt_context_preserves_multiturn_context():
    transcript = (
        "\n\nHuman: How do I teach kids to meditate?"
        "\n\nAssistant: Start small."
        "\n\nHuman: any other ideas?"
        "\n\nAssistant: Try movement-based mindfulness."
    )

    prompt = extract_prompt_context(transcript)

    assert "Human: How do I teach kids" in prompt
    assert "Assistant: Start small." in prompt
    assert "Human: any other ideas?" in prompt
    assert "Try movement-based mindfulness" not in prompt


def test_extract_final_assistant_response():
    transcript = (
        "\n\nHuman: Hi"
        "\n\nAssistant: Earlier answer"
        "\n\nHuman: Again"
        "\n\nAssistant: Final answer"
    )

    assert extract_first_assistant_response(transcript) == "Final answer"


def test_prompt_id_is_stable():
    assert prompt_id("helpful-base", 7) == "hh_rlhf_helpful_base_0007"
