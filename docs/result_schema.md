# Result Schema

Aggregate result files in this repository should be stable, compact, and free of local execution logs.

## `results/main_results.json`

Top-level object:

```json
{
  "dataset": "llm-jp/jawildtext",
  "tasks": ["board_vqa", "handwriting_ocr", "receipt_kie"],
  "dense_stvqa_judge": {
    "judge_model": "openai/gpt-oss-20b",
    "reasoning_effort": "low"
  },
  "metrics": {
    "overall": "unweighted average",
    "dense_stvqa": "judge accuracy",
    "handwriting_ocr": "max(0, 1 - CER)",
    "receipt_kie": "field/value F1"
  },
  "results": []
}
```

Each result entry:

```json
{
  "model": "Qwen3-VL-8B",
  "params": "8B",
  "overall": 0.64,
  "dense_stvqa": 0.62,
  "handwriting_ocr": 0.79,
  "receipt_kie": 0.53
}
```

## Excluded Artifacts

Do not include:

- raw run logs
- scheduler logs
- private/debug logs
- `.env` files
- raw temporary experiment directories
- machine-specific paths

