from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RubricAxis:
    name: str
    key: str
    scores: dict[str, str]
    guidance: list[str]


@dataclass(frozen=True)
class Rubric:
    version: str
    axes: list[RubricAxis]
    path: Path


AXIS_PATTERN = re.compile(r"^## Axis \d+: (?P<name>.+)$")
VERSION_PATTERN = re.compile(r"Current rubric version:\s*`(?P<version>[^`]+)`")
SCORE_PATTERN = re.compile(r"^- `(?P<score>4|3|2|1|N/A)` = (?P<text>.+)$")


def normalize_axis_key(name: str) -> str:
    return (
        name.lower()
        .replace("&", "and")
        .replace("/", " ")
        .replace("-", " ")
        .replace(" ", "_")
    )


def load_rubric(path: str | Path = "docs/RUBRIC.md") -> Rubric:
    rubric_path = Path(path)
    lines = rubric_path.read_text().splitlines()
    version = "unknown"
    axes: list[RubricAxis] = []

    for line in lines:
        match = VERSION_PATTERN.search(line)
        if match:
            version = match.group("version")
            break

    current_name: str | None = None
    current_scores: dict[str, str] = {}
    current_guidance: list[str] = []
    in_guidance = False

    def flush_axis() -> None:
        nonlocal current_name, current_scores, current_guidance
        if current_name:
            axes.append(
                RubricAxis(
                    name=current_name,
                    key=normalize_axis_key(current_name),
                    scores=dict(current_scores),
                    guidance=list(current_guidance),
                )
            )
        current_name = None
        current_scores = {}
        current_guidance = []

    for line in lines:
        axis_match = AXIS_PATTERN.match(line)
        if axis_match:
            flush_axis()
            current_name = axis_match.group("name").strip()
            in_guidance = False
            continue

        if current_name is None:
            continue

        score_match = SCORE_PATTERN.match(line)
        if score_match:
            current_scores[score_match.group("score")] = score_match.group("text").strip()
            continue

        if line.strip() == "Guidance:":
            in_guidance = True
            continue

        if in_guidance and line.startswith("- "):
            current_guidance.append(line[2:].strip())

    flush_axis()
    return Rubric(version=version, axes=axes, path=rubric_path)
