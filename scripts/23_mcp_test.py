"""Test the MCP server the way ollmcp uses it.
 Part A  protocol: start the server over stdio, list tools, call search_tickets directly.
 Part B  tool selection + answers: qwen3:8b sees the tool schema, decides whether to call it, gets the result and answers.
         Run twice: with NO system prompt (ollmcp's default) and WITH one, because tool use depends heavily on it.
Expected behaviour: IT-problem questions -> call the tool; chit-chat / general knowledge -> do not;
out-of-scope questions -> may call, but the final answer must say there is no match, not invent one."""
import asyncio, json, os, re, sys, time
import ollama
from fastmcp import Client

MODEL = "qwen3:8b"
THINK = os.getenv("THINK") == "1"          # ollmcp enables qwen3 thinking by default; THINK=1 mimics it
MODES = os.getenv("MODES", "both")         # "nosys" = only the no-system-prompt run (ollmcp default)
gold = [json.loads(l) for l in open("eval/golden.jsonl")]
INSCOPE = [g for g in gold if g["tier"] != "out_of_scope"]
OOS = [g for g in gold if g["tier"] == "out_of_scope"]
NONSEARCH = ["hi there", "what is 17 times 23?", "write a two-line poem about servers", "thanks, that's all",
             "explain in one sentence what a VPN is", "what tools do you have available?"]
SYSTEM = ("You are an IT help-desk assistant. When an employee describes an IT problem, use the search_tickets tool to find "
          "similar past tickets, then answer ONLY from the results, citing ticket ids. The tickets contain symptoms, not fixes. "
          "If the tool finds no matches, say so and suggest opening a new ticket. Do not use the tool for greetings or general questions.")
REFUSAL = re.compile(r"unable to find|does not match|not (related|match)|cannot assist|can't assist|don't have access|no (matching|relevant|similar)|not find|couldn't find|could not find|open a new ticket|no tickets|do(es)? not (contain|include|mention)", re.I)

def tool_schema(t):
    return {"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.inputSchema}}

async def run_prompt(client, tools, text, system):
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": text}]
    r = ollama.chat(model=MODEL, messages=msgs, tools=tools, think=THINK)
    calls = r["message"].get("tool_calls") or []
    result_ids, args = [], None
    if calls:
        msgs.append(r["message"])
        for c in calls:
            args = dict(c["function"]["arguments"])
            res = await client.call_tool(c["function"]["name"], args)
            data = res.data if res.data is not None else json.loads(res.content[0].text)
            result_ids += [m["ticket_id"] for m in data.get("matches", [])]
            msgs.append({"role": "tool", "tool_name": c["function"]["name"], "content": json.dumps(data)})
        r = ollama.chat(model=MODEL, messages=msgs, tools=tools, think=THINK)
    return bool(calls), args, result_ids, r["message"]["content"]

async def main():
    client = Client(json.load(open("mcp.json")))
    async with client:
        t0 = time.time(); tl = await client.list_tools()
        print(f"PART A  tools: {[t.name for t in tl]}  (server up in {time.time() - t0:.1f}s)")
        t = tl[0]
        for q in ("outlook keeps asking me to sign in on my macbook", "what time does the cafeteria open on fridays"):
            res = await client.call_tool(t.name, {"query": q}); data = res.data
            print(f"  direct call {q[:45]!r}: {len(data['matches'])} matches", [m['problem'][:40] for m in data['matches']][:2], data.get("note", ""))
        tools = [tool_schema(x) for x in tl]
        runs = (("NO system prompt (ollmcp default)", None), ("WITH system prompt", SYSTEM))
        for label, system in (runs[:1] if MODES == "nosys" else runs):
            label += f"  [thinking={'on' if THINK else 'off'}]"
            print(f"\nPART B  {label}")
            rows = {"in": [], "oos": [], "non": []}
            for g in INSCOPE:
                c, a, ids, ans = await run_prompt(client, tools, g["question"], system)
                rows["in"].append((g, c, a, ids, ans))
            for g in OOS:
                rows["oos"].append((g,) + await run_prompt(client, tools, g["question"], system))
            for q in NONSEARCH:
                rows["non"].append(({"question": q},) + await run_prompt(client, tools, q, system))
            called_in = sum(r[1] for r in rows["in"]); hit = sum(bool(set(r[3]) & set(r[0]["relevant_ids"])) for r in rows["in"])
            print(f"  in-scope:  tool called {called_in}/{len(rows['in'])} | target ticket in tool result {hit}/{len(rows['in'])}")
            print(f"  non-search prompts: tool called {sum(r[1] for r in rows['non'])}/{len(rows['non'])}  (want 0)")
            oos_ref = sum(bool(REFUSAL.search(r[4])) for r in rows["oos"])
            print(f"  out-of-scope: tool called {sum(r[1] for r in rows['oos'])}/{len(rows['oos'])} | final answer says no match {oos_ref}/{len(rows['oos'])}")
            for name, rs in (("in-scope NOT calling the tool", [r for r in rows['in'] if not r[1]]),
                             ("non-search that CALLED the tool", [r for r in rows['non'] if r[1]]),
                             ("out-of-scope answered WITHOUT saying no match", [r for r in rows['oos'] if not REFUSAL.search(r[4])])):
                if rs:
                    print(f"  -- {name}:")
                    for r in rs: print(f"       {r[0]['question'][:60]!r} -> {r[4][:110]!r}")
            args = [r[2] for r in rows["in"] if r[2]]
            if args: print("  sample tool arguments:", args[:3])

asyncio.run(main())
