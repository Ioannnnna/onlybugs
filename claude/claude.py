import os, json, requests
from dotenv import load_dotenv
import boto3
from botocore.config import Config

# ── 1. credentials ───────────────────────────────────────────────────
load_dotenv()
TOKEN  = os.environ["AWS_BEARER_TOKEN_BEDROCK"]
REGION = os.getenv("AWS_DEFAULT_REGION", "us-west-2")

client = boto3.client(
    "bedrock-runtime",
    region_name=REGION,
    aws_session_token=TOKEN,
    config=Config(signature_version="bearer"),
)
MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"

# ── 2. MCP tool schema ───────────────────────────────────────────────
TOOLS = [{
    "name": "pg_query",
    "description": "Run SQL on Postgres via MCP gateway",
    "input_schema": {
        "type": "object",
        "properties": {
            "query":     {"type": "string", "description": "SQL query to execute"},
            "connector": {"type": "string", "enum": ["local_pg"],
                          "description": "DB connector name (default local_pg)"}
        },
        "required": ["query"]
    }
}]

SYSTEM_MSG = (
    "You have access to the pg_query tool. "
    "Whenever a user question requires numbers or facts from the database, answer correctly based on you knowledge and db information."
)

# ── 3. Bedrock helper ────────────────────────────────────────────────
def invoke(messages, tool_results=None, max_tokens=400, temperature=0.3):
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "system": SYSTEM_MSG,
        "messages": messages,
        "tools": TOOLS,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if tool_results:
        body["tool_results"] = tool_results

    resp = client.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json"
    )
    return json.loads(resp["body"].read())

# print("▶ Ask anything (type 'quit' to exit)")
while True:
    try:
        q = input("\nYou: ").strip()
        if q.lower() in {"quit", "exit"}:
            break

        try:
            t = float(input("temperature 0-1 [0.3]: ") or "0.3")
        except ValueError:
            t = 0.3

        # ── build user message list ───────────────────────────────
        messages = [{
            "role": "user",
            "content": [{"type": "text", "text": q}]
        }]

        first = invoke(messages, temperature=t)

        # look for tool_use element
        tool_elem = next(
            (p for p in first["content"] if p.get("type") == "tool_use"),
            None
        )

        if tool_elem:
            sql       = tool_elem["input"]["query"]
            connector = tool_elem["input"].get("connector", "local_pg")
            print("SQL →", sql)

            rows = requests.post(
                "http://localhost:8000/query",
                json={"connector": connector, "query": sql},
                timeout=10
            ).json()
            print("Rows returned:", rows)        # comment out later

            tool_results = [{
                "tool_call_id": tool_elem["id"],
                "content": json.dumps(rows)
            }]

            # only pass valid assistant message onward
            assistant_msg = {
                "role": "assistant",
                "content": first["content"]
            }

            follow = invoke(
                messages + [assistant_msg],
                tool_results=tool_results,
                temperature=t
            )

            answer = follow["content"][0]["text"]

        else:
            # plain answer
            answer = next(
                (p["text"] for p in first["content"] if p["type"] == "text"),
                "<no text>"
            )

        print("\nClaude:", answer)

    except Exception as exc:
        # show any error and continue the loop
        print("\n⚠️  Error:", exc)
print("\nClaude:", answer)
