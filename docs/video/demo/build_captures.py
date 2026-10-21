"""Bundles everything under docs/video/anim/public/captures into docs/video/anim/src/captures.json for the terminal-replay clips.
Run after re-capturing:  python3 docs/video/demo/build_captures.py"""
import json, pathlib, subprocess
ROOT = pathlib.Path(__file__).resolve().parents[3]
CAP = ROOT / "docs/video/anim/public/captures"
sh = lambda cmd: subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True).stdout.rstrip("\n")
out = {
    "seg3": (CAP / "seg3.txt").read_text().strip("\n"),
    "seg4": (CAP / "seg4.txt").read_text().strip("\n"),
    "seg8": json.loads((CAP / "seg8.json").read_text()),
    "seg9": (CAP / "seg9.txt").read_text().strip("\n"),
    "ollmcp": json.loads((CAP / "ollmcp.json").read_text()) if (CAP / "ollmcp.json").exists() else None,
    # real file contents shown as inserts in segment 10
    "grep_priority": sh('grep -n -B1 -A1 "No optional filters" src/rag/mcp_server.py'),
    "sed_tool": sh("sed -n 9,17p src/rag/mcp_server.py"),
    "grep_floor": sh('grep -n "ANSWER_FLOOR" src/rag/config.py'),
}
(ROOT / "docs/video/anim/src/captures.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
print({k: (len(v) if isinstance(v, (str, list)) else type(v).__name__) for k, v in out.items()})
