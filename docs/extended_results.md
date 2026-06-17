# Extended Results

Generated at: `2026-06-17T07:36:52+00:00`

This page documents extended JaWildText aggregate results beyond the 14-model main-paper table.
Dense STVQA scores in these artifacts use `openai/gpt-oss-20b` with `reasoning_effort=low` as the public verifier.
Handwriting OCR and Receipt KIE use the standard task scorers.

## Artifacts

- `results/extended_leaderboard_gptoss.md`: full aggregate table.
- `results/extended_leaderboard_gptoss.json`: machine-readable rows with source roots.
- `results/family_summary_gptoss.md`: model-family summary.
- `results/family_summary_gptoss.json`: machine-readable family summary.

## Coverage

| Artifact | Rows |
| :--- | ---: |
| Models with at least one JaWildText aggregate score | 76 |
| Models with all three task scores in this export | 68 |
| Dense STVQA gpt-oss aggregate scores | 72 |
| Handwriting OCR aggregate scores | 73 |
| Receipt KIE aggregate scores | 68 |

## Provenance

| Task | Result root | Metric |
| :--- | :--- | :--- |
| Dense STVQA | jawildtext-board-vqa-gptoss | accuracy |
| Handwriting OCR | jawildtext-handwriting-ocr | 1 - CER |
| Receipt KIE | jawildtext-receipt-kie | field/value F1 |

`jawildtext-board-vqa-gpt51` is not used for the public Dense STVQA column in these artifacts.
Raw prediction files and run logs are intentionally excluded.
