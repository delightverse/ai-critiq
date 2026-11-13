"""Grade raw model outputs and write results.

Grading is deterministic: the verdict is the LAST line matching "VERDICT: CORRECT" or "VERDICT: INCORRECT"
(case-insensitive, markdown asterisks ignored). A response with no verdict line counts as a failure and is
reported separately as "no verdict". No AI model is used as a grader.

Rates are averaged over tasks (each task's pass rate counts once), so tasks that received extra repeat runs
(S1 and S8) do not outweigh the others. Raw counts are reported alongside.

Only models listed in models.json are scored. Responses from other labels stay in raw_outputs.jsonl and are
listed in the summary as excluded (e.g. gemini-3.5-flash, which the API served as gemini-3.6-flash).

Outputs (in the results folder):
  scores.csv          one row per response
  summary.md / .json  per-model metrics and per-task pass counts
  review_sample.csv   responses to hand-check whether the model's REASON was right, not just its verdict
  report.html         self-contained results viewer (open in any browser)
"""
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERDICT_RE = re.compile(r"VERDICT\s*:\s*\**\s*(CORRECT|INCORRECT)\b", re.IGNORECASE)


def extract_verdict(text):
    if not text:
        return None
    matches = VERDICT_RE.findall(text.replace("*", ""))
    return matches[-1].upper() if matches else None


def outcome(expected, verdict):
    if verdict is None:
        return "no_verdict"
    if verdict == expected:
        return "pass"
    return "false_pass" if expected == "INCORRECT" else "false_fail"


def mean(xs):
    return sum(xs) / len(xs) if xs else None


def fmt_pct(x):
    return "n/a" if x is None else f"{x:.0%}"


def main(results_dir=None):
    results_dir = Path(results_dir) if results_dir else ROOT / "results"
    tasks = {json.loads(l)["id"]: json.loads(l) for l in (ROOT / "tasks" / "tasks.jsonl").open()}
    cfg = json.loads((ROOT / "models.json").read_text())
    configured = [m["label"] for m in cfg["models"]]

    # latest successful response for each (model, task, run)
    latest = {}
    for line in (results_dir / "raw_outputs.jsonl").open():
        r = json.loads(line)
        if r.get("error") is None:
            latest[(r["model_label"], r["task_id"], r["run"])] = r

    seen = sorted({k[0] for k in latest})
    if any(m in configured for m in seen):  # real run: score only configured models, in config order
        order = [m for m in configured if m in seen]
        excluded = {m: sorted({str(r["returned_model"]) for k, r in latest.items() if k[0] == m})
                    for m in seen if m not in configured}
        latest = {k: r for k, r in latest.items() if k[0] in configured}
    else:  # mock or ad-hoc labels
        order, excluded = seen, {}

    rows = []
    for (model, task_id, run), r in sorted(latest.items()):
        t = tasks[task_id]
        verdict = extract_verdict(r["response"])
        o = outcome(t["expected_verdict"], verdict)
        rows.append(dict(model=model, returned_model=r["returned_model"], task_id=task_id, scenario=t["scenario"],
                         category=t["category"], version=t["version"], run=run, expected=t["expected_verdict"],
                         verdict=verdict or "NO_VERDICT", outcome=o, passed=int(o == "pass")))
    if not rows:
        print("No responses to score yet.")
        return

    with (results_dir / "scores.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # per (model, task) pass counts
    cell = defaultdict(lambda: [0, 0])
    for r in rows:
        c = cell[(r["model"], r["task_id"])]
        c[0] += r["passed"]
        c[1] += 1

    summary = {}
    for m in order:
        rs = [r for r in rows if r["model"] == m]
        err_rates = [cell[(m, t)][0] / cell[(m, t)][1] for t in tasks
                     if tasks[t]["version"] == "error" and cell[(m, t)][1]]
        cor_rates = [cell[(m, t)][0] / cell[(m, t)][1] for t in tasks
                     if tasks[t]["version"] == "correct" and cell[(m, t)][1]]
        tpr, tnr = mean(err_rates), mean(cor_rates)
        summary[m] = dict(
            returned_model=sorted({str(r["returned_model"]) for r in rs}),
            responses=len(rs),
            tasks_covered=sum(1 for t in tasks if cell[(m, t)][1]),
            tpr=tpr, tnr=tnr, balanced_accuracy=(tpr + tnr) / 2 if tpr is not None and tnr is not None else None,
            false_passes=sum(r["outcome"] == "false_pass" for r in rs),
            flawed_runs=sum(r["version"] == "error" for r in rs),
            false_fails=sum(r["outcome"] == "false_fail" for r in rs),
            correct_runs=sum(r["version"] == "correct" for r in rs),
            no_verdict=sum(r["outcome"] == "no_verdict" for r in rs),
        )

    lines = ["# Results summary", "",
             "Positive class = an explanation that contains an error. **TPR** (errors caught) and **TNR** (correct "
             "work accepted) are averaged over tasks, so the extra repeat runs on S1 and S8 do not outweigh other "
             "tasks. False pass = accepted a flawed explanation. False fail = rejected a correct one. "
             "No verdict = the response contained no verdict line (counted as a failure).", "",
             "| Model | Returned model ID | Tasks | TPR (errors caught) | TNR (correct accepted) | Balanced accuracy "
             "| False passes | False fails | No verdict |",
             "|---|---|---|---|---|---|---|---|---|"]
    for m in order:
        s = summary[m]
        lines.append(f"| {m} | {', '.join(s['returned_model'])} | {s['tasks_covered']}/{len(tasks)} | "
                     f"{fmt_pct(s['tpr'])} | {fmt_pct(s['tnr'])} | {fmt_pct(s['balanced_accuracy'])} | "
                     f"{s['false_passes']}/{s['flawed_runs']} | {s['false_fails']}/{s['correct_runs']} | "
                     f"{s['no_verdict']} |")
    lines += ["", "## Passes per task (passed / runs)", "",
              "| Task | Category | Expected | " + " | ".join(order) + " |",
              "|---|---|---|" + "---|" * len(order)]
    for task_id in sorted(tasks):
        t = tasks[task_id]
        cells = [f"{cell[(m, task_id)][0]}/{cell[(m, task_id)][1]}" if cell[(m, task_id)][1] else "–" for m in order]
        lines.append(f"| {task_id} | {t['category']} | {t['expected_verdict']} | " + " | ".join(cells) + " |")
    if excluded:
        lines += ["", "## Excluded labels", "",
                  "Responses under these labels are kept in raw_outputs.jsonl but not scored, because the label is "
                  "not in models.json:"]
        for m, ids in excluded.items():
            lines.append(f"- `{m}` (the API reported serving it as: {', '.join(ids)})")
    (results_dir / "summary.md").write_text("\n".join(lines) + "\n")
    (results_dir / "summary.json").write_text(json.dumps(dict(
        models=summary, excluded=excluded,
        per_task={t: {m: cell[(m, t)] for m in order if cell[(m, t)][1]} for t in sorted(tasks)}), indent=2))

    # hand-review sheet: every failure, plus every flawed-version pass (was the reason right?)
    review = []
    for (model, task_id, run), r in sorted(latest.items()):
        t = tasks[task_id]
        verdict = extract_verdict(r["response"])
        o = outcome(t["expected_verdict"], verdict)
        if o != "pass" or t["version"] == "error":
            review.append(dict(model=model, task_id=task_id, run=run, expected=t["expected_verdict"],
                               verdict=verdict or "NO_VERDICT", outcome=o, injected_error=t["error_note"] or "",
                               response=r["response"], verdict_extracted_ok_y_n="", reason_correct_y_n="",
                               open_code_note="", failure_category=""))
    with (results_dir / "review_sample.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(review[0].keys()) if review else ["empty"])
        w.writeheader()
        w.writerows(review)

    import report
    path = report.build(results_dir, tasks, latest, extract_verdict, order)
    print("\n".join(lines))
    print(f"\nReport: {path} (open in a browser)")
