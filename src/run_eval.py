"""Send every task to every model N times and save raw responses to results/raw_outputs.jsonl.

The run is resumable: responses already saved are skipped, so you can rerun after an interruption.
Models are configured in models.json. API keys come from environment variables (see .env.example).
"""
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "results" / "raw_outputs.jsonl"
_lock = threading.Lock()


def call_openai_compatible(m, prompt, temperature, max_tokens):
    """Any OpenAI-style endpoint: OpenRouter, GitHub Models, Z.ai, Groq, OpenAI itself, etc."""
    from openai import OpenAI
    base_url = m.get("base_url", "https://openrouter.ai/api/v1")
    key_env = m.get("api_key_env", "OPENROUTER_API_KEY")
    client = OpenAI(base_url=base_url, api_key=os.environ[key_env])
    model_id = m["model_id"]
    kwargs = dict(model=model_id, messages=[{"role": "user", "content": prompt}], max_tokens=max_tokens)
    if temperature is not None:
        kwargs["temperature"] = temperature
    r = client.chat.completions.create(**kwargs)
    usage = r.usage.model_dump() if r.usage else None
    return r.choices[0].message.content or "", r.model, usage


def call_gemini(m, prompt, temperature, max_tokens):
    model_id = m["model_id"]
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    cfg = dict(max_output_tokens=max_tokens)
    if temperature is not None:
        cfg["temperature"] = temperature
    r = client.models.generate_content(model=model_id, contents=prompt,
                                       config=types.GenerateContentConfig(**cfg))
    usage = r.usage_metadata.model_dump() if r.usage_metadata else None
    return r.text or "", getattr(r, "model_version", None) or model_id, usage


_mock_calls = {}


def call_mock(m, prompt, temperature, max_tokens):
    """Offline stand-in for testing the pipeline without API keys. Verdicts are pseudo-random, not real."""
    import hashlib
    model_id = m["model_id"]
    n = _mock_calls[(model_id, prompt)] = _mock_calls.get((model_id, prompt), 0) + 1
    h = int(hashlib.sha256(f"{model_id}{prompt}{n}".encode()).hexdigest(), 16)
    if h % 17 == 0:
        return "Mock response with no verdict line.", model_id, None
    verdict = "INCORRECT" if (h % 4 == 0) != ("Final answer" in prompt and h % 3 == 0) else "CORRECT"
    return f"Mock response for pipeline testing (not a real model).\nVERDICT: {verdict}", model_id, None


PROVIDERS = {"openrouter": call_openai_compatible, "openai_compatible": call_openai_compatible,
             "gemini": call_gemini, "mock": call_mock}


def load_done():
    done = set()
    if RAW.exists():
        for line in RAW.open():
            r = json.loads(line)
            if r.get("error") is None:
                done.add((r["model_label"], r["task_id"], r["run"]))
    return done


def save(record):
    with _lock, RAW.open("a") as f:
        f.write(json.dumps(record) + "\n")


def run_model(m, tasks, runs, temperature, max_tokens, done):
    call = PROVIDERS[m["provider"]]
    interval = m.get("min_interval_s", 0)
    for run in range(1, runs + 1):
        for t in tasks:
            if (m["label"], t["id"], run) in done:
                continue
            record = dict(model_label=m["label"], provider=m["provider"], requested_model_id=m["model_id"],
                          task_id=t["id"], run=run, temperature=m["temperature"] if "temperature" in m else temperature, max_tokens=m.get("max_tokens", max_tokens))
            for attempt in range(5):
                started = time.time()
                try:
                    text, returned_model, usage = call(m, t["prompt"], m["temperature"] if "temperature" in m else temperature, m.get("max_tokens", max_tokens))
                    record.update(response=text, returned_model=returned_model, usage=usage, error=None)
                    break
                except Exception as e:  # rate limits, timeouts, transient server errors
                    record.update(response=None, returned_model=None, usage=None, error=repr(e))
                    msg = repr(e)
                    if "RESOURCE_EXHAUSTED" in msg and ("PerDay" in msg or "limit: 0" in msg):
                        print(f"  [{m['label']}] daily free-tier quota used up -> stopping this model. "
                              f"Rerun later (or tomorrow) to continue where it left off.")
                        return
                    wait = 2 ** attempt * 5
                    print(f"  [{m['label']}] {t['id']} run {run}: {msg[:160]} -> retry in {wait}s")
                    time.sleep(wait)
            record["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
            record["latency_s"] = round(time.time() - started, 2)
            save(record)
            status = "error" if record["error"] else "ok"
            print(f"  [{m['label']}] {t['id']} run {run}: {status}")
            time.sleep(interval)


def main(model_labels=None, runs=3, mock=False, task_filter=None):
    global RAW
    if mock:  # keep pipeline-test output separate from real results
        RAW = ROOT / "results" / "mock" / "raw_outputs.jsonl"
    cfg = json.loads((ROOT / "models.json").read_text())
    tasks = [json.loads(l) for l in (ROOT / "tasks" / "tasks.jsonl").open()]
    models = cfg["models"]
    if task_filter:
        tasks = [t for t in tasks if t["scenario"] in task_filter or t["id"] in task_filter]
    if mock:
        models = [dict(label=f"mock-{x}", provider="mock", model_id=f"mock-model-{x}") for x in "abc"]
    elif model_labels:
        models = [m for m in models if m["label"] in model_labels]
    for m in models:
        if "REPLACE" in m["model_id"]:
            raise SystemExit(f"Set an exact model ID for '{m['label']}' in models.json before running.")
    RAW.parent.mkdir(parents=True, exist_ok=True)
    done = load_done()
    total = len(models) * len(tasks) * runs
    print(f"{len(models)} models x {len(tasks)} tasks x {runs} runs = {total} calls ({len(done)} already saved)")
    with ThreadPoolExecutor(max_workers=len(models)) as pool:  # one thread per model, sequential within
        futures = [pool.submit(run_model, m, tasks, runs, cfg.get("temperature"), cfg.get("max_tokens", 8000), done)
                   for m in models]
        for f in futures:
            f.result()
