"""Build results/report.html: the AI critiQ results dashboard (self-contained; open in any browser, no server needed).

Layout: overview tiles and charts, a scenario-by-model heatmap (as in HELM's model-by-scenario grid), the
scenarios where models failed, a per-model scorecard, and a drawer that opens the exact prompt and raw
responses behind any cell (as in the Inspect log viewer). Everything sits on one 12-column grid.
"""
import json
from datetime import datetime, timezone
from pathlib import Path


def build(results_dir, tasks, latest, extract_verdict, order=None):
    models = order or sorted({k[0] for k in latest})
    returned = {m: sorted({str(r["returned_model"]) for k, r in latest.items() if k[0] == m}) for m in models}
    responses = {}
    for (model, task_id, run), r in sorted(latest.items()):
        if model not in models:
            continue
        responses.setdefault(task_id, {}).setdefault(model, []).append(dict(
            run=run, verdict=extract_verdict(r["response"]) or "NONE", text=r["response"] or ""))
    scenarios = {}
    for t in tasks.values():
        s = scenarios.setdefault(t["scenario"], dict(id=t["scenario"], title=t["title"], category=t["category"]))
        s[t["version"]] = t["id"]
        if t["version"] == "error":
            s["note"] = t["error_note"]
    data = dict(
        generated=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        models=[dict(label=m, ids=returned[m]) for m in models],
        scenarios=sorted(scenarios.values(), key=lambda s: int(s["id"][1:])),
        tasks={t["id"]: dict(id=t["id"], scenario=t["scenario"], version=t["version"],
                             expected=t["expected_verdict"], truth=t["ground_truth"],
                             claims=t["explanation_claims"], prompt=t["prompt"]) for t in tasks.values()},
        responses=responses,
        mock="mock" in str(results_dir),
    )
    payload = json.dumps(data).replace("</", "<\\/")
    out = Path(results_dir) / "report.html"
    out.write_text(TEMPLATE.replace("__DATA__", payload))
    return out


TEMPLATE = r"""<!doctype html>
<html lang="en" data-palette="mint">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>AI critiQ · Interest calculation review eval</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
/* ---------- design tokens ---------- */
:root{
  --gap:20px; --pad:22px; --radius:14px; --radius-sm:8px;
  --font:"Inter",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  --display:"Manrope","Inter",system-ui,sans-serif;
}
/* Mint (default): white, light and friendly */
:root[data-palette="mint"]{
  --bg:#FFFFFF; --panel:#F6FAF8; --card:#FFFFFF; --ink:#1D2B25; --muted:#66756E; --faint:#93A19A;
  --rule:#E3EBE7; --rule-soft:#EEF3F0;
  --accent:#2FA57C; --accent-ink:#1E7A5A; --accent-soft:#E7F6EF; --accent-2:#38B2C8;
  --ok:#2E9266; --ok-bg:#E6F4EC; --ok-solid:#4DB386;
  --fp:#C2553D; --fp-bg:#FCEAE5; --fp1:#FBE3DC; --fp2:#EDA893; --fp3:#D2674D;
  --ff:#A87512; --ff-bg:#FCF3DF; --ff1:#FBF0D6; --ff2:#EBC77A; --ff3:#D3A13A;
  --nv:#A3B0A9; --na:#F4F7F5; --focus:#2C6BD6; --shadow:0 1px 2px rgba(29,43,37,.04),0 2px 8px rgba(29,43,37,.04);
  --on-solid:#FFFFFF; color-scheme:light;
}
/* Lagoon: white with calm blue-teal */
:root[data-palette="lagoon"]{
  --bg:#FFFFFF; --panel:#F5F9FC; --card:#FFFFFF; --ink:#1B2836; --muted:#627284; --faint:#94A2B1;
  --rule:#E2E9F0; --rule-soft:#EDF2F7;
  --accent:#2B8FB8; --accent-ink:#1C6C8C; --accent-soft:#E5F3F9; --accent-2:#5BBFA8;
  --ok:#2C8C73; --ok-bg:#E3F3EE; --ok-solid:#4AB497;
  --fp:#C2553D; --fp-bg:#FCEAE5; --fp1:#FBE3DC; --fp2:#EDA893; --fp3:#D2674D;
  --ff:#A87512; --ff-bg:#FCF3DF; --ff1:#FBF0D6; --ff2:#EBC77A; --ff3:#D3A13A;
  --nv:#A4B0BC; --na:#F4F7FA; --focus:#2C6BD6; --shadow:0 1px 2px rgba(27,40,54,.04),0 2px 8px rgba(27,40,54,.04);
  --on-solid:#FFFFFF; color-scheme:light;
}
/* Sand: warm paper with sage */
:root[data-palette="sand"]{
  --bg:#FDFBF7; --panel:#F7F3EB; --card:#FFFFFF; --ink:#2B2620; --muted:#756C60; --faint:#A39888;
  --rule:#ECE5D9; --rule-soft:#F3EEE5;
  --accent:#6E9C6A; --accent-ink:#4E7A4B; --accent-soft:#EEF4EA; --accent-2:#C79A5B;
  --ok:#4E8B56; --ok-bg:#EAF3E8; --ok-solid:#79AE76;
  --fp:#B9533B; --fp-bg:#F9E8E1; --fp1:#F8E2D9; --fp2:#E5A790; --fp3:#C9664C;
  --ff:#9E6F12; --ff-bg:#FAF0DA; --ff1:#F8ECD0; --ff2:#E4C176; --ff3:#C89A37;
  --nv:#B0A797; --na:#F6F2EA; --focus:#2C6BD6; --shadow:0 1px 2px rgba(43,38,32,.05),0 2px 8px rgba(43,38,32,.04);
  --on-solid:#FFFFFF; color-scheme:light;
}
/* Night: dark forest */
:root[data-palette="night"]{
  --bg:#0F1613; --panel:#131C18; --card:#17221D; --ink:#E4ECE8; --muted:#9AAAA2; --faint:#6F7F77;
  --rule:#26332D; --rule-soft:#1E2A24;
  --accent:#5BD3A3; --accent-ink:#7EE0B8; --accent-soft:#183129; --accent-2:#6CCFE0;
  --ok:#69CB98; --ok-bg:#173126; --ok-solid:#3E9E70;
  --fp:#EE8A70; --fp-bg:#3A201A; --fp1:#3A201A; --fp2:#7D3B2A; --fp3:#C9644A;
  --ff:#E6BC62; --ff-bg:#382C14; --ff1:#382C14; --ff2:#755A20; --ff3:#B98B2D;
  --nv:#6A7B73; --na:#1A2520; --focus:#8EB2FF; --shadow:none;
  --on-solid:#FFFFFF; color-scheme:dark;
}

/* ---------- base ---------- */
*{box-sizing:border-box}
html{scroll-behavior:smooth;scroll-padding-top:env(safe-area-inset-top,0px)}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}
body{margin:0;background:var(--bg);color:var(--ink);font:14.5px/1.55 var(--font);font-variant-numeric:tabular-nums;-webkit-font-smoothing:antialiased}
h1,h2,h3,.display{font-family:var(--display);letter-spacing:-0.015em}
button{font:inherit;color:inherit;cursor:pointer}
button:focus-visible,a:focus-visible,summary:focus-visible{outline:3px solid var(--focus);outline-offset:2px}

/* ---------- shell ---------- */
.shell{display:grid;grid-template-columns:236px minmax(0,1fr);min-height:100vh}
@media (max-width:960px){.shell{grid-template-columns:1fr}}
.side{background:var(--panel);border-right:1px solid var(--rule);padding:24px 16px;position:sticky;top:0;height:100vh;
  display:flex;flex-direction:column;gap:28px}
@media (max-width:960px){.side{position:static;height:auto;border-right:0;border-bottom:1px solid var(--rule);
  flex-direction:row;flex-wrap:wrap;align-items:center;gap:12px 24px;padding:14px 20px}}
.brand{display:flex;align-items:center;gap:10px;padding:0 8px;text-decoration:none;color:var(--ink)}
.brand .word{font:800 19px/1 var(--display);letter-spacing:-0.02em}
.brand .word .ai{color:var(--accent)}
.brand .word .q{color:var(--accent)}
.brand small{display:block;font:500 11.5px/1.3 var(--font);color:var(--muted);margin-top:4px;letter-spacing:0}
.nav{display:flex;flex-direction:column;gap:2px}
@media (max-width:960px){.nav{flex-direction:row;flex-wrap:wrap}}
.nav a{color:var(--muted);text-decoration:none;padding:9px 12px;border-radius:var(--radius-sm);font-weight:500;display:flex;align-items:center;gap:10px}
.nav a:hover{background:var(--accent-soft);color:var(--ink)}
.nav a svg{flex:none;opacity:.8}
.side-foot{margin-top:auto;display:flex;flex-direction:column;gap:14px;padding:0 8px}
@media (max-width:960px){.side-foot{margin:0;flex-direction:row;align-items:center;flex-wrap:wrap}}
.side-foot .lbl{font-size:11.5px;font-weight:600;color:var(--faint);text-transform:none;margin:0 0 8px}
.swatches{display:flex;gap:8px}
.swatch{width:30px;height:30px;border-radius:50%;border:2px solid var(--card);box-shadow:0 0 0 1px var(--rule);padding:0;position:relative}
.swatch[aria-pressed="true"]{box-shadow:0 0 0 2px var(--accent)}
.swatch span{position:absolute;inset:0;border-radius:50%;overflow:hidden;display:block}
.meta{font-size:12px;color:var(--muted);line-height:1.6}

/* ---------- main grid ---------- */
main{padding:32px clamp(20px,3vw,40px) 56px;max-width:1360px;width:100%}
.page-head{display:flex;flex-wrap:wrap;gap:12px 24px;align-items:flex-end;justify-content:space-between;padding-bottom:24px;border-bottom:1px solid var(--rule);margin-bottom:24px}
.eyebrow{display:inline-flex;align-items:center;gap:8px;color:var(--accent-ink);background:var(--accent-soft);font-weight:600;font-size:12.5px;padding:4px 10px;border-radius:999px;margin:0 0 12px}
h1{font-size:clamp(26px,2.8vw,34px);line-height:1.15;font-weight:800;margin:0;max-width:26ch}
.lede{color:var(--muted);margin:10px 0 0;max-width:70ch}
.mockbar{background:var(--ff-bg);border:1px solid var(--ff2);color:var(--ink);padding:10px 14px;border-radius:var(--radius-sm);margin:0 0 var(--gap)}
.grid{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:var(--gap);align-items:stretch}
.span-3{grid-column:span 3} .span-4{grid-column:span 4} .span-6{grid-column:span 6} .span-12{grid-column:span 12}
@media (max-width:1180px){.span-3{grid-column:span 6}.span-4{grid-column:span 6}.span-4.wide-md{grid-column:span 12}}
@media (max-width:720px){.span-3,.span-4,.span-6{grid-column:span 12}}
.card{background:var(--card);border:1px solid var(--rule);border-radius:var(--radius);box-shadow:var(--shadow);padding:var(--pad);display:flex;flex-direction:column;min-width:0}
.card-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin:0 0 16px}
.card-head h2{font-size:15.5px;font-weight:700;margin:0;line-height:1.3}
.card-head p{margin:3px 0 0;color:var(--muted);font-size:13px}
.section-head{grid-column:span 12;display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;gap:4px 16px;margin:16px 0 -4px}
.section-head h2{font-size:19px;font-weight:800;margin:0}
.section-head p{margin:0;color:var(--muted);font-size:13.5px}

/* ---------- KPI tiles ---------- */
.kpi .label{display:flex;align-items:center;gap:8px;color:var(--muted);font-size:13px;font-weight:500}
.kpi .icon{width:28px;height:28px;border-radius:8px;background:var(--accent-soft);color:var(--accent-ink);display:grid;place-items:center;flex:none}
.kpi .value{font:800 30px/1.1 var(--display);letter-spacing:-0.02em;margin:14px 0 4px}
.kpi .hint{font-size:12.5px;color:var(--muted);margin-top:auto}
.kpi.alert .icon{background:var(--fp-bg);color:var(--fp)}
.kpi.alert .value{color:var(--fp)}

/* ---------- charts ---------- */
.donut-wrap{display:flex;gap:20px;align-items:center;flex:1}
.donut{width:136px;height:136px;flex:none}
.donut .val{font:800 24px/1 var(--display);fill:var(--ink)}
.donut .cap{font:500 10.5px/1 var(--font);fill:var(--muted)}
.legend{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:9px;font-size:13px;flex:1;min-width:0}
.legend li{display:flex;align-items:center;gap:8px}
.legend li span{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.legend b{margin-left:auto;padding-left:10px;font-weight:600}
.sw{width:10px;height:10px;border-radius:3px;flex:none;display:inline-block}
.sw.ok{background:var(--ok-solid)} .sw.fp{background:var(--fp3)} .sw.ff{background:var(--ff3)} .sw.nv{background:transparent;border:2px dashed var(--nv)}
.bars{display:flex;flex-direction:column;gap:13px;flex:1;justify-content:center}
.bar-row{display:grid;grid-template-columns:minmax(0,11.5em) minmax(0,1fr) 5.5em;gap:12px;align-items:center;font-size:13px}
.bar-row .name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:600}
.track{height:10px;background:var(--rule-soft);border-radius:999px;overflow:hidden;display:flex}
.track i{display:block;height:100%}
.track .fp{background:var(--fp3)} .track .ff{background:var(--ff3)} .track .nv{background:var(--nv)}
.bar-row .count{color:var(--muted);font-size:12.5px;text-align:right}
.bar-row .clean{color:var(--ok);font-weight:600;font-size:12.5px;text-align:right}
.finding{background:var(--accent-soft);border-color:transparent;box-shadow:none}
.finding .tag{align-self:flex-start;display:inline-flex;gap:6px;align-items:center;background:var(--card);color:var(--accent-ink);border-radius:999px;padding:4px 10px;font-size:12px;font-weight:700}
.finding .big{font:700 18px/1.4 var(--display);letter-spacing:-0.01em;margin:14px 0 10px;color:var(--ink)}
.finding p{margin:0;color:var(--muted);font-size:13.5px}

/* ---------- heatmap ---------- */
.scale{display:flex;flex-wrap:wrap;gap:8px 16px;font-size:12.5px;color:var(--muted)}
.scale span{display:inline-flex;align-items:center;gap:6px}
.tablewrap{overflow-x:auto;margin:0 calc(-1 * var(--pad));padding:0 var(--pad)}
table.heat{border-collapse:collapse;width:100%;min-width:780px;table-layout:fixed}
.heat col.lab{width:260px}
.heat th,.heat td{padding:3px}
.heat thead th{font-weight:600;font-size:12px;color:var(--muted);text-align:center;line-height:1.25;vertical-align:bottom}
.heat thead tr.groups th{color:var(--ink);font-size:13px;font-weight:700;padding-bottom:6px}
.heat thead tr.groups th span{display:block;border-bottom:2px solid var(--rule);padding-bottom:6px;overflow-wrap:anywhere;line-height:1.3}
.heat thead tr.groups th small{display:block;font-weight:500;font-size:11.5px;color:var(--muted);margin-top:2px}
.heat thead tr.cols th{padding-bottom:8px}
.heat thead th:first-child{text-align:left;padding-left:0}
.heat tbody th{text-align:left;padding:3px 12px 3px 0;vertical-align:middle;font-weight:400}
.heat tbody tr + tr th,.heat tbody tr + tr td{border-top:1px solid var(--rule-soft)}
.heat .sid{display:inline-grid;place-items:center;min-width:30px;height:22px;border-radius:6px;background:var(--accent-soft);color:var(--accent-ink);font-weight:700;font-size:12px;margin-right:8px}
.heat .ttl{font-weight:600;font-size:13px;color:var(--ink)}
.heat .cat{display:block;color:var(--muted);font-size:12px;margin:2px 0 0 38px}
.hc{width:100%;height:50px;border:0;border-radius:var(--radius-sm);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;
  font-weight:700;font-size:13px;background:var(--na);color:var(--faint);margin:3px 0}
.hc.ok{background:var(--ok-bg);color:var(--ok)}
.hc.fp1{background:var(--fp1);color:var(--fp)} .hc.fp2{background:var(--fp2);color:var(--on-solid)} .hc.fp3{background:var(--fp3);color:var(--on-solid)}
.hc.ff1{background:var(--ff1);color:var(--ff)} .hc.ff2{background:var(--ff2);color:#3A2A06} .hc.ff3{background:var(--ff3);color:var(--on-solid)}
.hc.nv{background:transparent;border:2px dashed var(--nv);color:var(--muted)}
.hc .pp{display:flex;gap:3px}
.hc .pp i{width:5px;height:5px;border-radius:50%;background:currentColor;opacity:.9}
.hc .pp i.miss{opacity:.28}
.hc:hover{filter:brightness(.97)}
.hc[aria-pressed="true"]{outline:2px solid var(--accent);outline-offset:2px}

/* ---------- failure cards ---------- */
.fcard .fhead{display:flex;align-items:center;gap:10px;margin:0 0 8px}
.fcard .sid{display:inline-grid;place-items:center;min-width:34px;height:26px;border-radius:7px;background:var(--fp-bg);color:var(--fp);font-weight:800;font-size:12.5px}
.fcard h3{margin:0;font-size:15.5px;line-height:1.3}
.fcard .rule{margin:0 0 14px;color:var(--muted);font-size:13px}
.fcard ul{list-style:none;margin:0 0 16px;padding:0;border-top:1px solid var(--rule-soft)}
.fcard li{display:flex;gap:12px;align-items:center;padding:10px 0;border-bottom:1px solid var(--rule-soft)}
.fcard li .who{flex:1;min-width:0}
.fcard li .who b{display:block;font-size:13.5px}
.fcard li .who span{color:var(--muted);font-size:12.5px}
.badge{font-size:12px;font-weight:700;padding:3px 9px;border-radius:999px;white-space:nowrap}
.badge.pass{background:var(--ok-bg);color:var(--ok)} .badge.fpass{background:var(--fp-bg);color:var(--fp)}
.badge.ffail{background:var(--ff-bg);color:var(--ff)} .badge.none{border:1px dashed var(--nv);color:var(--muted)}
.btn{align-self:flex-start;margin-top:auto;background:var(--card);color:var(--accent-ink);border:1px solid var(--rule);border-radius:var(--radius-sm);padding:7px 14px;font-weight:600;font-size:13px}
.btn:hover{border-color:var(--accent);background:var(--accent-soft)}
.okline{grid-column:span 12;margin:0;color:var(--muted);font-size:13.5px;display:flex;align-items:center;gap:8px}
.okline::before{content:"";width:8px;height:8px;border-radius:50%;background:var(--ok-solid);flex:none}

/* ---------- scorecard ---------- */
table.ledger{width:100%;border-collapse:collapse;min-width:760px}
.ledger th,.ledger td{text-align:left;padding:12px;border-bottom:1px solid var(--rule-soft);vertical-align:middle;font-size:13.5px}
.ledger thead th{font-size:12px;font-weight:600;color:var(--muted);border-bottom:1px solid var(--rule);padding-top:0}
.ledger tr:last-child td,.ledger tr:last-child th{border-bottom:0}
.ledger th:first-child,.ledger td:first-child{padding-left:0}
.ledger th:last-child,.ledger td:last-child{padding-right:0}
.ledger .r{text-align:right}
.ledger td.r{font-weight:600}
.ledger .ids{display:block;font-size:12px;color:var(--muted);font-weight:400}
.ledger .bad{color:var(--fp)} .ledger .warn{color:var(--ff)}
.meter{display:inline-block;width:52px;height:6px;background:var(--rule-soft);border-radius:999px;vertical-align:middle;margin-left:10px;overflow:hidden}
.meter i{display:block;height:100%;background:var(--ok-solid);border-radius:999px}
.foot{grid-column:span 12;color:var(--muted);font-size:12.5px;margin:8px 0 0;max-width:96ch}

/* ---------- drawer ---------- */
.backdrop{position:fixed;inset:0;background:rgba(20,30,26,.32);opacity:0;pointer-events:none;z-index:20}
.drawer{position:fixed;top:0;right:0;height:100%;width:min(600px,100%);background:var(--card);z-index:21;transform:translateX(102%);visibility:hidden;
  display:flex;flex-direction:column;border-left:1px solid var(--rule);box-shadow:-16px 0 40px rgba(20,30,26,.12)}
@media (prefers-reduced-motion:no-preference){.drawer{transition:transform .24s ease,visibility .24s}.backdrop{transition:opacity .24s ease}}
body.open .drawer{transform:none;visibility:visible} body.open .backdrop{opacity:1;pointer-events:auto}
.dr-head{display:flex;gap:12px;align-items:flex-start;padding:calc(20px + env(safe-area-inset-top,0px)) 24px 14px;border-bottom:1px solid var(--rule)}
.dr-head h2{margin:0;font-size:18px;line-height:1.3;flex:1}
.dr-head .x{background:var(--card);border:1px solid var(--rule);border-radius:var(--radius-sm);width:34px;height:34px;font-size:18px;line-height:1;flex:none}
.dr-body{padding:18px 24px calc(28px + env(safe-area-inset-bottom,0px));overflow:auto}
.dr-body .sub{color:var(--muted);font-size:13px;margin:0 0 14px}
.tabs{display:inline-flex;gap:2px;margin:0 0 16px;background:var(--panel);border:1px solid var(--rule);border-radius:999px;padding:3px}
.tabs button{background:transparent;border:0;border-radius:999px;padding:6px 14px;font-weight:600;font-size:13px;color:var(--muted)}
.tabs button[aria-pressed="true"]{background:var(--card);color:var(--ink);box-shadow:0 1px 3px rgba(0,0,0,.08)}
.note{border:1px solid var(--fp2);background:var(--fp-bg);padding:10px 14px;margin:0 0 16px;border-radius:var(--radius-sm);font-size:13.5px}
.note.ok{border-color:var(--ok-solid);background:var(--ok-bg)}
.facts{width:100%;border-collapse:collapse;margin:0 0 18px;font-size:13.5px}
.facts th,.facts td{padding:7px 0;border-bottom:1px solid var(--rule-soft);text-align:right}
.facts th:first-child,.facts td:first-child{text-align:left;color:var(--muted);font-weight:500}
.facts thead th{font-weight:600;color:var(--muted);font-size:12px}
.facts td.diff{color:var(--fp);font-weight:700}
details{border:1px solid var(--rule);border-radius:10px;margin:0 0 8px;background:var(--card);overflow:hidden}
summary{cursor:pointer;padding:10px 14px;display:flex;gap:10px;align-items:center;font-weight:600;font-size:13.5px}
summary .badge{margin-left:auto}
pre{white-space:pre-wrap;word-wrap:break-word;margin:0;padding:12px 14px;border-top:1px solid var(--rule-soft);background:var(--panel);
  font:13px/1.6 var(--font);max-height:440px;overflow:auto}
h3.dh{font-size:14px;margin:22px 0 10px}
</style>
</head>
<body>
<div class="shell">
  <aside class="side" aria-label="Report navigation">
    <a class="brand" href="#overview" aria-label="AI critiQ, back to top">
      <svg width="34" height="34" viewBox="0 0 34 34" aria-hidden="true">
        <rect width="34" height="34" rx="10" fill="var(--accent)"/>
        <circle cx="15.5" cy="15.5" r="7.2" fill="none" stroke="#fff" stroke-width="2.4"/>
        <path d="M20.6 20.6 L25.5 25.5" stroke="#fff" stroke-width="2.6" stroke-linecap="round"/>
        <path d="M12.4 15.6 l2.2 2.2 l4-4.4" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <span><span class="word"><span class="ai">AI</span> criti<span class="q">Q</span></span><small>Reviewer reliability evals</small></span>
    </a>
    <nav class="nav">
      <a href="#overview"><svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><rect x="1.5" y="1.5" width="5.5" height="5.5" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.5"/><rect x="9" y="1.5" width="5.5" height="5.5" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.5"/><rect x="1.5" y="9" width="5.5" height="5.5" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.5"/><rect x="9" y="9" width="5.5" height="5.5" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>Overview</a>
      <a href="#heatmap"><svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M2 2h3v3H2zM6.5 2h3v3h-3zM11 2h3v3h-3zM2 6.5h3v3H2zM6.5 6.5h3v3h-3zM11 6.5h3v3h-3zM2 11h3v3H2zM6.5 11h3v3h-3zM11 11h3v3h-3z" fill="currentColor" opacity=".85"/></svg>Heatmap</a>
      <a href="#findings"><svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M8 1.8 15 14H1z" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M8 6.2v3.6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="8" cy="11.8" r=".9" fill="currentColor"/></svg>Where models failed</a>
      <a href="#scorecard"><svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M2 14V8M6 14V4M10 14V9M14 14V2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>Scorecard</a>
    </nav>
    <div class="side-foot">
      <div>
        <p class="lbl">Theme</p>
        <div class="swatches" role="group" aria-label="Color theme" id="swatches"></div>
      </div>
      <div class="meta" id="meta"></div>
    </div>
  </aside>

  <main>
    <header class="page-head" id="overview">
      <div>
        <p class="eyebrow">Fintech · Interest calculation review</p>
        <h1>Can AI reviewers check an interest calculation?</h1>
        <p class="lede">Each scenario is a loan interest calculation shown to every model twice: once fully correct, once with a single expert-level error. A reliable reviewer accepts the first and rejects the second. Expected answers are computed in code from the ISDA conventions.</p>
      </div>
    </header>
    <div id="mock"></div>

    <div class="grid">
      <div class="span-12 grid" id="kpis" style="gap:var(--gap)"></div>

      <div class="card span-4"><div class="card-head"><div><h2>Outcome of every run</h2><p>All graded responses</p></div></div><div class="donut-wrap" id="donut"></div></div>
      <div class="card span-4"><div class="card-head"><div><h2>Failed runs by model</h2><p>Wrong or missing verdicts</p></div></div><div class="bars" id="bars"></div></div>
      <div class="card span-4 wide-md finding"><span class="tag"><svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><path d="M6 .8l1.5 3.4 3.7.4-2.8 2.5.8 3.6L6 8.9 2.8 10.7l.8-3.6L.8 4.6l3.7-.4z" fill="currentColor"/></svg>Key finding</span><p class="big" id="finding"></p><p id="findingSub"></p></div>

      <section class="card span-12" id="heatmap" aria-labelledby="heatTitle">
        <div class="card-head" style="flex-wrap:wrap">
          <div><h2 id="heatTitle">Scenario × model heatmap</h2><p>Two columns per model: does it accept the correct version, and reject the flawed one? Dots are runs. Select a cell to read the responses.</p></div>
          <div class="scale" aria-label="Color key">
            <span><i class="sw ok"></i>All runs right</span><span><i class="sw ff"></i>Rejected correct work</span>
            <span><i class="sw fp"></i>Accepted a wrong calculation</span><span><i class="sw nv"></i>No verdict</span>
          </div>
        </div>
        <div class="tablewrap"><table class="heat" id="heat"></table></div>
      </section>

      <div class="section-head" id="findings"><h2>Where models failed</h2><p id="findCount"></p></div>
      <div class="span-12 grid" id="spot" style="gap:var(--gap)"></div>
      <p class="okline" id="okline" hidden></p>

      <div class="section-head" id="scorecard"><h2>Scorecard</h2><p>Rates average over tasks, so extra repeat runs don’t outweigh other scenarios.</p></div>
      <div class="card span-12"><div class="tablewrap"><table class="ledger" id="ledger"></table></div></div>

      <p class="foot">Grading is deterministic: the last “VERDICT: CORRECT” or “VERDICT: INCORRECT” line in each response is compared with the expected verdict. No AI grader is used. A response without a verdict line counts as a failure and is shown separately as “no verdict”.</p>
    </div>
  </main>
</div>

<div class="backdrop" id="backdrop"></div>
<aside class="drawer" id="drawer" role="dialog" aria-modal="true" aria-labelledby="drTitle" aria-hidden="true">
  <div class="dr-head"><h2 id="drTitle"></h2><button class="x" id="drClose" type="button" aria-label="Close">×</button></div>
  <div class="dr-body" id="drBody"></div>
</aside>

<script id="data" type="application/json">__DATA__</script>
<script>
const D = JSON.parse(document.getElementById('data').textContent);
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const models = D.models.map(m => m.label);
const isCheck = m => /-t\d+$/.test(m);
const mainModels = models.filter(m => !isCheck(m));
const LABEL = {pass:'Right verdict', fpass:'Accepted a wrong calculation', ffail:'Rejected a correct calculation', none:'No verdict'};
const runsOf = (tid, m) => (D.responses[tid] || {})[m] || [];
const outcome = (task, v) => v === 'NONE' ? 'none' : v === task.expected ? 'pass' : task.expected === 'INCORRECT' ? 'fpass' : 'ffail';
const tally = (tid, m) => { const t = D.tasks[tid], o = runsOf(tid, m).map(r => outcome(t, r.verdict));
  return {n:o.length, pass:o.filter(x => x === 'pass').length, fpass:o.filter(x => x === 'fpass').length,
          ffail:o.filter(x => x === 'ffail').length, none:o.filter(x => x === 'none').length}; };
const joinAnd = a => a.length < 2 ? (a[0] || '') : a.slice(0, -1).join(', ') + ' and ' + a.slice(-1);

/* theme palette (white Mint is the default; choice lasts for this visit) */
const PALETTES = [['mint','Mint','#FFFFFF','#2FA57C'],['lagoon','Lagoon','#FFFFFF','#2B8FB8'],['sand','Sand','#FDFBF7','#6E9C6A'],['night','Night','#0F1613','#5BD3A3']];
function renderSwatches(){
  const cur = document.documentElement.dataset.palette;
  $('#swatches').innerHTML = PALETTES.map(([id, name, bg, ac]) =>
    `<button class="swatch" type="button" data-palette="${id}" aria-pressed="${cur === id}" aria-label="${name} theme" title="${name}">
      <span style="background:linear-gradient(135deg,${bg} 0 50%,${ac} 50% 100%)"></span></button>`).join('');
}
$('#swatches').addEventListener('click', e => { const b = e.target.closest('.swatch'); if (!b) return;
  document.documentElement.dataset.palette = b.dataset.palette; renderSwatches(); });
renderSwatches();

/* totals */
const tids = Object.keys(D.tasks);
const all = tids.flatMap(t => mainModels.flatMap(m => runsOf(t, m).map(r => ({t, m, o: outcome(D.tasks[t], r.verdict)}))));
const count = k => all.filter(x => x.o === k).length;
const fails = all.filter(x => x.o !== 'pass');
const maxRuns = Math.max(0, ...tids.flatMap(t => models.map(m => runsOf(t, m).length)));
$('#meta').innerHTML = `${all.length} responses graded · up to ${maxRuns} runs per task<br>Built ${esc(D.generated)}`;
if (D.mock) $('#mock').innerHTML = '<p class="mockbar">These are mock responses from the offline pipeline test, not real model results.</p>';

function failuresFor(s){
  const out = [];
  models.forEach(m => {
    const c = s.correct ? tally(s.correct, m) : null, e = s.error ? tally(s.error, m) : null;
    if (e && e.fpass) out.push({m, kind:'fpass', k:e.fpass, n:e.n, text:`Accepted the flawed calculation in ${e.fpass} of ${e.n} runs`, tid:s.error});
    if (c && c.ffail) out.push({m, kind:'ffail', k:c.ffail, n:c.n, text:`Rejected the correct calculation in ${c.ffail} of ${c.n} runs`, tid:s.correct});
    if (c && c.none) out.push({m, kind:'none', k:c.none, n:c.n, text:`No verdict on the correct version in ${c.none} of ${c.n} runs`, tid:s.correct});
    if (e && e.none) out.push({m, kind:'none', k:e.none, n:e.n, text:`No verdict on the flawed version in ${e.none} of ${e.n} runs`, tid:s.error});
  });
  return out.sort((a, b) => b.k / b.n - a.k / a.n);
}
const failScen = D.scenarios.map(s => ({s, f: failuresFor(s)})).filter(x => x.f.length);
const failModels = mainModels.filter(m => failScen.some(x => x.f.some(f => f.m === m)));
const cleanModels = mainModels.filter(m => !failModels.includes(m) && tids.some(t => runsOf(t, m).length));

/* KPI tiles */
const ICONS = {
  models:'<svg width="16" height="16" viewBox="0 0 16 16"><rect x="2" y="2" width="12" height="9" rx="2" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M5 14h6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>',
  scen:'<svg width="16" height="16" viewBox="0 0 16 16"><path d="M3 2.5h10M3 6.5h10M3 10.5h6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>',
  ok:'<svg width="16" height="16" viewBox="0 0 16 16"><path d="M3 8.5l3 3 7-7" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  fail:'<svg width="16" height="16" viewBox="0 0 16 16"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>'};
const kpi = (icon, label, val, hint, cls = '') => `<div class="card kpi span-3 ${cls}"><div class="label"><span class="icon" aria-hidden="true">${icon}</span>${label}</div><div class="value">${val}</div><div class="hint">${hint}</div></div>`;
$('#kpis').innerHTML =
  kpi(ICONS.models, 'Models tested', mainModels.length, (cleanModels.length ? `${cleanModels.length} with no failures` : 'Same settings for every model') + (models.length > mainModels.length ? ` · plus ${models.length - mainModels.length} temperature checks` : '')) +
  kpi(ICONS.scen, 'Scenarios', D.scenarios.length, `${tids.length} tasks: one correct and one flawed version each`) +
  kpi(ICONS.ok, 'Right verdicts', all.length ? Math.round(100 * count('pass') / all.length) + '%' : '–', `${count('pass')} of ${all.length} runs`) +
  kpi(ICONS.fail, 'Failed runs', fails.length, failScen.length ? `All in ${joinAnd(failScen.map(x => x.s.id))}` : 'None', fails.length ? 'alert' : '');

/* donut */
(function(){
  const parts = [['ok', count('pass'), 'Right verdict', 'var(--ok-solid)'], ['ff', count('ffail'), 'Rejected correct work', 'var(--ff3)'],
                 ['fp', count('fpass'), 'Accepted a wrong calculation', 'var(--fp3)'], ['nv', count('none'), 'No verdict', 'var(--nv)']];
  const total = all.length || 1, r = 50, C = 2 * Math.PI * r;
  let off = 0;
  const arcs = parts.filter(p => p[1]).map(([k, v, , col]) => { const len = C * v / total;
    const a = `<circle cx="68" cy="68" r="${r}" fill="none" stroke="${col}" stroke-width="14" stroke-dasharray="${len} ${C - len}" stroke-dashoffset="${-off}" transform="rotate(-90 68 68)"/>`;
    off += len; return a; }).join('');
  const pctOk = all.length ? Math.round(100 * count('pass') / all.length) + '%' : '–';
  $('#donut').innerHTML = `<svg class="donut" viewBox="0 0 136 136" role="img" aria-label="${count('pass')} right verdicts out of ${all.length} runs">
      <circle cx="68" cy="68" r="${r}" fill="none" stroke="var(--rule-soft)" stroke-width="14"/>${arcs}
      <text x="68" y="69" text-anchor="middle" class="val">${pctOk}</text><text x="68" y="88" text-anchor="middle" class="cap">right verdicts</text></svg>
    <ul class="legend">${parts.map(([k, v, label]) => `<li><i class="sw ${k}"></i><span>${label}</span><b>${v}</b></li>`).join('')}</ul>`;
})();

/* bars */
(function(){
  const rows = mainModels.map(m => { const rs = all.filter(x => x.m === m);
    return {m, n: rs.length, fp: rs.filter(x => x.o === 'fpass').length, ff: rs.filter(x => x.o === 'ffail').length, nv: rs.filter(x => x.o === 'none').length}; });
  const max = Math.max(1, ...rows.map(r => r.fp + r.ff + r.nv));
  $('#bars').innerHTML = rows.map(r => { const f = r.fp + r.ff + r.nv;
    const seg = (cls, v) => v ? `<i class="${cls}" style="width:${100 * v / max}%"></i>` : '';
    return `<div class="bar-row"><span class="name" title="${esc(r.m)}">${esc(r.m)}</span>
      <span class="track" role="img" aria-label="${esc(r.m)}: ${f} failed runs of ${r.n}">${seg('ff', r.ff)}${seg('fp', r.fp)}${seg('nv', r.nv)}</span>
      ${f ? `<span class="count">${f} of ${r.n}</span>` : `<span class="clean">None</span>`}</div>`; }).join('');
})();

/* finding */
if (!all.length) $('#finding').textContent = 'No responses yet. Run the eval with python run.py, then rebuild this report.';
else if (!failScen.length) $('#finding').textContent = 'Every model reached the right verdict on every scenario.';
else {
  $('#finding').textContent = `${failModels.length} of ${mainModels.length} models misjudged correct or flawed calculations. Every failure came from ${failScen.length === 1 ? 'one scenario' : failScen.length + ' scenarios'}: ${joinAnd(failScen.map(x => x.s.id))}.`;
  $('#findingSub').textContent = cleanModels.length ? `${joinAnd(cleanModels)} made no mistakes in any run. Failures went both ways: accepting wrong answers and rejecting right ones.`
                                                    : 'Failures went both ways: accepting wrong answers and rejecting right ones.';
}

/* heatmap */
let current = null;
function heatClass(tid, m){
  const x = tally(tid, m); if (!x.n) return 'na';
  if (x.pass === x.n) return 'ok';
  if (x.none === x.n) return 'nv';
  const f = (x.n - x.pass) / x.n, lvl = f >= 0.8 ? 3 : f >= 0.4 ? 2 : 1;
  return (D.tasks[tid].version === 'error' ? 'fp' : 'ff') + lvl;
}
function renderHeat(){
  const cols = `<colgroup><col class="lab">${models.map(() => '<col><col>').join('')}</colgroup>`;
  const head = `<thead><tr class="groups"><th></th>${models.map(m => `<th colspan="2" scope="colgroup"><span title="${esc(m)}">${esc(m.replace(/-t\d+$/, ''))}${isCheck(m) ? '<small>T = 1.0 check</small>' : ''}</span></th>`).join('')}</tr>
    <tr class="cols"><th scope="col">Scenario</th>${models.map(() => '<th scope="col">Accepts correct</th><th scope="col">Rejects flawed</th>').join('')}</tr></thead>`;
  const body = D.scenarios.map(s => `<tr><th scope="row"><span class="sid">${esc(s.id)}</span><span class="ttl">${esc(s.title)}</span><span class="cat">${esc(s.category)}</span></th>
    ${models.map(m => ['correct', 'error'].map(v => { const tid = s[v]; if (!tid) return '<td></td>';
      const x = tally(tid, m), t = D.tasks[tid], cls = heatClass(tid, m);
      const dots = runsOf(tid, m).map(r => `<i class="${outcome(t, r.verdict) === 'pass' ? '' : 'miss'}"></i>`).join('');
      const label = `${s.id} ${v === 'correct' ? 'correct version' : 'flawed version'}, ${m}: ${x.n ? `${x.pass} of ${x.n} runs right` : 'no runs'}`;
      return `<td><button class="hc ${cls}" type="button" data-task="${tid}" data-model="${esc(m)}" aria-pressed="${current === tid + '|' + m}" aria-label="${esc(label)}">
        <span>${x.n ? x.pass + '/' + x.n : '–'}</span>${x.n ? `<span class="pp" aria-hidden="true">${dots}</span>` : ''}</button></td>`; }).join('')).join('')}</tr>`).join('');
  $('#heat').innerHTML = cols + head + '<tbody>' + body + '</tbody>';
}
$('#heat').addEventListener('click', e => { const b = e.target.closest('.hc'); if (b) openDetail(b.dataset.task, b.dataset.model, b); });

/* failure cards */
$('#findCount').textContent = failScen.length ? `${failScen.length} of ${D.scenarios.length} scenarios` : 'No failures';
$('#spot').innerHTML = failScen.map(({s, f}) => `<article class="card fcard span-6">
    <div class="fhead"><span class="sid">${esc(s.id)}</span><h3>${esc(s.title)}</h3></div>
    <p class="rule">${esc(s.note || '')}</p>
    <ul>${f.map(x => `<li><span class="who"><b>${esc(x.m)}</b><span>${esc(x.text)}</span></span><span class="badge ${x.kind}">${x.k}/${x.n}</span></li>`).join('')}</ul>
    <button class="btn" type="button" data-task="${f[0].tid}" data-model="${esc(f[0].m)}">Read the responses →</button></article>`).join('');
$('#spot').addEventListener('click', e => { const b = e.target.closest('.btn'); if (b) openDetail(b.dataset.task, b.dataset.model, b); });
const okIds = D.scenarios.filter(s => !failScen.some(x => x.s.id === s.id)).map(s => s.id);
if (all.length && okIds.length){ $('#okline').hidden = false; $('#okline').textContent = `Every model handled ${joinAnd(okIds)} correctly in every run.`; }

/* scorecard */
const pct = x => x == null ? '–' : Math.round(100 * x) + '%';
const meter = x => x == null ? '' : `<span class="meter" aria-hidden="true"><i style="width:${Math.round(100 * x)}%"></i></span>`;
$('#ledger').innerHTML = `<thead><tr><th>Model</th><th class="r">Errors caught (TPR)</th><th class="r">Correct work accepted (TNR)</th><th class="r">Balanced accuracy</th>
  <th class="r">Wrong calculations accepted</th><th class="r">Correct calculations rejected</th><th class="r">No verdict</th></tr></thead><tbody>` +
  D.models.map(({label: m, ids}) => {
    const rates = v => tids.filter(t => D.tasks[t].version === v).map(t => tally(t, m)).filter(x => x.n).map(x => x.pass / x.n);
    const avg = a => a.length ? a.reduce((p, q) => p + q, 0) / a.length : null;
    const tpr = avg(rates('error')), tnr = avg(rates('correct')), bal = tpr != null && tnr != null ? (tpr + tnr) / 2 : null;
    const sum = (v, k) => tids.filter(t => D.tasks[t].version === v).reduce((a, t) => a + tally(t, m)[k], 0);
    const fp = sum('error', 'fpass'), ff = sum('correct', 'ffail'), ne = sum('error', 'n'), nc = sum('correct', 'n'), nv = sum('error', 'none') + sum('correct', 'none');
    return `<tr><th scope="row">${esc(m)}<span class="ids">${esc(ids.join(', '))}</span></th><td class="r">${pct(tpr)}${meter(tpr)}</td><td class="r">${pct(tnr)}${meter(tnr)}</td>
      <td class="r">${pct(bal)}</td><td class="r ${fp ? 'bad' : ''}">${fp}/${ne}</td><td class="r ${ff ? 'warn' : ''}">${ff}/${nc}</td><td class="r">${nv}</td></tr>`;
  }).join('') + '</tbody>';

/* drawer */
const FIELDS = [['payment_date','Payment date'],['accrual_end','Accrual end'],['days','Days'],['denominator','Denominator'],['interest','Interest (USD)']];
let lastTrigger = null;
function openDetail(tid, focusModel, trigger){
  if (trigger) lastTrigger = trigger;
  current = tid + '|' + (focusModel || ''); renderHeat();
  const t = D.tasks[tid], s = D.scenarios.find(x => x.id === t.scenario), isErr = t.version === 'error';
  const tab = (v, label) => s[v] ? `<button type="button" data-task="${s[v]}" aria-pressed="${s[v] === tid}">${label}</button>` : '';
  const facts = `<table class="facts"><thead><tr><th></th><th>Correct</th><th>Explanation says</th></tr></thead><tbody>` +
    FIELDS.map(([k, label]) => { const d = String(t.truth[k]) !== String(t.claims[k]);
      return `<tr><td>${label}</td><td>${esc(t.truth[k])}</td><td class="${d ? 'diff' : ''}">${esc(t.claims[k])}</td></tr>`; }).join('') + '</tbody></table>';
  const order = focusModel ? [focusModel, ...models.filter(m => m !== focusModel)] : models;
  const blocks = order.map(m => runsOf(tid, m).map(r => { const o = outcome(t, r.verdict);
    return `<details ${m === focusModel && o !== 'pass' ? 'open' : ''}><summary>${esc(m)} · run ${r.run}<span class="badge ${o}">${LABEL[o]}</span></summary><pre>${esc(r.text || '(empty response)')}</pre></details>`;
  }).join('')).join('');
  $('#drTitle').textContent = `${s.id} · ${s.title}`;
  $('#drBody').innerHTML = `<p class="sub">${esc(s.category)}</p>
    <div class="tabs" role="group" aria-label="Version">${tab('correct', 'Correct version')}${tab('error', 'Flawed version')}</div>
    ${isErr ? `<p class="note"><strong>Injected error.</strong> ${esc(s.note)}</p>` : '<p class="note ok"><strong>No error.</strong> This explanation is fully correct; rejecting it is a false fail.</p>'}
    ${facts}<h3 class="dh">Responses</h3>${blocks || '<p class="sub">No responses recorded for this version.</p>'}
    <h3 class="dh">Prompt sent to every model</h3><details><summary>Show prompt</summary><pre>${esc(t.prompt)}</pre></details>`;
  $('#drBody').dataset.model = focusModel || '';
  document.body.classList.add('open'); $('#drawer').setAttribute('aria-hidden', 'false'); $('#drClose').focus();
}
function closeDetail(){
  document.body.classList.remove('open'); $('#drawer').setAttribute('aria-hidden', 'true');
  const key = lastTrigger && [lastTrigger.dataset.task, lastTrigger.dataset.model];
  current = null; renderHeat();
  const target = lastTrigger && document.body.contains(lastTrigger) ? lastTrigger
    : key && [...document.querySelectorAll('.hc')].find(b => b.dataset.task === key[0] && b.dataset.model === key[1]);
  if (target) target.focus();
}
$('#drBody').addEventListener('click', e => { const b = e.target.closest('.tabs button'); if (b) openDetail(b.dataset.task, $('#drBody').dataset.model || null); });
$('#drClose').onclick = closeDetail; $('#backdrop').onclick = closeDetail;
document.addEventListener('keydown', e => { if (e.key === 'Escape' && document.body.classList.contains('open')) closeDetail(); });

renderHeat();
</script>
</body>
</html>
"""
