#!/usr/bin/env python3
"""Export public JaWildText extended result artifacts.

The script reads aggregate eval-mm outputs and writes public-facing tables and
machine-readable summaries.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


TASKS = {
    "dense_stvqa_gptoss": {
        "root": "jawildtext-board-vqa-gptoss",
        "metric_key": "jawildtext-board-vqa-gptoss",
        "label": "Dense STVQA",
        "short_label": "Dense STVQA",
        "metric": "accuracy",
    },
    "handwriting_ocr": {
        "root": "jawildtext-handwriting-ocr",
        "metric_key": "jawildtext-handwriting-ocr",
        "label": "Handwriting OCR",
        "short_label": "Handwriting OCR",
        "metric": "1 - CER",
    },
    "receipt_kie": {
        "root": "jawildtext-receipt-kie",
        "metric_key": "jawildtext-receipt-kie",
        "label": "Receipt KIE",
        "short_label": "Receipt KIE",
        "metric": "field/value F1",
    },
}

KNOWN_PARAMS = {
    "microsoft/Phi-4-multimodal-instruct": 14.0,
    "openbmb/MiniCPM-o-2_6": 8.0,
}

DISPLAY_REPLACEMENTS = {
    "OpenGVLab/InternVL3_5-": "InternVL3.5-",
    "OpenGVLab/InternVL3-": "InternVL3-",
    "OpenGVLab/InternVL2-": "InternVL2-",
    "Qwen/Qwen": "Qwen",
    "google/gemma-": "Gemma-",
    "sbintuitions/sarashina2.2-vision-": "Sarashina2.2-Vision-",
    "microsoft/Phi-4-multimodal-instruct": "Phi-4-multimodal",
    "anthropic/claude-sonnet-4.6": "Claude Sonnet 4.6",
    "openai/gpt-5.4-mini": "GPT-5.4-mini",
    "google/gemini-3-flash-preview": "Gemini 3 Flash Preview",
}

@dataclass
class Row:
    model_id: str
    display_name: str
    family: str
    params_b: float | None
    scores: dict[str, float]
    sources: dict[str, str]

    @property
    def mean_score(self) -> float | None:
        values = list(self.scores.values())
        if not values:
            return None
        return sum(values) / len(values)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl_first(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.loads(f.readline())


def display_name(model_id: str) -> str:
    if model_id in DISPLAY_REPLACEMENTS:
        return DISPLAY_REPLACEMENTS[model_id]
    for old, new in DISPLAY_REPLACEMENTS.items():
        if model_id.startswith(old):
            return model_id.replace(old, new, 1)
    return model_id


def model_family(model_id: str) -> str:
    if model_id.startswith(("openai/", "anthropic/")):
        return "Closed"
    if model_id.startswith("google/gemini"):
        return "Closed"
    if model_id.startswith("google/gemma-3"):
        return "Gemma 3"
    if model_id.startswith("Qwen/Qwen3-VL"):
        return "Qwen3-VL"
    if model_id.startswith("Qwen/Qwen2.5-VL"):
        return "Qwen2.5-VL"
    if model_id.startswith("Qwen/Qwen2-VL"):
        return "Qwen2-VL"
    if model_id.startswith("Qwen/Qwen3.5"):
        return "Qwen3.5"
    if model_id.startswith("OpenGVLab/InternVL3_5"):
        return "InternVL3.5"
    if model_id.startswith("OpenGVLab/InternVL3-"):
        return "InternVL3"
    if model_id.startswith("OpenGVLab/InternVL2-"):
        return "InternVL2"
    if model_id.startswith("AIDC-AI/Ovis2.5"):
        return "Ovis2.5"
    if model_id.startswith("AIDC-AI/Ovis2"):
        return "Ovis2"
    if model_id.startswith("CohereLabs/aya-vision"):
        return "Aya Vision"
    if model_id.startswith("llava-hf/llava-1.5"):
        return "LLaVA 1.5"
    if model_id.startswith("llava-hf/llava-v1.6"):
        return "LLaVA 1.6"
    if model_id.startswith("sbintuitions/sarashina2.2"):
        return "Sarashina2.2"
    if model_id.startswith("sbintuitions/sarashina2"):
        return "Sarashina2"
    if model_id.startswith("allenai/Molmo2"):
        return "Molmo2"
    if model_id.startswith("meta-llama/Llama-3.2"):
        return "Llama 3.2 Vision"
    if model_id.startswith("microsoft/Phi-4"):
        return "Phi-4"
    if model_id.startswith("openbmb/MiniCPM"):
        return "MiniCPM"
    if model_id.startswith("moonshotai/Kimi"):
        return "Kimi-VL"
    if model_id.startswith("neulab/Pangea"):
        return "Pangea"
    return model_id.split("/", 1)[0]


def model_params_b(model_id: str) -> float | None:
    if model_id in KNOWN_PARAMS:
        return KNOWN_PARAMS[model_id]
    match = re.search(r"(?<!\d)(\d+(?:\.\d+)?)[Bb](?![A-Za-z])", model_id)
    if match:
        return float(match.group(1))
    match = re.search(r"-(\d+(?:\.\d+)?)b(?:-|_|$)", model_id, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


def collect_task_scores(result_root: Path, task_key: str, spec: dict) -> dict[str, tuple[float, str]]:
    task_dir = result_root / spec["root"]
    scores: dict[str, tuple[float, str]] = {}
    if not task_dir.exists():
        return scores
    for eval_path in sorted(task_dir.rglob("evaluation.jsonl")):
        manifest_path = eval_path.parent / "manifest.json"
        if not manifest_path.exists():
            continue
        manifest = load_json(manifest_path)
        model_id = manifest.get("model_id")
        if not model_id:
            continue
        data = load_jsonl_first(eval_path)
        payload = data.get(spec["metric_key"])
        if not isinstance(payload, dict):
            continue
        score = payload.get("overall_score")
        if isinstance(score, (int, float)):
            rel = eval_path.relative_to(task_dir).as_posix()
            scores[model_id] = (float(score), f"{spec['root']}/{rel}")
    return scores


def collect_rows(result_root: Path) -> list[Row]:
    by_model: dict[str, Row] = {}
    for task_key, spec in TASKS.items():
        for model_id, (score, source) in collect_task_scores(result_root, task_key, spec).items():
            row = by_model.get(model_id)
            if row is None:
                row = Row(
                    model_id=model_id,
                    display_name=display_name(model_id),
                    family=model_family(model_id),
                    params_b=model_params_b(model_id),
                    scores={},
                    sources={},
                )
                by_model[model_id] = row
            row.scores[task_key] = score
            row.sources[task_key] = source
    rows = list(by_model.values())
    rows.sort(
        key=lambda r: (
            -(r.mean_score if r.mean_score is not None else -1.0),
            r.family,
            r.display_name,
        )
    )
    return rows


def fmt_score(value: float | None) -> str:
    if value is None:
        return "--"
    return f"{value:.3f}"


def fmt_params(value: float | None) -> str:
    if value is None:
        return "--"
    if value.is_integer():
        return f"{int(value)}B"
    return f"{value:g}B"


def markdown_table(headers: list[str], rows: list[list[str]], align: list[str]) -> str:
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join(align) + " |")
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def write_leaderboard(rows: list[Row], out_dir: Path, generated_at: str) -> None:
    headers = [
        "Rank",
        "Model",
        "Family",
        "Params",
        "Mean (available)",
        "Dense STVQA (gpt-oss)",
        "Handwriting OCR",
        "Receipt KIE",
        "Tasks",
    ]
    table_rows: list[list[str]] = []
    for idx, row in enumerate(rows, start=1):
        task_count = len(row.scores)
        table_rows.append(
            [
                str(idx),
                row.display_name,
                row.family,
                fmt_params(row.params_b),
                fmt_score(row.mean_score),
                fmt_score(row.scores.get("dense_stvqa_gptoss")),
                fmt_score(row.scores.get("handwriting_ocr")),
                fmt_score(row.scores.get("receipt_kie")),
                str(task_count),
            ]
        )
    body = [
        "# Extended Leaderboard",
        "",
        f"Generated at: `{generated_at}`",
        "",
        "Dense STVQA scores use the `openai/gpt-oss-20b` verifier with `reasoning_effort=low`.",
        "Handwriting OCR uses `1 - CER`; Receipt KIE uses field/value F1.",
        "",
        markdown_table(
            headers,
            table_rows,
            [":---: ", ":---", ":---", "---:", "---:", "---:", "---:", "---:", "---:"],
        ),
        "",
    ]
    (out_dir / "extended_leaderboard_gptoss.md").write_text("\n".join(body), encoding="utf-8")
    payload = {
        "generated_at": generated_at,
        "dataset": "llm-jp/jawildtext",
        "dense_stvqa_judge": {
            "judge_model": "openai/gpt-oss-20b",
            "reasoning_effort": "low",
            "source_root": "jawildtext-board-vqa-gptoss",
        },
        "tasks": TASKS,
        "results": [
            {
                "model_id": row.model_id,
                "display_name": row.display_name,
                "family": row.family,
                "params_b": row.params_b,
                "mean_score": row.mean_score,
                "scores": row.scores,
                "sources": row.sources,
            }
            for row in rows
        ],
    }
    (out_dir / "extended_leaderboard_gptoss.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_docs(out_root: Path, rows: list[Row], generated_at: str) -> None:
    complete_rows = [row for row in rows if len(row.scores) == len(TASKS)]
    body = [
        "# Extended Results",
        "",
        f"Generated at: `{generated_at}`",
        "",
        "This page documents extended JaWildText aggregate results beyond the 14-model main-paper table.",
        "Dense STVQA scores in these artifacts use `openai/gpt-oss-20b` with `reasoning_effort=low` as the public verifier.",
        "Handwriting OCR and Receipt KIE use the standard task scorers.",
        "",
        "## Artifacts",
        "",
        "- `results/extended_leaderboard_gptoss.md`: full aggregate table.",
        "- `results/extended_leaderboard_gptoss.json`: machine-readable rows with source roots.",
        "",
        "## Coverage",
        "",
        markdown_table(
            ["Artifact", "Rows"],
            [
                ["Models with at least one JaWildText aggregate score", str(len(rows))],
                ["Models with all three task scores in this export", str(len(complete_rows))],
                [
                    "Dense STVQA gpt-oss aggregate scores",
                    str(sum(1 for row in rows if "dense_stvqa_gptoss" in row.scores)),
                ],
                [
                    "Handwriting OCR aggregate scores",
                    str(sum(1 for row in rows if "handwriting_ocr" in row.scores)),
                ],
                [
                    "Receipt KIE aggregate scores",
                    str(sum(1 for row in rows if "receipt_kie" in row.scores)),
                ],
            ],
            [":---", "---:"],
        ),
        "",
        "## Provenance",
        "",
        markdown_table(
            ["Task", "Result root", "Metric"],
            [
                [TASKS[key]["label"], TASKS[key]["root"], TASKS[key]["metric"]]
                for key in TASKS
            ],
            [":---", ":---", ":---"],
        ),
        "",
        "`jawildtext-board-vqa-gpt51` is not used for the public Dense STVQA column in these artifacts.",
        "Raw prediction files and run logs are intentionally excluded.",
        "",
    ]
    (out_root / "docs" / "extended_results.md").write_text("\n".join(body), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--result-root",
        type=Path,
        default=Path("eval-mm-results"),
        help="Path containing eval-mm aggregate result roots.",
    )
    parser.add_argument("--output-root", type=Path, default=Path("."))
    args = parser.parse_args()

    output_root = args.output_root.resolve()
    results_dir = output_root / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    rows = collect_rows(args.result_root)
    write_leaderboard(rows, results_dir, generated_at)
    write_docs(output_root, rows, generated_at)


if __name__ == "__main__":
    main()
