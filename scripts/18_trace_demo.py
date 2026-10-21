"""Run a few questions through answer(), flush spans to Phoenix, then read them back over Phoenix's REST API
and print per-stage latency. UI: http://localhost:6006  (project: helpdesk-rag)."""
import collections, datetime as dt, json, statistics, sys, time, urllib.request
START = dt.datetime.now(dt.timezone.utc)                 # only traces started after this moment belong to this run
sys.path.insert(0, "src")
from opentelemetry import trace
from rag.pipeline import answer

QUESTIONS = sys.argv[1:] or [
    "outlok keeps askin me to sign in again on my macbook",
    "corporate network access drops every quarter hour when I travel",
    "what time does the cafeteria open on fridays",          # out-of-scope: should stop at the floor
]
for q in QUESTIONS:
    r = answer(q); print(f"{(r['refused'] or 'answered'):12s} {q[:60]}")
trace.get_tracer_provider().force_flush()
time.sleep(2)                                               # let Phoenix ingest

url = "http://localhost:6006/v1/projects/helpdesk-rag/spans?limit=500"
t = lambda s: dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
spans = json.load(urllib.request.urlopen(url))["data"]
by_trace = collections.defaultdict(list)
for s in spans: by_trace[s["context"]["trace_id"]].append(s)
mine = {tid for tid, ss in by_trace.items() for s in ss
        if s["parent_id"] is None and s["name"] == "rag.answer" and t(s["start_time"]) >= START}
by_trace = {tid: ss for tid, ss in by_trace.items() if tid in mine}          # ignore older runs, MCP traffic, other scripts
spans = [s for ss in by_trace.values() for s in ss]

print(f"\n{len(spans)} spans in {len(by_trace)} traces\n")
per_stage = collections.defaultdict(list)
for tid, ss in sorted(by_trace.items(), key=lambda kv: min(x["start_time"] for x in kv[1])):   # chronological: first run first
    root = next(s for s in ss if s["parent_id"] is None)
    q = (root["attributes"].get("input.value") or "")[:55]
    total = (t(root["end_time"]) - t(root["start_time"])).total_seconds()
    print(f"trace: {q!r}  total={total:.2f}s  refused={root['attributes'].get('refused')}")
    for s in sorted(ss, key=lambda s: s["start_time"]):
        d = (t(s["end_time"]) - t(s["start_time"])).total_seconds()
        per_stage[s["name"]].append(d)
        print(f"    {s['name']:26s} {d:6.2f}s  {100*d/total:4.0f}%")
print("\nmean latency by stage (all traces)")
for name, v in sorted(per_stage.items(), key=lambda x: -statistics.mean(x[1])):
    print(f"  {name:26s} n={len(v):2d}  mean={statistics.mean(v):.2f}s")
