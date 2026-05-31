# Main Results

| Model | Params | Overall | Dense STVQA | Handwriting OCR | Receipt KIE |
|---|---:|---:|---:|---:|---:|
| Qwen3-VL-8B | 8B | 0.64 | 0.62 | 0.79 | 0.53 |
| Qwen3-VL-4B | 4B | 0.60 | 0.52 | 0.77 | 0.50 |
| InternVL3.5-38B | 38B | 0.55 | 0.44 | 0.71 | 0.50 |
| InternVL3.5-8B | 8B | 0.53 | 0.39 | 0.72 | 0.48 |
| Qwen3-VL-2B | 2B | 0.52 | 0.31 | 0.76 | 0.48 |
| Sarashina2.2-3B | 3B | 0.50 | 0.44 | 0.68 | 0.40 |
| InternVL3.5-14B | 14B | 0.49 | 0.30 | 0.71 | 0.47 |
| InternVL3.5-4B | 4B | 0.48 | 0.31 | 0.70 | 0.44 |
| InternVL3.5-2B | 2B | 0.44 | 0.23 | 0.66 | 0.42 |
| Gemma3-27B-IT | 27B | 0.43 | 0.37 | 0.53 | 0.39 |
| Gemma3-12B-IT | 12B | 0.40 | 0.32 | 0.51 | 0.38 |
| InternVL3.5-1B | 1B | 0.37 | 0.11 | 0.61 | 0.37 |
| Gemma3-4B-IT | 4B | 0.19 | 0.12 | 0.20 | 0.23 |
| Phi-4-multimodal | 14B | 0.18 | 0.008 | 0.29 | 0.23 |

Dense STVQA uses judge accuracy. Handwriting OCR uses `max(0, 1 - CER)`. Receipt KIE uses field/value F1. Overall is the unweighted average of the three task scores.

