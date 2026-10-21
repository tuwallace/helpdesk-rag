"""Pre-retrieval: rewrite the user's messy question, optionally HyDE."""
import ollama
from . import config as C
from .tracing import tracer

def _chat(prompt):
    r = ollama.chat(model=C.GEN_MODEL, think=False,
                    messages=[{"role": "user", "content": prompt}])
    return r["message"]["content"].strip()

def rewrite(q: str) -> str:
    with tracer.start_as_current_span("pre.rewrite") as s:
        s.set_attribute("openinference.span.kind", "LLM")
        out = _chat("Rewrite this IT help-desk question as a concise search query. "
                    f"Output only the query.\n\nQuestion: {q}")
        s.set_attribute("input.value", q); s.set_attribute("output.value", out)
        return out

def hyde(q: str) -> str:
    """Hypothetical Document Embeddings: embed a fake DOCUMENT instead of the question.
    Our corpus holds symptom summaries (no resolutions), so the fake document is a ticket summary."""
    with tracer.start_as_current_span("pre.hyde") as s:
        s.set_attribute("openinference.span.kind", "LLM")
        out = _chat("An employee wrote the message below. Write the one-sentence summary a help-desk agent "
                    "would put as the TITLE of the ticket, naming the product or system and the symptom. "
                    f"Output only the title.\n\nMessage: {q}")
        s.set_attribute("output.value", out)
        return out
