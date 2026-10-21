"""Drives the REAL ollmcp client through a pseudo-terminal and records what a person would SEE on screen.
Raw output is fed through a terminal emulator (pyte), so spinners and the in-place redraw of the streaming answer resolve
into the final screen text. Session: /hil (turn off the default per-call confirmation), /st (hide thinking text), /mc -> sp ->
system prompt from ollmcp_system_prompt.txt -> s, then the first two prompts of seg10_prompts.txt.
Run from the project root:
  uv run --no-project --python 3.12 --with pexpect --with pyte python docs/video/demo/capture_ollmcp.py
Writes docs/video/anim/public/captures/ollmcp.json  ({"lines": [...], "marks": {...}, "seconds": {...}})."""
import json, os, pathlib, re, time
import pexpect, pyte

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = ROOT / "docs/video/anim/public/captures/ollmcp.json"
SYSTEM = (ROOT / "docs/video/demo/ollmcp_system_prompt.txt").read_text().strip()
PROMPTS = [l.strip() for l in (ROOT / "docs/video/demo/seg10_prompts.txt").read_text().splitlines() if l.strip() and not l.startswith("#")][:2]
COLS, ROWS = 110, 60
ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07]*\x07|\x1b[=>()][0-9A-B]?")

screen = pyte.HistoryScreen(COLS, ROWS, history=5000, ratio=0.5); stream = pyte.Stream(screen)
child = pexpect.spawn("ollmcp", ["-j", "mcp.json", "-m", "qwen3:8b"], cwd=str(ROOT), encoding="utf-8", dimensions=(ROWS, COLS),
                      env={**os.environ, "TERM": "xterm-256color"})
raw_tail = ""

def pump(timeout=1.0):
    global raw_tail
    try:
        chunk = child.read_nonblocking(65536, timeout=timeout)
    except pexpect.TIMEOUT:
        return False
    stream.feed(chunk); raw_tail = (raw_tail + chunk)[-400:]; return True

def drain(sec):
    t0 = time.time()
    while time.time() - t0 < sec: pump(0.5)

def settle(quiet=6.0, minimum=3.0, limit=420.0):
    """Wait until output has been quiet for `quiet` s and the last thing on screen is the prompt character."""
    t0 = last = time.time()
    while time.time() - t0 < limit:
        if pump(1.0): last = time.time()
        if time.time() - last >= quiet and time.time() - t0 >= minimum and "❯" in ANSI.sub("", raw_tail)[-120:]: break
    return time.time() - t0 - quiet

def transcript():
    hist = ["".join(ch.data for ch in (row[x] for x in range(COLS))).rstrip() for row in screen.history.top for x in [0]] if False else []
    rows = []
    for row in screen.history.top:
        rows.append("".join(row[x].data for x in range(COLS)).rstrip())
    rows += [l.rstrip() for l in screen.display]
    while rows and not rows[-1]: rows.pop()
    return rows

settle(quiet=5.0, minimum=5.0)                               # banner and first prompt
marks, seconds = {"banner_end": len(transcript())}, {}
for cmd in ("/hil", "/st"):
    child.sendline(cmd); drain(3)
child.sendline("/mc"); drain(3); child.sendline("sp"); drain(2); child.sendline(SYSTEM); drain(2); child.sendline("s"); drain(4)
marks["setup_end"] = len(transcript())
for i, text in enumerate(PROMPTS, 1):
    marks[f"p{i}_start"] = len(transcript())
    child.sendline(text); seconds[f"p{i}"] = round(settle(), 1)
    print(f"prompt {i}: ~{seconds[f'p{i}']}s", flush=True)
marks["end"] = len(transcript())
child.sendline("/quit"); time.sleep(1); child.close()
OUT.write_text(json.dumps({"lines": transcript(), "marks": marks, "seconds": seconds, "prompts": PROMPTS}, indent=1, ensure_ascii=False))
print("saved", OUT, len(transcript()), "lines")
