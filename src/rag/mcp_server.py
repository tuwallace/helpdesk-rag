"""Expose retrieval as an MCP tool so ollmcp (or any MCP client) lets a local LLM decide when to search.
Runs over stdio: NOTHING may be printed to stdout except MCP protocol messages."""
from fastmcp import FastMCP
from . import config as C
from .pipeline import retrieve_docs

mcp = FastMCP("helpdesk-rag")

@mcp.tool()
def search_tickets(query: str, top_n: int = 5) -> dict:
    """Search the history of IT help-desk tickets for problems similar to a described symptom.
    Use for any employee IT problem (email, VPN, MFA, printers, ERP, devices, access). Tickets hold symptoms, priority,
    status and time-to-resolve, but NO fix steps. Do not use for greetings, general knowledge or non-IT questions.
    query: describe the problem in plain words.
    Returns matches (one per distinct problem, with how many tickets share it) or an empty list if nothing matches."""
    # No optional filters on purpose: qwen3:8b filled `priority` with P1/P2/P3 on EVERY call, which hid the right tickets.
    docs = retrieve_docs(query, top_n=top_n, min_top_score=C.ANSWER_FLOOR)
    if not docs:
        return {"matches": [], "note": "No matching tickets found. Do not guess; tell the user to open a new ticket."}
    return {"matches": [{"ticket_id": d["id"], "problem": d["summary"], "tickets_with_this_problem": d.get("similar_count", 1),
                         "relevance": round(d.get("rerank_score", 0.0), 3), "details": d["text"][:600]} for d in docs]}

if __name__ == "__main__":
    mcp.run(show_banner=False)
