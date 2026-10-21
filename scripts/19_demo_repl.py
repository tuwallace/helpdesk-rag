"""Interactive demo for recording: loads the pipeline once, warms it up, then answers each question you type and
shows how long it took, whether it was refused, and the cited tickets. Quit with an empty line or Ctrl+D.
(A fresh `python -m rag.pipeline` pays ~8 s of start-up every time, which hides the real per-question speed.)"""
import faulthandler, os, sys, time
sys.path.insert(0, "src")
from rag.pipeline import answer

if os.getenv("DEMO_WATCHDOG"):                      # debugging aid: print every thread's stack if one step takes >45 s
    faulthandler.dump_traceback_later(45, repeat=True, file=sys.stderr)
print("warming up (loading models)...", flush=True)
answer("warm up question about outlook password prompts")          # one throwaway call loads rewrite model + reranker
print("ready. Type a question.\n", flush=True)
while True:
    try:
        q = input("question> ").strip()
    except EOFError:
        break
    if not q:
        break
    t = time.perf_counter(); r = answer(q); dt = time.perf_counter() - t
    print(f"\n  {r['answer']}\n  sources={r['sources']}  refused={r['refused']}  [{dt:.2f}s]\n", flush=True)
