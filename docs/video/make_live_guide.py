#!/usr/bin/env python3
"""Writes docs/video/live-recording-guide.md. Cue times come from anim/src/narration.json (so they match the audio).
Re-run after changing the voice or the narration:   python3 docs/video/make_live_guide.py
If a segment's sentence count changes, the ACTIONS lists below must be updated (the script stops and tells you)."""
import json, pathlib

HERE = pathlib.Path(__file__).resolve().parent
N = json.loads((HERE / "anim/src/narration.json").read_text())
mmss = lambda t: f"{int(t // 60)}:{t % 60:04.1f}"


def cue(seg, actions):
    sents = N[seg]["sentences"]
    assert len(sents) == len(actions), f"{seg}: narration now has {len(sents)} sentences but the guide lists {len(actions)} actions; update ACTIONS"
    rows = ["| Time | Narration says | You do (on screen) |", "|---|---|---|"]
    for s, a in zip(sents, actions):
        rows.append(f"| {mmss(s['start'])} | {s['text'].replace('|', '/')} | {a} |")
    return "\n".join(rows)


dur = lambda seg: N[seg]["duration"]
ANIM = {"seg1": "Hook.mp4", "seg2": "Pipeline.mp4", "seg5": "Recall.mp4", "seg6": "FailedIdeas.mp4", "seg7": "ReadingNumbers.mp4", "seg11": "Takeaways.mp4"}
ORDER = [("1", "Hook", "seg1", "ANIM"), ("2", "What I built", "seg2", "ANIM"), ("3", "The data twist", "seg3", "LIVE"), ("4", 'The "printer" problem', "seg4", "LIVE"),
         ("5", "The fix", "seg5", "ANIM"), ("6", "What didn't work", "seg6", "ANIM"), ("7", "Evaluating honestly", "seg7", "ANIM"),
         ("8", "Knowing when to say I don't know", "seg8", "LIVE"), ("9", "Tracing", "seg9", "LIVE"), ("10", "ollmcp", "seg10", "LIVE"), ("11", "Takeaways", "seg11", "ANIM")]
total = sum(dur(s) + (2 if t == "ANIM" else 0) for _, _, s, t in ORDER)
order_rows = "\n".join(
    f"| {n} | {title} | {t} | {('anim/out/' + ANIM[s]) if t == 'ANIM' else 'your recording (' + s + '.mov)'} | "
    f"{('(embedded)' if t == 'ANIM' else 'anim/public/narration/' + s + '.wav')} | {dur(s) + (2 if t == 'ANIM' else 0):.0f} s |" for n, title, s, t in ORDER)

A3 = ["Terminal is open at the project folder with the command already typed (not run). Prompt is short.",
      "Press **Enter**. The table prints in about a second. Pause so \"tickets 1,000\" and \"distinct problems 56\" are readable.",
      "Hold on the \"tickets per problem 10 to 28\" line.",
      "Hold on the \"comments 2,000 / distinct comment sentences 24\" lines and the \"attached to tickets at random\" heading.",
      "Hold on the three most repeated comments (each is repeated about a hundred times).",
      "Hold (nothing new on screen).", "Hold, then end the clip."]
A4 = ["Command typed, not run. Press **Enter** as the first words start. Output prints in about 1 to 2 seconds.",
      "Scroll or hold so all three blocks (dense, bm25, hybrid) are visible. Every line reads \"Label printer feeds blank stock\".",
      "Hold on the line \"distinct problems in these 15 results: 1\", then the list of three printer problems at the bottom.",
      "Hold on the \"23 tickets\" line (the cluster that filled the list).", "Hold.", "Hold, end of clip."]
A8 = ["REPL is running and shows `question>` (started and warmed up before you press record). Nothing typed yet.",
      "Optional insert: cut to a second terminal showing `grep -n \"ANSWER_FLOOR\" src/rag/config.py` (shows `ANSWER_FLOOR = 0.05`).",
      "Start **typing or pasting** the cafeteria question (line 1 in `seg8_questions.txt`). Do not press Enter yet.",
      "Press **Enter**. The no-match message appears with a timer like `[0.4s]`, `sources=[]`, `refused=below_floor`.",
      "Hold on that result.",
      "Paste the **email-app question** (line 2): it is valid, and the floor still refuses it (`[0.3s]`, `refused=below_floor`). This is the cost.",
      "Hold on the refusal. Optionally run the Outlook question (line 3) to show a normal answer in about 2 to 3 seconds.",
      "Hold (nothing new; this is about a prompt change, not a demo).", "Hold, end of clip."]
A9 = ["Terminal with `python scripts/18_trace_demo.py` typed. Press **Enter** at the very start.",
      "The three questions run (about 13 to 20 s of real time; speed up or trim the wait in editing). Then the table of stages and percentages appears.",
      "Hold on the `generate` and `pre.rewrite` lines in a warm trace (generate roughly 70 to 80%).",
      "Point to the **first** trace in the list. It was run cold, so it is the slowest (about 7 s in testing).",
      "Switch to the browser: Phoenix at http://localhost:6006, project **helpdesk-rag**, Traces tab, click the newest trace.",
      "Hold on the span tree (rag.answer with rewrite, retrieve, rerank, generate and their durations).", "Hold, end of clip."]
A10 = ["`ollmcp` is already running. The banner shows `helpdesk-rag.search_tickets` and `1/1 tools enabled`.",
       "Hold on the Available Tools panel.",
       "Type prompt 1 (IT problem) and let the tool call show on screen: a call to `helpdesk-rag.search_tickets` with only a `query` argument, then the answer. Then prompt 2 (`17 times 23`): answered directly, **no tool call**. Real thinking-mode answers can take 10 to 40 s each; speed up or jump-cut the waits.",
       "Hold on the tool call from prompt 1 if you can still see it, or on the `no tool call` answer.",
       "Cut to a second terminal: `grep -n -B1 -A1 \"No optional filters\" src/rag/mcp_server.py` (the comment about `priority`).",
       "Hold on that comment (the explanation of the bug).",
       "Cut to `sed -n 9,17p src/rag/mcp_server.py` (the whole tool definition: `query` and `top_n` only). Hold, end of clip."]

OUT = f"""# Live recording guide: segments 3, 4, 8, 9 and 10

Generated by `docs/video/make_live_guide.py` from the narration timings in `anim/src/narration.json`. Re-run it after
changing the narration. The numbers quoted here are from test runs on this machine and will differ a little when you record.

> **Status:** the finished video in `docs/video/upload/` does **not** need these recordings. Its five live segments are
> terminal **replays** of real captured output (clearly labelled on screen), built by `docs/video/anim/src/LiveSegs.tsx`.
> Use this guide only if you want to replace a replay with your own real screen recording; then swap that segment's clip in
> `finalize.py` or in iMovie.

## 1. How the finished video fits together

The six animated clips are already rendered (narration is inside them). For the five live segments you record the
**screen only, silent**, and lay the generated narration audio under each recording in iMovie. The cue tables below say when
each thing should be on screen so the picture matches the voice.

| # | Segment | Type | Picture from | Narration from | Length |
|---|---|---|---|---|---|
{order_rows}

Total about **{total / 60:.1f} minutes** (not the 12 minutes first estimated: the script has about 1,000 spoken words). Audio files
are in `docs/video/anim/public/narration/`; animated clips are in `docs/video/anim/out/`.

## 2. One-time setup before you record anything

Run each line in a terminal. Work from the project folder.

```bash
cd path/to/helpdesk-rag && source .venv/bin/activate
docker compose ps                      # qdrant and phoenix must both say Up (docker compose up -d if not)
ollama list | grep qwen3:8b            # the model must be present
caffeinate -dis &                      # keeps the Mac awake while you record (see the note on stalls below)
```

Then:

1. **Notifications off** (Do Not Disturb). Close chat, mail and anything showing private content.
2. **Terminal**: font size 20 pt or larger, a window of about 1280 x 720, dark background. Shorten the prompt so it hides your user name
   and folders: `PROMPT='$ '` then `clear`.
3. **Browser** (segment 9 only): open http://localhost:6006/projects and confirm a project called `helpdesk-rag` exists.
4. **Recording**: press `Cmd+Shift+5`, choose *Record Selected Portion*, drag a 16:9 area around the terminal, open *Options* and set
   Microphone to **None**. Save each take as `segN.mov` in a `recordings/` folder.
5. **Warm everything once**: run `python scripts/19_demo_repl.py`, wait for `ready`, ask one question, then press Enter on an empty line to quit.
   (A fresh Python process takes about 8 seconds to start because it imports libraries and loads the reranker. The recordings below avoid showing that.)

**Record in short takes**, one segment per file. If anything looks wrong, stop and retake that segment only.

## 3. Segment 3: the data twist ({mmss(dur('seg3'))})

**Viewer should see:** a small table: 1,000 tickets, 56 distinct problems, 10 to 28 tickets per problem, 2,000 comments but only 24 distinct sentences.

Type this before pressing record (so you only press Enter on camera):

```bash
python docs/video/demo/seg3_data.py
```

{cue('seg3', A3)}

Expected output (recorded on this machine):

```
  tickets                            1,000
  distinct problems (summaries)         56
  tickets per problem             10 to 28
  comments                           2,000
  distinct comment sentences            24

  most repeated comments (attached to tickets at random):
    102x  Found stale token in local credential manager.
     99x  Issue now limited to users on macOS Sonoma.
     97x  Closing after three business days without reply.
```

**Edit note:** the output appears in about a second but the narration runs about {dur('seg3'):.0f} s. After the table is on screen, simply hold the last frame
(iMovie: *Modify > Add Freeze Frame*) until the audio ends.

## 4. Segment 4: the "printer" problem ({mmss(dur('seg4'))})

**Viewer should see:** three blocks of results (dense, bm25, hybrid), every line the same problem, then the list of three printer problems that really exist.

```bash
python docs/video/demo/seg4_printer.py
```

{cue('seg4', A4)}

Expected: all 15 result lines read `Label printer feeds blank stock after maintenance.`; then `distinct problems in these 15 results: 1`; then
`23 tickets Label printer feeds blank stock...`, `12 tickets Printer on dock 4 is stuck in offline state.`, `11 tickets New Zebra printer not visible to shipping station.`
The ticket ids in the lines (191, 128, ...) can differ from yours; the repetition is what matters.

**Edit note:** the output is longer than one screen at a large font. Either make the window taller, or scroll slowly during the second sentence.

## 5. Segment 8: knowing when to say "I don't know" ({mmss(dur('seg8'))})

**Viewer should see:** a question the system cannot answer being refused in well under a second; then a *valid* question that the floor also refuses (the cost); optionally a normal answer.

Start the demo REPL **before** recording, and wait until it prints `ready. Type a question.`:

```bash
python scripts/19_demo_repl.py
```

Questions to paste, in order (also in `docs/video/demo/seg8_questions.txt`).

{cue('seg8', A8)}

What you should see (real values from test runs; yours will differ slightly):

| Question | Result | Time |
|---|---|---|
| cafeteria | `I couldn't find a matching ticket...` `sources=[]` `refused=below_floor` | 0.3 to 0.6 s |
| email-app question | same refusal (refused 5 of 5 times in testing) | 0.3 to 0.5 s |
| outlok question | an answer citing ticket 794 (`sources=[794]`) | 2.0 to 2.9 s |

**Honesty checks for this segment**

- The narration says the refusal path takes "under half a second". That holds **only in this warm REPL**. A fresh `python -m rag.pipeline` call takes 8 to 14 s mostly in start-up. Use the REPL, as above.
- Do not use the spam question (`A bunch of unwanted messages flooded the team's help center...`): it was refused only about one time in three. The two questions listed above refused every time in testing.
- The answers sometimes state how a problem was "resolved". Those phrases come from canned comments attached to tickets at random, so they are **not** reliable fixes. If one appears on screen, do not describe it as the fix.

## 6. Segment 9: tracing ({mmss(dur('seg9'))})

**Viewer should see:** the stage-by-stage latency table, with the generator taking most of the time, then the same trace as a tree in Phoenix.

To get a visible **cold start** in the first trace, unload the models right before recording:

```bash
ollama stop qwen3:8b; ollama stop nomic-embed-text
python scripts/18_trace_demo.py        # type this, do not run it until the cue
```

{cue('seg9', A9)}

Numbers from three test runs today (they vary): the cold first trace took 6.7 s; warm traces took 1.7 to 3.1 s; `generate` was 69 to 80% of a warm trace,
`pre.rewrite` 17 to 24%, retrieval plus rerank about 6%. The narration deliberately says "a few seconds" and "roughly three quarters" so it stays true when yours differ.
In Phoenix: Projects > **helpdesk-rag** > Traces > click the newest `rag.answer`.

## 7. Segment 10: ollmcp ({mmss(dur('seg10'))})

**Viewer should see:** the real `ollmcp` client with your tool; a tool call for an IT question; no tool call for arithmetic; and the one-line comment explaining the `priority` bug.

Prepare **before** recording:

```bash
ollmcp -j mcp.json -m qwen3:8b
```

Inside ollmcp:

1. Check the banner: it must list **only** `helpdesk-rag.search_tickets` (`1/1 tools enabled`). If it lists other servers, stop and use only `-j mcp.json`.
2. `/mc` (model configuration): set the **system prompt** to the text in `docs/video/demo/ollmcp_system_prompt.txt` (paste it). Without a system prompt the model sometimes answers non-IT questions from general knowledge.
3. `/st` hides the long visible "thinking" text (it is on by default and fills the screen). `/ste` should leave tool execution **shown** (it is by default).
4. If ollmcp asks you to confirm each tool call (human-in-the-loop), answer `y`; `/hil` toggles that. I could not drive the interactive menus myself, so check these screens once before recording.

Prompts to type (also in `docs/video/demo/seg10_prompts.txt`): the Outlook problem, then `what is 17 times 23?`, optionally the vacation-days question.

{cue('seg10', A10)}

What testing showed with the same tool (harness, not the ollmcp window): the tool was called for 19 of 19 IT questions and 0 of 6 chit-chat prompts; the right ticket was in the result for 16 of 19;
for unanswerable questions the final answer said there was no match in 6 of 7 (no system prompt) and 7 of 7 (with one). Thinking mode did not change this.

## 8. Putting it together in iMovie

1. Create a project (16:9, 1080p, 30 fps). Import the six MP4s in `docs/video/anim/out/`, your five recordings, and the five narration WAVs.
2. Place everything in the order of the table in section 1.
3. For each live segment: drop the recording on the timeline, **detach/mute its audio**, then drag `segN.wav` underneath and align its start with the start of the recording.
4. Use the cue table to line things up. If a recording is shorter than the audio, add a freeze frame on the last frame; if it is longer (waiting for slow answers), speed up that part (*Modify > Speed*) or trim it.
5. Between clips, use a plain cut or a short cross-dissolve. Keep the same loudness: every narration file is about -16 LUFS.
6. Export 1080p, high quality, and watch the whole thing once with headphones before uploading.

## 9. Things that can go wrong

- **A step hangs for minutes.** Twice during testing a command ran for many minutes at near-zero CPU (a rerank call took 907 s once, and a one-minute job timed out at 400 s once) and I could not reproduce it afterwards.
  Possible causes I could not confirm: the Mac idling or sleeping, or a stalled network check. Mitigations already in place: the reranker now loads from the local cache first, and the commands above use `caffeinate`.
  If a step shows no progress for about 45 seconds, press `Ctrl+C`, and retake that segment. `DEMO_WATCHDOG=1 python scripts/19_demo_repl.py` prints a stack trace if anything stalls for 45 s, which would help diagnose it.
- **Docker containers stopped.** Symptoms: "connection refused" on port 6333 or 6006. Run `docker compose up -d`. They now restart automatically after a Docker restart.
- **Numbers differ from the narration.** Timings and the exact wording of answers vary every run (the query rewrite and the answers come from an LLM). The narration is worded to stay true; if something on screen contradicts it, re-record or edit the narration (`build_narration.py --only N`) and re-run this generator.
- **Privacy.** Recordings show your terminal. Hide your user name and folders (short prompt), and do not show any config files from `~/.config`.
- **Disclosure.** The narration is synthetic. YouTube may require its "altered or synthetic content" label when you upload.
"""
(HERE / "live-recording-guide.md").write_text(OUT)
print(f"wrote {HERE / 'live-recording-guide.md'}  ({len(OUT.splitlines())} lines, total runtime {total / 60:.1f} min)")
