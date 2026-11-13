# AI critiQ

**Can AI reviewers check an interest calculation?** An eval of AI models acting as reviewers of loan interest
calculations, built for the micro1 Eval Hackathon (November 2026).

🎥 **Video walkthrough:** https://drive.google.com/file/d/14tj-LhG5vjl9xlVMp4t1vcKG_596h0Dv/view?usp=sharing

📊 **Interactive dashboard:** open `results/report.html` in any browser

## Overview

AI critiQ tests whether AI models acting as **reviewers** can tell a correct loan interest calculation from one
containing a single expert-level mistake. Eight scenarios combine business-day conventions, US holiday calendars,
accrual bases, and day-count rules; each is shown once fully correct and once with one realistic error, and every
expected answer is computed in code from the 2006 ISDA Definitions.

**Key findings**

- Every failure came from two of the eight scenarios; all five models handled the other six correctly in every run.
- The 30/360 Bond Basis scenario (S8) tripped four of five models at least once, in both directions, through one
  shared misconception about the end of February. Only Gemini 3.6 Flash was never wrong.
- Gemini 3.1 Flash-Lite "corrected" an accurate 183-day count to 184 in every run at temperature 0, and in 3 of 5
  runs at temperature 1.0.

## Domain

Financial operations, specifically loan and fixed-income interest calculation: business-day conventions (Following,
Modified Following, Preceding), US banking holiday calendars, adjusted versus unadjusted accrual, and day-count
conventions (ACT/360, ACT/365 Fixed, 30/360 Bond Basis). This is the expertise treasury, loan operations and
settlement teams apply every day, and exactly what an AI reviewer of these calculations must get right.

## What it tests and why it matters

| ID | Scenario | Rule under test | Injected error |
|---|---|---|---|
| S1 | Modified Following rollback across Labor Day | Business-day convention | Applies plain Following |
| S2 | Adjusted accrual after a rollback | Accrual basis | Counts to the unadjusted date |
| S3 | Unadjusted accrual, adjusted payment | Accrual basis | Counts to the payment date |
| S4 | Following over Thanksgiving | Holiday calendar | Treats the holiday as a business day |
| S5 | Preceding over MLK Day | Business-day convention | Rolls forward instead of back |
| S6 | Leap day in an ACT/365 Fixed period | Day count | February 2024 counted as 28 days |
| S7 | ACT/365 Fixed denominator in a leap year | Day count | Denominator 366 instead of 365 |
| S8 | 30/360 Bond Basis ending February 29 | Day count | February month-end treated as day 30 |

Every scenario appears in two versions: **flawed** (expected verdict INCORRECT) and **correct** (expected verdict
CORRECT), so the eval measures both failure directions:

- **False pass:** the reviewer accepts a wrong calculation, so a client is over- or under-charged.
- **False fail:** the reviewer rejects a correct calculation, causing rework or a correct figure being "fixed" into a wrong one.

A one-day accrual error on a USD 10 million position at 5% is about USD 1,400 per period, repeated across every
loan, swap and bond in a portfolio. Lighter models are exactly the ones teams deploy for high-volume checking.

## Quickstart

Requires Python 3.10+ and a free Google AI Studio API key.

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then set GEMINI_API_KEY in .env
python run.py                      # generate tasks -> query models -> score -> build the dashboard
```

- **Models** are configured in `models.json`.
- **Options:** `--runs N` runs per task, `--models <labels>` a subset of models, `--tasks S1 S8` only some scenarios,
  `--score-only` to re-grade saved responses, `--mock` to test the pipeline offline without a key.
- **Free-tier quotas:** Gemini Flash models allow about 20 requests per day each. When a quota runs out, the harness
  stops that model, and the next run resumes where it left off.
- **Cost:** USD 0 on the free tier. Models are called with no tools and no system prompt.

## Results

**Run dates:** 2026-11-07 to 2026-11-09. **Settings:** temperature 0, max output 32,768 tokens (shared by thinking
and answer), single-turn prompts. **Runs:** one full pass of all 16 tasks per model, repeat runs on S1 and S8 (5 for
the Lite models and Gemma, 3 for the Flash models), and a robustness check at temperature 1.0.

| Model (label) | Model ID returned by the API | TPR (errors caught) | TNR (correct work accepted) | Balanced accuracy | False passes | False fails |
|---|---|---|---|---|---|---|
| gemini-3.6-flash | gemini-3.6-flash | 100% | 100% | 100% | 0/12 | 0/12 |
| gemini-3-flash | gemini-3-flash-preview | 96% | 100% | 98% | 1/12 | 0/12 |
| gemini-3.5-flash-lite | gemini-3.5-flash-lite | 90% | 98% | 94% | 4/16 | 1/16 |
| gemini-3.1-flash-lite | gemini-3.1-flash-lite | 100% | 75% | 88% | 0/16 | 10/16 |
| gemma-4-31b | gemma-4-31b-it | 88% | 100% | 94% | 5/16 | 0/16 |

TPR and TNR average each task's pass rate, so the repeat runs on S1 and S8 do not outweigh the other tasks; the
false pass and false fail columns count every run. The robustness-check rows (`-t1`) are reported separately below.

**Every failure came from S1 or S8.** All five models handled S2–S7 correctly in every run.

| Scenario and version | gemini-3.6-flash | gemini-3-flash | gemini-3.5-flash-lite | gemini-3.1-flash-lite | gemma-4-31b |
|---|---|---|---|---|---|
| S1 correct (should accept) | 3/3 | 3/3 | 4/5 | **0/5** | 5/5 |
| S1 flawed (should reject) | 3/3 | 3/3 | 5/5 | 5/5 | 5/5 |
| S8 correct (should accept) | 3/3 | 3/3 | 5/5 | **0/5** | 5/5 |
| S8 flawed (should reject) | 3/3 | **2/3** | **1/5** | 5/5 | **0/5** |

### Determinism at temperature 0

gemini-3.1-flash-lite and gemma-4-31b returned byte-identical responses on every
repeat of S1 and S8 (1 distinct response per 5 runs), so for these two models the repeats show the result is stable
but are effectively one sample. gemini-3.5-flash-lite and gemini-3.6-flash produced a different response on every
run, so their repeats are independent samples.

### Robustness check at temperature 1.0

To test whether the two deterministic models' failures hold when answers
vary, S1 and S8 were rerun 5 times each at temperature 1.0 (labels ending in `-t1`; every response distinct):

| Scenario and version | gemini-3.1-flash-lite at T=0 | gemini-3.1-flash-lite at T=1.0 | gemma-4-31b at T=0 | gemma-4-31b at T=1.0 |
|---|---|---|---|---|
| S1 correct (should accept) | 0/5 | 2/5 | 5/5 | 5/5 |
| S1 flawed (should reject) | 5/5 | 5/5 | 5/5 | 5/5 |
| S8 correct (should accept) | 0/5 | 2/5 | 5/5 | 5/5 |
| S8 flawed (should reject) | 5/5 | 3/5 | **0/5** | **5/5** |

Under sampling, gemini-3.1-flash-lite still rejected correct work in 3 of 5 runs on both S1 and S8, and on S8 it
was right in only 5 of 10 runs across both versions (no better than chance), now erring in both directions. The
failures are not an artifact of one locked-in answer. Gemma is the opposite case: at temperature 1.0 it answered all
20 correctly, including the flawed S8 it accepted in every temperature-0 run. Its S8 failure is real but lives in its
single deterministic answer, so we report it as such rather than as a robust weakness. The `-t1` rows cover only S1 and S8, so their overall rates
in `results/summary.md` should not be compared with the full-pass models.


## Failure analysis

### S8: one shared misconception, appearing in both directions, in four of five models

The period runs from August 31, 2023 to
February 29, 2024 under 30/360 Bond Basis (ISDA 2006 Section 4.16(f)). Only a day 31 is changed to 30, so D1 = 30,
D2 = 29, and the count is 179 days. The February month-end adjustment belongs to other 30/360 variants (30E/360 ISDA,
and the US variant only when the period also starts at the end of February). Four of the five models treated the
period as 180 days at least once:

- **gemini-3.1-flash-lite** rejected the correct 179-day explanation in 5 of 5 runs, reasoning that the period is
  "exactly half a year" and therefore 180 days, treating February 29 as "February 30".
- **gemini-3.5-flash-lite** accepted the flawed 180-day explanation in 4 of 5 runs.
- **gemma-4-31b** accepted the flawed explanation in its deterministic temperature-0 answer (5 of 5 identical runs),
  stating a rule that does not exist in any 30/360 variant: "if D2 is the last day of February and D1 is 30 or 31, D2
  is changed to 30." At temperature 1.0 it rejected the flaw in 5 of 5 runs.
- **gemini-3-flash**, a full Flash model, accepted the flawed explanation in 1 of 3 runs.

The same false belief produces opposite verdicts depending on what the model is shown, which is why measuring false
passes and false fails separately matters.

### S1: correcting a right answer into a wrong one

The correct explanation counts 183 days from February 29 to
August 30, 2024. gemini-3.1-flash-lite rejected it in 5 of 5 runs. In the responses reviewed, it first reproduced
the correct month-by-month count (183), then "corrected" it by subtracting day-of-year numbers, claiming August 30
is day 244 (it is day 243), concluded 184, and invented a justification ("the explanation missed the leap day").
In pilot testing in the Gemini chat app before this harness existed, Gemini made the same false correction to 184
in 3 of 4 fresh chats.

### What the strongest models did differently

The full Flash models reasoned at length before answering
(gemini-3-flash used about 7,700 thinking tokens on one task). gemini-3.6-flash was right in every run, and
gemini-3-flash's only miss was one S8 run, so even a strong model is not immune to the 30/360 confusion.

### Practical implication

Reviewer reliability depends on the model tier, and the failures are consistent rather
than random, so they will repeat at scale. Teams using lighter models to check financial calculations should
validate the validator: test the reviewer on known-correct and known-flawed cases like these, and route
convention-specific checks (30/360 variants, business-day adjustments) to a stronger model or a human expert.

### Hand review

 All 21 failing responses in the main runs were read by hand (recorded in `results/hand_review.csv`). The
extracted verdict matched each response's stated conclusion in 21 of 21, validating the code grader. Open coding of
the reasons produced two categories (axial coding):

| Category | Failures | Models | Pattern |
|---|---|---|---|
| A. Arithmetic slip turned into a false correction | 6 | gemini-3.1-flash-lite (5), gemini-3.5-flash-lite (1) | Recounts an accurate day count, makes an arithmetic error (wrong day-of-year number, mis-summed month lengths), then rejects correct work with an invented reason |
| B. 30/360 variant confusion | 15 | gemini-3.1-flash-lite (5), gemini-3.5-flash-lite (4), gemma-4-31b (5), gemini-3-flash (1) | Treats February 29 as day 30 or assumes six months is always 180 days, importing the February rule from other 30/360 variants |


## How grading works

`src/score.py` is fully deterministic: it reads the last `VERDICT: CORRECT` or `VERDICT: INCORRECT` line in each
response and compares it with the expected verdict. No AI model is used as a grader. A response without a verdict
line counts as a failure and is reported separately as "no verdict". "Explanation contains an error" is the
positive class: TPR is the share of flawed explanations rejected, TNR the share of correct explanations accepted,
and balanced accuracy their average, so a model that always answers CORRECT (or always INCORRECT) scores only 50%.


## Data integrity notes

- **Archived, not deleted:** responses produced under settings we later corrected are kept in `results/archive/`
  and excluded from scoring: gemini-3-flash answers cut off by an 8,000-token limit (its thinking used the whole
  budget), and two earlier Gemma passes (one recorded a token setting that did not match the request; one was cut
  off at 8,192 tokens). Every scored response was produced with the settings stated under Results.
- **Redirected model excluded:** requests to `gemini-3.5-flash` were served by the API as `gemini-3.6-flash` (shown in
  the returned model ID), so they are kept in the raw file but excluded from scoring as duplicates.
- **Server errors:** HTTP 500/503 errors were retried with backoff; a few Gemma requests failed after five attempts
  and were rerun later, so run counts differ slightly between tasks.


## Limitations

- Small sample: 8 scenarios, with repeats concentrated on the two scenarios that showed failures.
- One provider family (Gemini and Gemma), because those models were available on a free tier; OpenAI models were
  planned but could not be reached from the test environment.
- At temperature 0, two models were fully deterministic and two were not, so repeat counts carry different weight
  per model (see "Determinism at temperature 0"); the temperature 1.0 check addresses this for the deterministic ones.
- Scenarios use 2023–2025 dates and the US (New York) holiday calendar only.


## Sources and acknowledgements

- Conventions: 2006 ISDA Definitions, Section 4.12 (business day conventions) and Section 4.16 (day count
  fractions, including 4.16(f) 30/360 Bond Basis).
- Holiday calendar: US Federal Reserve holiday schedule, implemented in `src/generate_tasks.py`.
- Methodology: practices taught by Hamel Husain and Shreya Shankar (the AI Evals course and the open-source
  `evals-skills` repository): binary pass/fail verdicts, code-based grading where the rule is objective, TPR/TNR
  instead of raw accuracy, and open then axial coding of failures. Used as guidance only; none of their code is included.
- "Validating the validator": Dr. Christopher Lovejoy, *Mission-Critical Evals at Scale*, AI Engineer conference.
- All tasks are original; no existing benchmark or dataset was used.

## Project layout

```
run.py                  one-command entry point
models.json             model IDs and settings
src/generate_tasks.py   scenarios, holiday calendar, ground-truth computation, prompt rendering
src/run_eval.py         API calls (resumable, quota-aware), raw output logging
src/score.py            deterministic grading, summary tables, hand-review sheet
src/report.py           builds results/report.html, the AI critiQ dashboard
tasks/tasks.jsonl       generated tasks with ground truth
results/                raw outputs, scores, summary, review sheet, dashboard, archive
```

## License

MIT. See [LICENSE](LICENSE).
