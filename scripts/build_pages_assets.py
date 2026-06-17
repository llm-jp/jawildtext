#!/usr/bin/env python3
"""Build GitHub Pages tables and figures for JaWildText results."""

from __future__ import annotations

import argparse
import json
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    import seaborn as sns
except Exception:  # pragma: no cover - optional styling dependency
    sns = None


TASK_COLUMNS = [
    ("dense_stvqa", "Dense STVQA"),
    ("handwriting_ocr", "Handwriting OCR"),
    ("receipt_kie", "Receipt KIE"),
]

EXTENDED_TASK_COLUMNS = [
    ("dense_stvqa_gptoss", "Dense STVQA"),
    ("handwriting_ocr", "Handwriting OCR"),
    ("receipt_kie", "Receipt KIE"),
]

REPO_BLOB_ROOT = "https://github.com/llm-jp/jawildtext/blob/main"
SWALLOW_EVAL_URL = "https://swallow-llm.github.io/evaluation/about.ja.html"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fmt_score(value: float | None) -> str:
    return "--" if value is None else f"{value:.3f}"


def markdown_table(headers: list[str], rows: list[list[str]], align: list[str]) -> str:
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join(align) + " |")
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def wrap_labels(labels: list[str], width: int = 22) -> list[str]:
    return ["\n".join(textwrap.wrap(label, width=width, break_long_words=False)) for label in labels]


def set_style() -> None:
    if sns is not None:
        sns.set_theme(style="whitegrid", context="notebook")
    else:
        plt.rcParams.update(
            {
                "axes.spines.top": False,
                "axes.spines.right": False,
                "axes.grid": True,
                "grid.alpha": 0.24,
                "figure.facecolor": "white",
                "axes.facecolor": "white",
            }
        )


def save_main_heatmap(main_payload: dict, out_path: Path) -> None:
    rows = main_payload["results"]
    labels = [row["model"] for row in rows]
    values = [[row[key] for key, _ in TASK_COLUMNS] for row in rows]

    fig, ax = plt.subplots(figsize=(8.5, 7.2))
    if sns is not None:
        sns.heatmap(
            values,
            ax=ax,
            annot=True,
            fmt=".2f",
            cmap="viridis",
            vmin=0,
            vmax=1,
            cbar_kws={"label": "Score"},
            xticklabels=[label for _, label in TASK_COLUMNS],
            yticklabels=wrap_labels(labels, 24),
        )
    else:
        image = ax.imshow(values, aspect="auto", cmap="viridis", vmin=0, vmax=1)
        fig.colorbar(image, ax=ax, label="Score")
        ax.set_xticks(range(len(TASK_COLUMNS)), [label for _, label in TASK_COLUMNS])
        ax.set_yticks(range(len(labels)), wrap_labels(labels, 24))
        for y, row_values in enumerate(values):
            for x, value in enumerate(row_values):
                ax.text(x, y, f"{value:.2f}", ha="center", va="center", color="white", fontsize=8)
    ax.set_title("JaWildText Main Results by Task", pad=14, weight="bold")
    ax.set_xlabel("")
    ax.set_ylabel("")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def save_extended_top_bar(extended_payload: dict, out_path: Path, limit: int = 12) -> None:
    rows = [row for row in extended_payload["results"] if row.get("mean_score") is not None][:limit]
    rows = list(reversed(rows))
    labels = [row["display_name"] for row in rows]
    values = [row["mean_score"] for row in rows]

    fig, ax = plt.subplots(figsize=(8.5, 6.2))
    colors = plt.cm.mako(values) if sns is not None else plt.cm.viridis(values)
    ax.barh(wrap_labels(labels, 28), values, color=colors)
    ax.set_xlim(0, 1)
    ax.set_xlabel("Mean score over available tasks")
    ax.set_title("Extended Leaderboard: Top Models", pad=12, weight="bold")
    for y, value in enumerate(values):
        ax.text(min(value + 0.015, 0.98), y, f"{value:.3f}", va="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def save_family_bar(family_payload: dict, out_path: Path, limit: int = 12) -> None:
    rows = [
        item
        for item in family_payload["families"]
        if item.get("mean_available_score") is not None
    ][:limit]
    rows = list(reversed(rows))
    labels = [item["family"] for item in rows]
    values = [item["mean_available_score"] for item in rows]
    counts = [item["models"] for item in rows]

    fig, ax = plt.subplots(figsize=(8.5, 5.8))
    ax.barh(labels, values, color="#2f6f73")
    ax.set_xlim(0, 1)
    ax.set_xlabel("Mean score over available task scores")
    ax.set_title("Model-Family Summary", pad=12, weight="bold")
    for y, (value, count) in enumerate(zip(values, counts, strict=True)):
        ax.text(min(value + 0.015, 0.98), y, f"{value:.3f} ({count} models)", va="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def main_table(main_payload: dict) -> str:
    rows = []
    for row in main_payload["results"]:
        rows.append(
            [
                row["model"],
                row["params"],
                fmt_score(row["overall"]),
                fmt_score(row["dense_stvqa"]),
                fmt_score(row["handwriting_ocr"]),
                fmt_score(row["receipt_kie"]),
            ]
        )
    return markdown_table(
        ["Model", "Params", "Overall", "Dense STVQA", "Handwriting OCR", "Receipt KIE"],
        rows,
        [":---", "---:", "---:", "---:", "---:", "---:"],
    )


def extended_table(extended_payload: dict, limit: int = 20) -> str:
    rows = []
    for rank, row in enumerate(extended_payload["results"][:limit], start=1):
        scores = row.get("scores", {})
        rows.append(
            [
                str(rank),
                row["display_name"],
                row["family"],
                fmt_score(row.get("mean_score")),
                fmt_score(scores.get("dense_stvqa_gptoss")),
                fmt_score(scores.get("handwriting_ocr")),
                fmt_score(scores.get("receipt_kie")),
            ]
        )
    return markdown_table(
        ["Rank", "Model", "Family", "Mean", "Dense STVQA", "Handwriting OCR", "Receipt KIE"],
        rows,
        [":---:", ":---", ":---", "---:", "---:", "---:", "---:"],
    )


def coverage_table(extended_payload: dict) -> str:
    rows = []
    for key, label in EXTENDED_TASK_COLUMNS:
        rows.append([label, str(sum(1 for row in extended_payload["results"] if key in row.get("scores", {})))])
    rows.append(["Any JaWildText aggregate score", str(len(extended_payload["results"]))])
    return markdown_table(["Coverage item", "Models"], rows, [":---", "---:"])


def write_leaderboard_page(output_root: Path, main_payload: dict, extended_payload: dict) -> None:
    docs_dir = output_root / "docs"
    page = [
        "---",
        "layout: page",
        "title: Leaderboard",
        "---",
        "",
        "# Leaderboard",
        "",
        "This page collects public JaWildText result tables and visual summaries.",
        "The layout is designed to mirror common evaluation pages: task definitions, model coverage, aggregate tables, and task-wise visual comparisons are kept close together.",
        "",
        "## Main Paper Table",
        "",
        "The main table covers the 14-model set used in the JaWildText paper.",
        "",
        "![Main task heatmap](assets/main_results_heatmap.png)",
        "",
        main_table(main_payload),
        "",
        "## Extended Leaderboard",
        "",
        "The extended leaderboard uses `jawildtext-board-vqa-gptoss` for the Dense STVQA column, with `openai/gpt-oss-20b` as the verifier.",
        "It is intentionally kept separate from the main-paper Dense STVQA setting.",
        "",
        "![Extended top models](assets/extended_top_models.png)",
        "",
        extended_table(extended_payload),
        "",
        f"Full machine-readable rows are available in [`results/extended_leaderboard_gptoss.json`]({REPO_BLOB_ROOT}/results/extended_leaderboard_gptoss.json).",
        "",
        "## Coverage",
        "",
        coverage_table(extended_payload),
        "",
        "## Family View",
        "",
        "![Model-family summary](assets/family_summary.png)",
        "",
    ]
    (docs_dir / "leaderboard.md").write_text("\n".join(page), encoding="utf-8")


def write_index(output_root: Path) -> None:
    docs_dir = output_root / "docs"
    page = [
        "---",
        "layout: home",
        "title: JaWildText Evaluation",
        "---",
        "",
        "# JaWildText Evaluation",
        "",
        "JaWildText is a benchmark for Japanese wild-text understanding with three complementary tasks: Dense STVQA, Receipt KIE, and Handwriting OCR.",
        "",
        f"This site is the public evaluation companion for the release repository. It follows the same information architecture as public LLM evaluation pages such as the [Swallow evaluation overview]({SWALLOW_EVAL_URL}): motivation, task descriptions, evaluation tools, model coverage, result tables, and visual summaries are documented in separate but linked sections.",
        "",
        "## What This Site Documents",
        "",
        "- Motivation: why Japanese wild-text understanding needs a dedicated benchmark.",
        "- Tasks: Dense STVQA, Receipt KIE, and Handwriting OCR.",
        "- Evaluation protocol: prompts, normalization, metrics, and judge provenance.",
        "- Model coverage: main-paper models and extended leaderboard models are separated.",
        "- Results: Markdown tables, machine-readable JSON, and matplotlib visual summaries.",
        "",
        "## Pages",
        "",
        "- [Evaluation Protocol](evaluation.md): task definitions, prompts, metrics, and judge provenance.",
        "- [Leaderboard](leaderboard.md): Markdown tables and generated matplotlib visualizations.",
        "- [Extended Results](extended_results.md): extended aggregate leaderboard and coverage notes.",
        "- [Result Schema](result_schema.md): machine-readable aggregate result schema.",
        "- [Release Results](results.md): provenance notes and included artifacts.",
        "",
        "## Result Artifacts",
        "",
        f"- [`results/main_results.md`]({REPO_BLOB_ROOT}/results/main_results.md): main 14-model benchmark table.",
        f"- [`results/extended_leaderboard_gptoss.md`]({REPO_BLOB_ROOT}/results/extended_leaderboard_gptoss.md): extended leaderboard using the public gpt-oss Dense STVQA judge root.",
        f"- [`results/family_summary_gptoss.md`]({REPO_BLOB_ROOT}/results/family_summary_gptoss.md): model-family aggregate summary.",
        "",
        "## Deployment",
        "",
        "The repository includes a GitHub Pages workflow that builds this `docs/` directory with Jekyll and deploys it from GitHub Actions.",
        "",
    ]
    (docs_dir / "index.md").write_text("\n".join(page), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=Path("."))
    args = parser.parse_args()

    output_root = args.output_root.resolve()
    docs_dir = output_root / "docs"
    assets_dir = docs_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    set_style()

    main_payload = load_json(output_root / "results" / "main_results.json")
    extended_payload = load_json(output_root / "results" / "extended_leaderboard_gptoss.json")
    family_payload = load_json(output_root / "results" / "family_summary_gptoss.json")

    save_main_heatmap(main_payload, assets_dir / "main_results_heatmap.png")
    save_extended_top_bar(extended_payload, assets_dir / "extended_top_models.png")
    save_family_bar(family_payload, assets_dir / "family_summary.png")
    write_leaderboard_page(output_root, main_payload, extended_payload)
    write_index(output_root)


if __name__ == "__main__":
    main()
