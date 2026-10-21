#!/usr/bin/env python3
"""Builds the upload folder: docs/video/upload/{helpdesk-rag-video.mp4, captions.srt, thumbnail.png, description.txt, README.txt}.
Joins the 11 rendered clips (anim/out/*.mp4) in script order, trims the idle tail of each clip, fades in/out, and writes captions
and chapters from the real clip durations and the narration timings.   Run:  python3 docs/video/finalize.py"""
import json, pathlib, shutil, subprocess, textwrap

HERE = pathlib.Path(__file__).resolve().parent
OUT, UP = HERE / "anim/out", HERE / "upload"
N = json.loads((HERE / "anim/src/narration.json").read_text())
ORDER = [("Hook", "seg1", "Hook"), ("Pipeline", "seg2", "What I built"), ("Seg3", "seg3", "The data twist"), ("Seg4", "seg4", 'The "printer" problem'),
         ("Recall", "seg5", "The fix: grouped pool + reranking"), ("FailedIdeas", "seg6", "What didn't work"), ("ReadingNumbers", "seg7", "Evaluating honestly"),
         ("Seg8", "seg8", 'Knowing when to say "I don\'t know"'), ("Seg9", "seg9", "Tracing: where the time goes"), ("Seg10", "seg10", "ollmcp: a local model uses the tool"),
         ("Takeaways", "seg11", "Takeaways")]
TRIM = 2.4          # the 2 s hold Remotion adds + the 0.4 s of silence the narration builder appends; removed from every clip except the last
HEAD = 0.25         # of the 0.5 s lead-in silence at the start of each narration, removed from every clip except the first
FADE_IN, FADE_OUT = 0.6, 0.9

def run(cmd): return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
def probe(f, entry): return run(["ffprobe", "-v", "error", "-show_entries", entry, "-of", "csv=p=0", str(f)]).strip()
ts = lambda t, sep=",": f"{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{int(t % 60):02d}{sep}{int(round((t % 1) * 1000)):03d}"

UP.mkdir(exist_ok=True)
clips = []
for cid, seg, title in ORDER:
    f = OUT / f"{cid}.mp4"
    assert f.exists(), f"missing {f}: render it first (npm run render:all in docs/video/anim)"
    d = float(probe(f, "format=duration")); clips.append(dict(cid=cid, seg=seg, title=title, file=f, dur=d))
for i, c in enumerate(clips):
    c["head"] = HEAD if i > 0 else 0.0
    c["keep"] = c["dur"] - c["head"] - (TRIM if i < len(clips) - 1 else 0)
    c["offset"] = sum(x["keep"] for x in clips[:i])
total = sum(c["keep"] for c in clips)

# ---- video: trim tails, normalise format, concatenate, fade in/out ----
parts, ins = [], []
for i, c in enumerate(clips):
    ins += ["-i", str(c["file"])]
    parts.append(f"[{i}:v]trim=start={c['head']:.3f}:duration={c['keep']:.3f},setpts=PTS-STARTPTS,fps=30,format=yuv420p[v{i}];"
                 f"[{i}:a]atrim=start={c['head']:.3f}:duration={c['keep']:.3f},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo[a{i}]")
cat = "".join(f"[v{i}][a{i}]" for i in range(len(clips))) + f"concat=n={len(clips)}:v=1:a=1[v][a]"
fade = (f"[v]fade=t=in:st=0:d={FADE_IN},fade=t=out:st={total - FADE_OUT:.3f}:d={FADE_OUT}[vf];"
        f"[a]afade=t=in:st=0:d={FADE_IN},afade=t=out:st={total - FADE_OUT:.3f}:d={FADE_OUT}[af]")
final = UP / "helpdesk-rag-video.mp4"
run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", ";".join(parts) + ";" + cat + ";" + fade, "-map", "[vf]", "-map", "[af]",
     "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
     "-movflags", "+faststart", str(final)])

# ---- captions (SRT) from the narration sentences ----
cues = []
for c in clips:
    for s in N[c["seg"]]["sentences"]:
        a, b = c["offset"] + s["start"] - c["head"], c["offset"] + s["end"] - c["head"]
        if s["start"] - c["head"] > c["keep"]: continue
        text, words = s["text"], s["text"].split(); chunks, cur = [], ""
        for w in words:                                   # split long sentences into cues of <= 76 characters (two caption lines)
            if len(cur) + len(w) + 1 > 76 and cur: chunks.append(cur); cur = w
            else: cur = (cur + " " + w).strip()
        chunks.append(cur); L = sum(len(x) for x in chunks); t = a
        for x in chunks:
            seg_len = (b - a) * len(x) / L; cues.append((t, t + seg_len, x)); t += seg_len
srt = []
for i, (a, b, x) in enumerate(cues, 1):
    srt.append(f"{i}\n{ts(a)} --> {ts(b)}\n" + "\n".join(textwrap.wrap(x, 44)) + "\n")
(UP / "captions.srt").write_text("\n".join(srt))

# ---- chapters + description ----
chapters = "\n".join(f"{int(c['offset'] // 60)}:{int(c['offset'] % 60):02d} {c['title']}" for c in clips)
(UP / "description.txt").write_text(f"""I built a help-desk RAG that runs entirely on a MacBook: Ollama (qwen3:8b + nomic-embed-text), Qdrant, a cross-encoder reranker,
Arize Phoenix tracing, and ollmcp. This is what worked, what didn't (HyDE, fine-tuning, a better embedder), and how I checked.
Code + full write-up: https://github.com/YOUR-USERNAME/helpdesk-rag

{chapters}

HOW TO READ THE NUMBERS
All results come from 19 in-scope and 7 out-of-scope test questions, and I tuned the pipeline on those same questions, so treat them as
illustrations, not benchmarks. The data is synthetic.

ABOUT THIS VIDEO
- Narration is a synthetic (AI-generated) voice, made with Kokoro-82M.
- The terminal segments (data twist, printer problem, "I don't know", tracing, ollmcp) are replays of real captured output, not live screen recordings.
  The Phoenix tracing screenshot and the ollmcp transcript are from real runs.
- Animations were built with Remotion.

CREDITS
Dataset: mindweave/help-desk-tickets on Hugging Face (synthetic, license CC-BY-NC-4.0, non-commercial).
Tools: Ollama, Qdrant, Arize Phoenix, sentence-transformers, FastMCP, ollmcp.

CODE AND NOTES
Repository: https://github.com/YOUR-USERNAME/helpdesk-rag
How to read the numbers: https://github.com/YOUR-USERNAME/helpdesk-rag/blob/main/docs/reading-the-numbers.md
Every command used in this video: https://github.com/YOUR-USERNAME/helpdesk-rag/blob/main/docs/commands.md
""")
(UP / "tags.txt").write_text("RAG, local LLM, Ollama, Qdrant, reranking, HyDE, fine-tuning, embeddings, MCP, ollmcp, AI engineering, evaluation\n")
shutil.copy(OUT / "thumbnail.png", UP / "thumbnail.png")
(UP / "README.txt").write_text("""UPLOAD CHECKLIST (nothing here has been uploaded; that is up to you)
1. Open description.txt and replace YOUR-USERNAME (4 places) with your GitHub username, after the repository exists and docs/ is pushed.
2. Upload helpdesk-rag-video.mp4. Start as PRIVATE or UNLISTED and watch it fully, with headphones, before making it public.
3. Thumbnail: thumbnail.png (1280x720). Captions: captions.srt (English). Tags: tags.txt.
4. Under "Altered content" answer YES: the narration is a synthetic voice.
5. Dataset license is CC-BY-NC-4.0 (non-commercial): check that fits your channel's monetization. Check Remotion's and Kokoro's licenses too.
6. Listen for mispronounced names (Qwen, Qdrant, nomic, HyDE, ollmcp). If any are wrong: edit PRONOUNCE in narration/build_narration.py,
   re-run it, re-render the clips, then re-run this script.
""")
print(f"wrote {final} ({total / 60:.2f} min), {len(cues)} caption cues, {len(clips)} chapters")
