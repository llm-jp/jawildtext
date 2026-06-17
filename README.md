<img width="900" alt="スクリーンショット 2026-06-08 9 40 24" src="https://github.com/user-attachments/assets/b2d59921-f631-44c2-a418-154d106d8089" />

# JaWildText

JaWildText is a benchmark for evaluating vision-language models on Japanese wild-text understanding. It covers three complementary tasks: Dense Scene Text Visual Question Answering (Dense STVQA), Receipt Key Information Extraction (Receipt KIE), and Handwriting OCR.

The dataset is hosted on Hugging Face Datasets:

- https://huggingface.co/datasets/llm-jp/jawildtext

This repository is the release bundle for evaluation documentation, prompts, result summaries, and reproducibility metadata. It does not duplicate the dataset files and must not include run logs, scheduler logs, private logs, local `.env` files, or raw temporary experiment dumps.

## Contents

- `docs/index.html`: GitHub Pages project-page entry point.
- `docs/evaluation.md`: task definitions, prompts, and scoring protocol.
- `docs/leaderboard.md`: public tables and generated visual summaries.
- `docs/results.md`: benchmark result summary and provenance notes.
- `docs/extended_results.md`: extended leaderboard coverage summary.
- `docs/result_schema.md`: expected aggregate result schema.
- `docs/assets/`: generated matplotlib figures for public pages.
- `results/main_results.md`: main benchmark table.
- `results/main_results.json`: machine-readable main benchmark table.
- `results/receipt_kie_fields.md`: Receipt KIE field-level table.
- `results/extended_leaderboard_gptoss.md`: extended aggregate table with Dense STVQA re-judged by `gpt-oss-20b`.
- `scripts/build_pages_assets.py`: regenerates GitHub Pages tables and figures from `results/*.json`.
- `scripts/export_extended_results.py`: regenerates extended result artifacts from aggregate eval outputs.

## Dataset

Use Hugging Face Datasets to load JaWildText:

```python
from datasets import load_dataset

ds = load_dataset("llm-jp/jawildtext", "board_vqa", split="train")
```

Available configs:

- `default`: union of all task examples.
- `board_vqa`: Dense STVQA examples.
- `handwriting_ocr`: Handwriting OCR examples.
- `receipt_kie`: Receipt KIE examples.

Although the Hugging Face split is named `train`, JaWildText is intended as an evaluation benchmark.

## Evaluation Code

The JaWildText integration for `llm-jp-eval-mm` is being prepared on the evaluation framework side. The current integration candidate is the `jawildtext-board-vqa`, `jawildtext-handwriting-ocr`, and `jawildtext-receipt-kie` tasks in `llm-jp/llm-jp-eval-mm`.

This release bundle records the public evaluation protocol. The runnable evaluator should be cited with its exact commit once merged.

## Log Policy

Do not add logs to this repository. In particular, exclude:

- run logs
- scheduler logs
- private/debug logs
- local `.env` files
- machine-specific paths
- raw `tmp/` or experiment dump directories

Aggregate result tables and documented prompts are allowed.

## GitHub Pages

The public site is served from the `/docs` folder on the `main` branch. The landing page follows an academic project-page layout, while result figures are generated from the checked-in result JSON files:

```bash
python scripts/build_pages_assets.py --output-root .
```

The GitHub Pages repository setting should use `main` / `docs` as the publishing source.

## License

This repository is released under the Apache License 2.0. The dataset page also records the dataset license and usage notes.

## Citation

```bibtex
@inproceedings{maeda-etal-2026-jawildtext,
  title     = {{JaWildText}: A Benchmark for Vision-Language Models on Japanese Scene Text Understanding},
  author    = {Maeda, Koki and Okazaki, Naoaki},
  booktitle = {Proceedings of the 20th International Conference on Document Analysis and Recognition (ICDAR)},
  year      = {2026},
  note      = {To appear}
}
```
