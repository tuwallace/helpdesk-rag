"""Audition voices: speak the same short, jargon-heavy passage in several voices -> samples/*.wav (gitignored).
Play one with:  afplay samples/kokoro_af_heart.wav"""
import pathlib, build_narration as b

TEXT = ("The fix was to stop retrieving tickets and start retrieving distinct problems. Qdrant can group by a field, "
        "so I asked for the top twenty different summaries. HyDE and fine-tuning did nothing, and ollmcp let a local "
        "Qwen model decide when to search. The chance that the right problem was in the pool jumped from seventy-four "
        "to ninety-five percent.")
out = pathlib.Path(__file__).parent / "samples"; out.mkdir(exist_ok=True)
b.speak(TEXT, "Daniel", 175, out / "say_Daniel.wav", "say")
for v in ["af_heart", "af_bella", "am_michael", "bm_george", "bf_emma"]:
    b.speak(TEXT, v, 175, out / f"kokoro_{v}.wav", "kokoro"); print("wrote", v)
for f in sorted(out.glob("*.wav")): b.normalize(f, -16.0)
print(sorted(p.name for p in out.glob("*.wav")))
