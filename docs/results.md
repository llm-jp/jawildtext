# Results

This release bundle currently records the 14-model main benchmark table used for the JaWildText paper. Extended leaderboard artifacts should be kept separate unless the exact shared model set and judge provenance are documented.

## Result Roots

Local provenance roots used during release preparation:

| Root | Intended use |
|---|---|
| `jawildtext-board-vqa` | Base Dense STVQA results |
| `jawildtext-board-vqa-gptoss` | Public Dense STVQA judge setting using `openai/gpt-oss-20b` |
| `jawildtext-board-vqa-gpt51` | Older/intermediate re-judged root; not the public judge setting |
| `jawildtext-handwriting-ocr` | Handwriting OCR aggregate root |
| `jawildtext-receipt-kie` | Receipt KIE aggregate root |

## Public Judge Provenance

Dense STVQA public judge:

```json
{
  "judge_model": "openai/gpt-oss-20b",
  "reasoning_effort": "low"
}
```

## Included Tables

- `results/main_results.md`
- `results/main_results.json`
- `results/receipt_kie_fields.md`
- `results/extended_leaderboard_gptoss.md`
- `results/extended_leaderboard_gptoss.json`
- `results/family_summary_gptoss.md`
- `results/family_summary_gptoss.json`

See `docs/extended_results.md` for the extended leaderboard and model-family summary.

Raw logs are intentionally excluded.
