#!/usr/bin/env python3
"""Export public JaWildText extended result artifacts.

The script reads aggregate eval-mm outputs and writes public-facing tables,
machine-readable summaries, and a small-multiple scaling-curve SVG.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import re
import subprocess
from collections import defaultdict
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

PALETTE = {
    "Qwen3-VL": "#2563eb",
    "Qwen2.5-VL": "#0f766e",
    "Qwen3.5": "#7c3aed",
    "InternVL3.5": "#dc2626",
    "InternVL3": "#ea580c",
    "Gemma 3": "#16a34a",
    "Ovis2": "#9333ea",
    "LLaVA 1.5": "#475569",
    "Closed": "#111827",
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


def family_summary(rows: list[Row]) -> list[dict]:
    by_family: dict[str, list[Row]] = defaultdict(list)
    for row in rows:
        by_family[row.family].append(row)
    summary: list[dict] = []
    for family, family_rows in sorted(by_family.items()):
        entry: dict = {"family": family, "models": len(family_rows)}
        all_task_values: list[float] = []
        for task_key in TASKS:
            values = [(r.scores[task_key], r) for r in family_rows if task_key in r.scores]
            if not values:
                entry[task_key] = None
                continue
            best_score, best_row = max(values, key=lambda item: item[0])
            avg_score = sum(score for score, _ in values) / len(values)
            all_task_values.extend(score for score, _ in values)
            entry[task_key] = {
                "models": len(values),
                "average": avg_score,
                "best": best_score,
                "best_model": best_row.model_id,
            }
        entry["mean_available_score"] = (
            sum(all_task_values) / len(all_task_values) if all_task_values else None
        )
        summary.append(entry)
    summary.sort(
        key=lambda item: (
            -(item["mean_available_score"] if item["mean_available_score"] is not None else -1.0),
            item["family"],
        )
    )
    return summary


def write_family_summary(rows: list[Row], out_dir: Path, generated_at: str) -> list[dict]:
    summary = family_summary(rows)
    headers = [
        "Family",
        "Models",
        "Mean (available)",
        "Dense STVQA avg",
        "Dense STVQA best",
        "HW OCR avg",
        "HW OCR best",
        "Receipt KIE avg",
        "Receipt KIE best",
    ]
    table_rows: list[list[str]] = []
    for item in summary:
        def avg(task_key: str) -> str:
            task = item.get(task_key)
            return fmt_score(task["average"]) if task else "--"

        def best(task_key: str) -> str:
            task = item.get(task_key)
            if not task:
                return "--"
            return f"{fmt_score(task['best'])} ({display_name(task['best_model'])})"

        table_rows.append(
            [
                item["family"],
                str(item["models"]),
                fmt_score(item["mean_available_score"]),
                avg("dense_stvqa_gptoss"),
                best("dense_stvqa_gptoss"),
                avg("handwriting_ocr"),
                best("handwriting_ocr"),
                avg("receipt_kie"),
                best("receipt_kie"),
            ]
        )
    body = [
        "# Model Family Summary",
        "",
        f"Generated at: `{generated_at}`",
        "",
        markdown_table(
            headers,
            table_rows,
            [":---", "---:", "---:", "---:", ":---", "---:", ":---", "---:", ":---"],
        ),
        "",
    ]
    (out_dir / "family_summary_gptoss.md").write_text("\n".join(body), encoding="utf-8")
    (out_dir / "family_summary_gptoss.json").write_text(
        json.dumps(
            {
                "generated_at": generated_at,
                "dataset": "llm-jp/jawildtext",
                "dense_stvqa_judge": {
                    "judge_model": "openai/gpt-oss-20b",
                    "reasoning_effort": "low",
                },
                "families": summary,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return summary


def scaling_points(rows: list[Row]) -> dict:
    points: dict[str, dict[str, list[dict]]] = {}
    for task_key in TASKS:
        by_family: dict[str, list[dict]] = defaultdict(list)
        for row in rows:
            if task_key not in row.scores or row.params_b is None:
                continue
            by_family[row.family].append(
                {
                    "model_id": row.model_id,
                    "display_name": row.display_name,
                    "params_b": row.params_b,
                    "score": row.scores[task_key],
                }
            )
        points[task_key] = {}
        for family, family_points in by_family.items():
            family_points.sort(key=lambda item: (item["params_b"], item["model_id"]))
            if len(family_points) >= 2:
                points[task_key][family] = family_points
    return points


def svg_text(x: float, y: float, text: str, size: int = 12, anchor: str = "start") -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" '
        f'font-family="Arial, sans-serif" text-anchor="{anchor}" fill="#111827">'
        f"{html.escape(text)}</text>"
    )


def path_for_points(points: list[dict], x_scale, y_scale) -> str:
    coords = [(x_scale(item["params_b"]), y_scale(item["score"])) for item in points]
    if len(coords) == 1:
        x, y = coords[0]
        return f"M {x:.1f} {y:.1f}"
    return " ".join(
        f"{'M' if idx == 0 else 'L'} {x:.1f} {y:.1f}"
        for idx, (x, y) in enumerate(coords)
    )


def write_scaling_artifacts(rows: list[Row], out_dir: Path, generated_at: str) -> None:
    curve_dir = out_dir / "scaling_curves"
    curve_dir.mkdir(parents=True, exist_ok=True)
    points = scaling_points(rows)
    (curve_dir / "by_task_and_family.json").write_text(
        json.dumps(
            {
                "generated_at": generated_at,
                "dataset": "llm-jp/jawildtext",
                "x_axis": "model parameters in billions, log scale",
                "y_axis": "task score",
                "tasks": TASKS,
                "points": points,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    width = 1320
    height = 520
    panel_w = 370
    panel_h = 330
    gap = 45
    top = 92
    left0 = 70
    bottom_pad = 70
    all_params = [
        item["params_b"]
        for task in points.values()
        for family_points in task.values()
        for item in family_points
        if item["params_b"] > 0
    ]
    x_min = math.log10(min(all_params) if all_params else 1.0)
    x_max = math.log10(max(all_params) if all_params else 100.0)
    if x_min == x_max:
        x_max += 1
    y_min, y_max = 0.0, 1.0
    families = sorted(
        {
            family
            for task in points.values()
            for family, family_points in task.items()
            if len(family_points) >= 2
        }
    )
    preferred = [
        "Qwen3-VL",
        "Qwen2.5-VL",
        "Qwen3.5",
        "InternVL3.5",
        "InternVL3",
        "Gemma 3",
        "Ovis2",
        "LLaVA 1.5",
    ]
    plotted_families = [f for f in preferred if f in families]
    for family in families:
        if family not in plotted_families and len(plotted_families) < 10:
            plotted_families.append(family)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        svg_text(40, 38, "JaWildText scaling curves by model family", 22),
        svg_text(
            40,
            64,
            "Dense STVQA uses gpt-oss-20b; x-axis is total model parameters on a log scale.",
            13,
        ),
    ]
    ticks_x = [1, 2, 4, 8, 16, 32, 72]
    ticks_y = [0.0, 0.25, 0.5, 0.75, 1.0]
    task_order = ["dense_stvqa_gptoss", "handwriting_ocr", "receipt_kie"]
    for panel_idx, task_key in enumerate(task_order):
        x0 = left0 + panel_idx * (panel_w + gap)
        y0 = top
        x1 = x0 + panel_w
        y1 = y0 + panel_h

        def x_scale(value: float) -> float:
            return x0 + ((math.log10(value) - x_min) / (x_max - x_min)) * panel_w

        def y_scale(value: float) -> float:
            return y1 - ((value - y_min) / (y_max - y_min)) * panel_h

        parts.append(f'<rect x="{x0}" y="{y0}" width="{panel_w}" height="{panel_h}" fill="#fafafa" stroke="#d1d5db"/>')
        parts.append(svg_text(x0, y0 - 16, TASKS[task_key]["label"], 16))
        for tick in ticks_y:
            y = y_scale(tick)
            parts.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}" stroke="#e5e7eb"/>')
            parts.append(svg_text(x0 - 10, y + 4, f"{tick:.2f}", 11, "end"))
        for tick in ticks_x:
            if math.log10(tick) < x_min or math.log10(tick) > x_max:
                continue
            x = x_scale(tick)
            parts.append(f'<line x1="{x:.1f}" y1="{y0}" x2="{x:.1f}" y2="{y1}" stroke="#e5e7eb"/>')
            parts.append(svg_text(x, y1 + 20, f"{tick}B", 11, "middle"))
        for family in plotted_families:
            family_points = points.get(task_key, {}).get(family)
            if not family_points:
                continue
            color = PALETTE.get(family, "#64748b")
            parts.append(
                f'<path d="{path_for_points(family_points, x_scale, y_scale)}" '
                f'fill="none" stroke="{color}" stroke-width="2.4"/>'
            )
            for item in family_points:
                x = x_scale(item["params_b"])
                y = y_scale(item["score"])
                parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.8" fill="{color}"/>')
        parts.append(svg_text((x0 + x1) / 2, y1 + 48, "Parameters", 12, "middle"))
    legend_x = 40
    legend_y = height - 30
    offset = 0
    for family in plotted_families:
        color = PALETTE.get(family, "#64748b")
        x = legend_x + offset
        parts.append(f'<line x1="{x}" y1="{legend_y}" x2="{x + 22}" y2="{legend_y}" stroke="{color}" stroke-width="3"/>')
        parts.append(svg_text(x + 28, legend_y + 4, family, 12))
        offset += max(108, len(family) * 8 + 48)
    parts.append("</svg>")
    svg_path = curve_dir / "by_task_and_family.svg"
    svg_path.write_text("\n".join(parts) + "\n", encoding="utf-8")

    png_path = curve_dir / "by_task_and_family.png"
    try:
        subprocess.run(
            ["convert", str(svg_path), str(png_path)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except Exception:
        if png_path.exists():
            png_path.unlink()


def write_docs(out_root: Path, rows: list[Row], summary: list[dict], generated_at: str) -> None:
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
        "- `results/family_summary_gptoss.md`: model-family summary.",
        "- `results/family_summary_gptoss.json`: machine-readable family summary.",
        "- `results/scaling_curves/by_task_and_family.svg`: scaling-curve plot.",
        "- `results/scaling_curves/by_task_and_family.png`: rendered scaling-curve image.",
        "- `results/scaling_curves/by_task_and_family.json`: plot source data.",
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
        "## Scaling Curves",
        "",
        "![Scaling curves by task and family](../results/scaling_curves/by_task_and_family.png)",
        "",
        "The plotted image emphasizes multi-size families with at least two parameter points.",
        "The JSON artifact contains all task-family points used for the plot.",
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
    summary = write_family_summary(rows, results_dir, generated_at)
    write_scaling_artifacts(rows, results_dir, generated_at)
    write_docs(output_root, rows, summary, generated_at)


if __name__ == "__main__":
    main()
