# Companion video: tooling and sources

**Watch the video: https://youtu.be/iZwTJmpY7Jg**

This folder holds everything used to make the YouTube video about this project ("I built a local RAG. Most of my best ideas failed."). It is
optional: the RAG project itself does not depend on any of it. Rendered audio and video are **not** committed (they are large and
regenerable); this folder has the sources and the scripts to rebuild them.

## What is here

| Path | What it is |
|---|---|
| `script.md` | The video script: 11 segments, narration text, visuals, upload text |
| `narration/` | `build_narration.py` turns the script's narration into audio with a synthetic voice (Kokoro-82M) and sentence timings |
| `anim/` | A [Remotion](https://www.remotion.dev) project (React) with the animated clips and the terminal-replay clips; every animation step is timed to a spoken phrase |
| `demo/` | The commands whose real output the terminal replays show, plus the script that captures a real ollmcp session |
| `finalize.py` | Joins the 11 clips and writes the upload folder (video, captions, chapters, description) |
| `upload/` | Captions, description, tags, thumbnail and checklist for the published video |
| `live-recording-guide.md`, `make_live_guide.py` | A guide for recording the five live segments yourself, in case you want real screen recordings instead of replays |

## How the video was made

- **Narration is synthetic** (Kokoro-82M, voice `af_heart`).
- **Six segments are animations**; **five are terminal replays** of real captured output (command output, a Phoenix screenshot, and a real ollmcp
  session). Each replay frame is labelled on screen as a replay, not a live screen recording.
- All numbers in the video come from this repository's own evaluation runs: 19 in-scope and 7 out-of-scope questions, tuned on the same
  questions, on synthetic data. Treat them as illustrations, not benchmarks.

## Rebuilding it

You need Node.js, Python 3.12, `ffmpeg`, and `espeak-ng` (Kokoro uses it; on macOS `brew install ffmpeg espeak-ng`), plus the Kokoro Python environment in `narration/`. Run commands from the project root; the full,
step-by-step commands with run details are in [`docs/commands.md`](../commands.md), section 9.

```bash
# 1. narration audio and timings (Kokoro)
cd docs/video/narration && uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python kokoro soundfile
.venv/bin/python build_narration.py --engine kokoro --voice af_heart

# 2. the clips (the first command renders the 6 animations; the loop renders the 5 terminal replays)
cd ../anim && npm install && npm run render:all
for c in Seg3 Seg4 Seg8 Seg9 Seg10; do npx remotion render src/index.ts $c out/$c.mp4 --overwrite --port=3100; done

# 3. assemble the final video and upload folder
cd ../../.. && python3 docs/video/finalize.py
```

To refresh the captured output behind the replays (needs Ollama, Qdrant and Phoenix running), see `demo/` and `docs/commands.md` section 9.5.

## Licenses

The code here is MIT like the rest of the repository. Remotion, Kokoro and the other tools it uses have their own licenses (Remotion in particular has
terms that depend on company size), and the dataset shown in the video is CC-BY-NC-4.0; see the root README.
