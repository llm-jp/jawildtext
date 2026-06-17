#!/usr/bin/env python3
"""Build GitHub Pages tables and figures for JaWildText results."""

from __future__ import annotations

import argparse
import html
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


def extended_table(extended_payload: dict, limit: int | None = None) -> str:
    rows = []
    source_rows = extended_payload["results"] if limit is None else extended_payload["results"][:limit]
    for rank, row in enumerate(source_rows, start=1):
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
    ]
    (docs_dir / "leaderboard.md").write_text("\n".join(page), encoding="utf-8")


def html_score(value: float | None) -> str:
    return "--" if value is None else f"{value:.3f}"


def index_result_rows(extended_payload: dict) -> str:
    table_rows = []
    for rank, row in enumerate(extended_payload["results"], start=1):
        scores = row.get("scores", {})
        table_rows.append(
            "              <tr>\n"
            f"                <td class=\"is-number\">{rank}</td>\n"
            f"                <td>{html.escape(row['display_name'])}</td>\n"
            f"                <td>{html.escape(row['family'])}</td>\n"
            f"                <td class=\"is-number\">{html_score(row.get('mean_score'))}</td>\n"
            f"                <td class=\"is-number\">{html_score(scores.get('dense_stvqa_gptoss'))}</td>\n"
            f"                <td class=\"is-number\">{html_score(scores.get('handwriting_ocr'))}</td>\n"
            f"                <td class=\"is-number\">{html_score(scores.get('receipt_kie'))}</td>\n"
            f"                <td class=\"is-number\">{len(scores)}</td>\n"
            "              </tr>"
        )
    return "\n".join(table_rows)


def write_index(output_root: Path, extended_payload: dict) -> None:
    docs_dir = output_root / "docs"
    rows = extended_payload["results"]
    dense_count = sum(1 for row in rows if "dense_stvqa_gptoss" in row.get("scores", {}))
    handwriting_count = sum(1 for row in rows if "handwriting_ocr" in row.get("scores", {}))
    receipt_count = sum(1 for row in rows if "receipt_kie" in row.get("scores", {}))
    complete_count = sum(1 for row in rows if len(row.get("scores", {})) == len(EXTENDED_TASK_COLUMNS))
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="title" content="JaWildText: Japanese Scene Text Understanding Benchmark">
  <meta name="description" content="Project page for JaWildText, a benchmark for Japanese scene text understanding with Dense STVQA, Receipt KIE, and Handwriting OCR tasks.">
  <meta name="keywords" content="JaWildText, Japanese OCR, scene text VQA, document AI, multimodal evaluation, VLM benchmark">
  <meta name="author" content="Koki Maeda, Naoaki Okazaki">
  <meta property="og:type" content="article">
  <meta property="og:site_name" content="LLM-jp">
  <meta property="og:title" content="JaWildText">
  <meta property="og:description" content="A benchmark for Japanese scene text understanding across Dense STVQA, Receipt KIE, and Handwriting OCR.">
  <meta property="og:url" content="https://llm-jp.github.io/jawildtext/">
  <meta name="twitter:card" content="summary">
  <title>JaWildText | Japanese Scene Text Understanding Benchmark</title>
  <link rel="stylesheet" href="static/css/bulma.min.css">
  <link rel="stylesheet" href="static/css/jawildtext.css">
</head>
<body>
  <nav class="navbar is-white project-nav" aria-label="main navigation">
    <div class="container">
      <div class="navbar-brand">
        <a class="navbar-item" href="./">JaWildText</a>
      </div>
      <div class="navbar-menu is-active">
        <div class="navbar-end">
          <a class="navbar-item" href="#abstract">Abstract</a>
          <a class="navbar-item" href="#dataset">Dataset</a>
          <a class="navbar-item" href="#results">Results</a>
          <a class="navbar-item" href="#analysis">Analysis</a>
          <a class="navbar-item" href="#leaderboard">Leaderboard</a>
          <a class="navbar-item" href="#citation">BibTeX</a>
          <a class="navbar-item" href="evaluation.html">Evaluation</a>
          <a class="navbar-item" href="https://github.com/llm-jp/jawildtext">GitHub</a>
        </div>
      </div>
    </div>
  </nav>

  <main>
    <section class="hero publication-hero">
      <div class="hero-body">
        <div class="container is-max-desktop has-text-centered">
          <h1 class="publication-title">JaWildText</h1>
          <p class="publication-subtitle">
            A Benchmark for Vision-Language Models on Japanese Scene Text Understanding
          </p>
          <div class="author-line">
            <a class="author-link" href="https://silviase.com">Koki Maeda</a> · Naoaki Okazaki
          </div>
          <div class="venue-line">ICDAR 2026 (to appear) · arXiv:2603.27942</div>
          <div class="publication-links">
            <a class="button is-jawild" href="https://arxiv.org/abs/2603.27942">Paper</a>
            <a class="button is-outline-jawild" href="https://arxiv.org/pdf/2603.27942">PDF</a>
            <a class="button is-outline-jawild" href="https://github.com/llm-jp/jawildtext">GitHub</a>
            <a class="button is-outline-jawild" href="https://huggingface.co/datasets/llm-jp/jawildtext">Dataset</a>
            <a class="button is-outline-jawild" href="evaluation.html">Evaluation</a>
          </div>
          <p class="paper-meta">
            3,241 instances · 2,961 images · 1.12M annotated characters · 3,643 character types
          </p>
          <figure class="publication-banner">
            <img src="assets/jawildtext_figure_1.png" alt="JaWildText task overview">
            <figcaption>JaWildText evaluates Dense STVQA, Receipt KIE, and Handwriting OCR on Japanese wild text.</figcaption>
          </figure>
          <p class="hero-summary">
            Japanese scene text mixes kanji, kana, Latin characters, vertical layouts, handwriting,
            receipts, signs, and dense public notices. JaWildText turns those conditions into a
            diagnostic benchmark that separates recognition, reasoning, and formatting failures.
          </p>
        </div>
      </div>
    </section>

    <section class="section" id="abstract">
      <div class="container is-max-desktop">
        <h2 class="section-title">Abstract</h2>
        <p class="section-copy">
          JaWildText is a benchmark for evaluating how well vision-language models understand
          Japanese scene text in real-world images. The benchmark contains <strong>3,241 instances</strong>
          from <strong>2,961 images</strong>, with <strong>1.12 million annotated characters</strong> across
          <strong>3,643 unique character types</strong>. It combines Dense Scene Text VQA,
          Receipt Key Information Extraction, and Handwriting OCR so that failures can be traced
          to recognition, reasoning, or output-formatting errors. Experiments on 14 open-weight
          VLMs show that even the best model reaches only a <strong>0.64 average score</strong>,
          with kanji recognition emerging as the largest bottleneck.
        </p>
      </div>
    </section>

    <section class="section is-soft" id="dataset">
      <div class="container is-max-desktop">
        <h2 class="section-title">JaWildText Tasks</h2>
        <figure class="project-figure wide-figure">
          <img src="assets/jawildtext_figure_2.png" alt="Examples from the three JaWildText task subsets">
        </figure>
        <p class="section-copy">
          Dense STVQA covers text-rich real-world images such as signs, posters, packages, and
          bulletin boards. Receipt KIE evaluates structured extraction from Japanese receipts.
          Handwriting OCR tests page-level transcription across paper, whiteboards, and tablets,
          including horizontal and vertical writing.
        </p>
        <div class="task-list">
          <div class="task-card">
            <h3>Dense STVQA</h3>
            <p>Open-ended visual question answering over dense Japanese scene text.</p>
          </div>
          <div class="task-card">
            <h3>Receipt KIE</h3>
            <p>JSON-style extraction of store, date, total, tax, and line-item fields.</p>
          </div>
          <div class="task-card">
            <h3>Handwriting OCR</h3>
            <p>Full-page transcription scored by normalized character error rate.</p>
          </div>
        </div>
      </div>
    </section>

    <section class="section" id="statistics">
      <div class="container is-max-desktop">
        <h2 class="section-title">Dataset Statistics</h2>
        <div class="figure-grid">
          <figure class="project-figure">
            <img src="assets/jawildtext_figure_3a.png" alt="Annotated character counts by image">
          </figure>
          <figure class="project-figure">
            <img src="assets/jawildtext_figure_3b.png" alt="Text density distributions by task">
          </figure>
        </div>
        <figure class="project-figure wide-figure">
          <img src="assets/jawildtext_figure_4.png" alt="Character type composition by JaWildText subset">
        </figure>
        <p class="section-copy">
          JaWildText contains <strong>95,705 text regions</strong> and covers
          <strong>1,985 of 2,136 Joyo kanji</strong> plus <strong>881 non-Joyo kanji</strong>.
          The subsets stress different mixtures of kanji, kana, digits, Latin characters,
          short dense notices, long receipts, and free-form handwriting.
        </p>
      </div>
    </section>

    <section class="section" id="results">
      <div class="container is-max-desktop">
        <h2 class="section-title">Main Results</h2>
        <figure class="project-figure wide-figure">
          <img src="assets/jawildtext_figure_5.png" alt="Main JaWildText model results by task and model size">
        </figure>
        <p class="section-copy">
          The main paper evaluates 14 open-weight VLMs with task-specific prompts and scoring:
          LLM-based binary judging for Dense STVQA, token-level F1 for Receipt KIE, and
          character-level similarity for Handwriting OCR. Larger models help, but the gap to
          reliable Japanese wild-text understanding remains substantial.
        </p>
      </div>
    </section>

    <section class="section is-soft" id="analysis">
      <div class="container is-max-desktop">
        <h2 class="section-title">Error Analysis</h2>
        <div class="figure-grid">
          <figure class="project-figure">
            <img src="assets/jawildtext_figure_6.png" alt="Dense STVQA error analysis">
          </figure>
          <figure class="project-figure">
            <img src="assets/jawildtext_figure_7.png" alt="Handwriting OCR character-type CER analysis">
          </figure>
        </div>
        <figure class="project-figure wide-figure">
          <img src="assets/jawildtext_figure_8.png" alt="Representative Handwriting OCR failure cases">
        </figure>
        <p class="section-copy">
          Recognition errors dominate Dense STVQA failures, while Handwriting OCR exposes
          character-level weaknesses for kanji and visually similar scripts. These analyses
          make JaWildText a diagnostic benchmark rather than only a leaderboard.
        </p>
      </div>
    </section>

    <section class="section" id="leaderboard">
      <div class="container content-frame">
        <h2 class="section-title">Extended Leaderboard</h2>
        <p class="lead">
          The public extended export lists {len(rows)} models. Dense STVQA uses the <code>jawildtext-board-vqa-gptoss</code>
          result root with <code>openai/gpt-oss-20b</code> as verifier; Handwriting OCR and Receipt KIE use task-specific scorers.
        </p>
        <div class="stat-grid compact-stats" aria-label="Extended result coverage">
          <div class="stat-card"><span class="stat-value">{dense_count}</span><span class="stat-label">Dense STVQA gpt-oss</span></div>
          <div class="stat-card"><span class="stat-value">{handwriting_count}</span><span class="stat-label">Handwriting OCR</span></div>
          <div class="stat-card"><span class="stat-value">{receipt_count}</span><span class="stat-label">Receipt KIE</span></div>
          <div class="stat-card"><span class="stat-value">{complete_count}</span><span class="stat-label">All three columns</span></div>
        </div>
        <div class="table-wrap">
          <table class="leaderboard-table">
            <thead>
              <tr>
                <th class="is-number">Rank</th>
                <th>Model</th>
                <th>Family</th>
                <th class="is-number">Mean</th>
                <th class="is-number">Dense STVQA</th>
                <th class="is-number">Handwriting OCR</th>
                <th class="is-number">Receipt KIE</th>
                <th class="is-number">Tasks</th>
              </tr>
            </thead>
            <tbody>
{index_result_rows(extended_payload)}
            </tbody>
          </table>
        </div>
        <p class="note">
          Machine-readable rows are available in
          <a href="https://github.com/llm-jp/jawildtext/blob/main/results/extended_leaderboard_gptoss.json">extended_leaderboard_gptoss.json</a>.
          The count of {complete_count} complete rows means all three aggregate columns are available; it does not mean all three tasks were judged by gpt-oss.
        </p>
      </div>
    </section>

    <section class="section is-soft" id="citation">
      <div class="container is-max-desktop">
        <h2 class="section-title">BibTeX</h2>
        <p class="lead">Please cite the paper when using JaWildText or the released evaluation artifacts.</p>
        <pre class="bibtex"><code>@inproceedings{{maeda-etal-2026-jawildtext,
  title     = {{{{JaWildText}}: A Benchmark for Vision-Language Models on Japanese Scene Text Understanding}},
  author    = {{Maeda, Koki and Okazaki, Naoaki}},
  booktitle = {{Proceedings of the 20th International Conference on Document Analysis and Recognition (ICDAR)}},
  year      = {{2026}},
  note      = {{To appear}}
}}</code></pre>
      </div>
    </section>
  </main>

  <footer class="footer">
    <div class="container is-max-desktop">
      <p>
        JaWildText release materials are maintained in
        <a href="https://github.com/llm-jp/jawildtext">llm-jp/jawildtext</a>.
        The project-page layout is inspired by the
        <a href="https://github.com/eliahuhorwitz/Academic-project-page-template">Academic Project Page Template</a>.
      </p>
    </div>
  </footer>
</body>
</html>
"""
    (docs_dir / "index.html").write_text(page, encoding="utf-8")


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

    save_main_heatmap(main_payload, assets_dir / "main_results_heatmap.png")
    save_extended_top_bar(extended_payload, assets_dir / "extended_top_models.png")
    write_leaderboard_page(output_root, main_payload, extended_payload)
    write_index(output_root, extended_payload)


if __name__ == "__main__":
    main()
