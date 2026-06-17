---
layout: home
title: JaWildText Evaluation
---

# JaWildText Evaluation

JaWildText is a benchmark for Japanese wild-text understanding with three complementary tasks: Dense STVQA, Receipt KIE, and Handwriting OCR.

This site is the public evaluation companion for the release repository. It follows the same information architecture as public LLM evaluation pages such as the [Swallow evaluation overview](https://swallow-llm.github.io/evaluation/about.ja.html): motivation, task descriptions, evaluation tools, model coverage, result tables, and visual summaries are documented in separate but linked sections.

## What This Site Documents

- Motivation: why Japanese wild-text understanding needs a dedicated benchmark.
- Tasks: Dense STVQA, Receipt KIE, and Handwriting OCR.
- Evaluation protocol: prompts, normalization, metrics, and judge provenance.
- Model coverage: main-paper models and extended leaderboard models are separated.
- Results: Markdown tables, machine-readable JSON, and matplotlib visual summaries.

## Pages

- [Evaluation Protocol](evaluation.md): task definitions, prompts, metrics, and judge provenance.
- [Leaderboard](leaderboard.md): Markdown tables and generated matplotlib visualizations.
- [Extended Results](extended_results.md): extended aggregate leaderboard and coverage notes.
- [Result Schema](result_schema.md): machine-readable aggregate result schema.
- [Release Results](results.md): provenance notes and included artifacts.

## Result Artifacts

- [`results/main_results.md`](https://github.com/llm-jp/jawildtext/blob/main/results/main_results.md): main 14-model benchmark table.
- [`results/extended_leaderboard_gptoss.md`](https://github.com/llm-jp/jawildtext/blob/main/results/extended_leaderboard_gptoss.md): extended leaderboard using the public gpt-oss Dense STVQA judge root.
- [`results/family_summary_gptoss.md`](https://github.com/llm-jp/jawildtext/blob/main/results/family_summary_gptoss.md): model-family aggregate summary.

## Deployment

The repository includes a GitHub Pages workflow that builds this `docs/` directory with Jekyll and deploys it from GitHub Actions.
