# Evaluation Protocol

JaWildText evaluates three Japanese wild-text understanding tasks. The dataset source is Hugging Face Datasets `llm-jp/jawildtext`.

## Dense STVQA (`board_vqa`)

Dense STVQA evaluates question answering over text-rich real-world images such as signs, boards, posters, and packages.

### Inference Prompt

For each example, the model receives the question followed by this instruction:

```text
画像を参照して回答してください。推論過程は出力しても構いませんが、最終回答は必ず \boxed{...} で囲み、ボックス内には最終回答のみを1つだけ記載してください。
```

The evaluator extracts the final boxed answer according to the release evaluator implementation. If the output cannot be parsed as a boxed answer, the example receives 0.

### Judge

Public Dense STVQA provenance should use:

```json
{
  "judge_model": "openai/gpt-oss-20b",
  "reasoning_effort": "low"
}
```

The binary judge prompt compares the question, gold answer, and model prediction. The judge must answer only:

```text
correct: yes
```

or

```text
correct: no
```

The Dense STVQA score is binary judge accuracy.

## Handwriting OCR (`handwriting_ocr`)

Handwriting OCR evaluates transcription of handwritten Japanese text.

The model is prompted to read all text in the image and preserve line breaks. Before scoring, text is normalized with Unicode NFKC normalization and newline/space normalization.

The score is:

```text
max(0, 1 - CER)
```

where CER is the Levenshtein distance between prediction and reference divided by the reference length.

## Receipt KIE (`receipt_kie`)

Receipt KIE evaluates structured information extraction from Japanese receipt images.

The model is prompted to output a JSON object with the following fields:

- `store_name`
- `store_address`
- `receipt_id`
- `date`
- `time`
- `total_amount`
- `tax_amount`
- `line_items[]`

Each line item can contain:

- `item_name`
- `item_price`
- `item_quantity`

Invalid JSON receives 0 for the F1 score. Field values are normalized with Unicode NFKC normalization, lowercasing, whitespace normalization, and removal of yen symbols and thousands separators before comparison.

The main Receipt KIE score is token-level field/value F1. Field-level accuracy is computed for scalar fields present in the gold answer.

## Overall Score

The overall JaWildText score is the unweighted average of:

- Dense STVQA judge accuracy
- Receipt KIE F1
- Handwriting OCR `1 - CER`

