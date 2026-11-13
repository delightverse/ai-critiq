# Results summary

Positive class = an explanation that contains an error. **TPR** (errors caught) and **TNR** (correct work accepted) are averaged over tasks, so the extra repeat runs on S1 and S8 do not outweigh other tasks. False pass = accepted a flawed explanation. False fail = rejected a correct one. No verdict = the response contained no verdict line (counted as a failure).

| Model | Returned model ID | Tasks | TPR (errors caught) | TNR (correct accepted) | Balanced accuracy | False passes | False fails | No verdict |
|---|---|---|---|---|---|---|---|---|
| gemini-3.6-flash | gemini-3.6-flash | 16/16 | 100% | 100% | 100% | 0/12 | 0/12 | 0 |
| gemini-3-flash | gemini-3-flash-preview | 16/16 | 96% | 100% | 98% | 1/12 | 0/12 | 0 |
| gemini-3.5-flash-lite | gemini-3.5-flash-lite | 16/16 | 90% | 98% | 94% | 4/16 | 1/16 | 0 |
| gemini-3.1-flash-lite | gemini-3.1-flash-lite | 16/16 | 100% | 75% | 88% | 0/16 | 10/16 | 0 |
| gemma-4-31b | gemma-4-31b-it | 16/16 | 88% | 100% | 94% | 5/16 | 0/16 | 0 |
| gemini-3.1-flash-lite-t1 | gemini-3.1-flash-lite | 4/16 | 80% | 40% | 60% | 2/10 | 6/10 | 0 |
| gemma-4-31b-t1 | gemma-4-31b-it | 4/16 | 100% | 100% | 100% | 0/10 | 0/10 | 0 |

## Passes per task (passed / runs)

| Task | Category | Expected | gemini-3.6-flash | gemini-3-flash | gemini-3.5-flash-lite | gemini-3.1-flash-lite | gemma-4-31b | gemini-3.1-flash-lite-t1 | gemma-4-31b-t1 |
|---|---|---|---|---|---|---|---|---|---|
| S1_correct | business-day convention | CORRECT | 3/3 | 3/3 | 4/5 | 0/5 | 5/5 | 2/5 | 5/5 |
| S1_error | business-day convention | INCORRECT | 3/3 | 3/3 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| S2_correct | accrual basis | CORRECT | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | – | – |
| S2_error | accrual basis | INCORRECT | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | – | – |
| S3_correct | accrual basis | CORRECT | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | – | – |
| S3_error | accrual basis | INCORRECT | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | – | – |
| S4_correct | holiday calendar | CORRECT | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | – | – |
| S4_error | holiday calendar | INCORRECT | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | – | – |
| S5_correct | business-day convention | CORRECT | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | – | – |
| S5_error | business-day convention | INCORRECT | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | – | – |
| S6_correct | day count | CORRECT | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | – | – |
| S6_error | day count | INCORRECT | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | – | – |
| S7_correct | day count | CORRECT | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | – | – |
| S7_error | day count | INCORRECT | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | – | – |
| S8_correct | day count | CORRECT | 3/3 | 3/3 | 5/5 | 0/5 | 5/5 | 2/5 | 5/5 |
| S8_error | day count | INCORRECT | 3/3 | 2/3 | 1/5 | 5/5 | 0/5 | 3/5 | 5/5 |

## Excluded labels

Responses under these labels are kept in raw_outputs.jsonl but not scored, because the label is not in models.json:
- `gemini-3.5-flash` (the API reported serving it as: gemini-3.6-flash)
