"""One command to reproduce the whole eval: generate tasks -> query models -> score.

  python run.py                 # all models in models.json, 3 runs per task
  python run.py --runs 1        # quicker, cheaper single pass
  python run.py --models gemini # only some models (labels from models.json)
  python run.py --mock          # offline pipeline test, no API keys needed
  python run.py --score-only    # re-grade existing raw outputs
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from dotenv import load_dotenv  # noqa: E402

import generate_tasks  # noqa: E402
import run_eval  # noqa: E402
import score  # noqa: E402

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--runs", type=int, default=3)
    p.add_argument("--models", nargs="*")
    p.add_argument("--tasks", nargs="*", help="scenario IDs (e.g. S1 S8) or task IDs")
    p.add_argument("--mock", action="store_true")
    p.add_argument("--score-only", action="store_true")
    a = p.parse_args()
    load_dotenv()
    results = Path(__file__).resolve().parent / "results" / ("mock" if a.mock else "")
    if not a.score_only:
        print("1/3 Generating tasks")
        tasks = generate_tasks.build()
        out = Path(__file__).resolve().parent / "tasks" / "tasks.jsonl"
        out.write_text("".join(__import__("json").dumps(t) + "\n" for t in tasks))
        print(f"    {len(tasks)} tasks written")
        print("2/3 Querying models")
        run_eval.main(a.models, a.runs, a.mock, a.tasks)
    print("3/3 Scoring")
    score.main(results)
