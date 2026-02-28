"""FastAPI entrypoint for the internal orchestration layer."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from nanobot.internal_orchestrator.agent import InternalToolAgent
from nanobot.observability.tool_trace import ToolTraceStore


class ChatRequest(BaseModel):
    query: str
    session_id: str = "default"


def create_app(agent: InternalToolAgent | None = None) -> FastAPI:
    orchestrator = agent or InternalToolAgent.from_defaults()
    trace_store = ToolTraceStore()
    app = FastAPI(title="Nanobot Internal Orchestrator", version="0.1.0")

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/traces")
    async def traces(limit: int = 200) -> dict:
        return {"items": trace_store.tail(limit=max(1, min(limit, 1000)))}

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        return """
        <html>
          <head>
            <title>Internal Orchestrator Dashboard</title>
            <style>
              body { font-family: sans-serif; max-width: 1100px; margin: 2rem auto; }
              .row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
              textarea, pre { width: 100%; box-sizing: border-box; }
              pre { background:#f3f3f3;padding:1rem; min-height: 260px; overflow:auto; }
              button { margin-right: 8px; }
            </style>
          </head>
          <body>
            <h2>Nanobot Intranet Dashboard</h2>
            <div class='row'>
              <div>
                <h3>Orchestrator 调试</h3>
                <textarea id='query' rows='8'>帮我看下 ecommerce 今天销售额，并给出下周预测。</textarea>
                <br/><br/>
                <button onclick='send()'>提交</button>
                <pre id='output'></pre>
              </div>
              <div>
                <h3>工具调用链路 (tool_trace.jsonl)</h3>
                <button onclick='refreshTrace()'>刷新</button>
                <pre id='trace'></pre>
              </div>
            </div>
            <script>
              async function send() {
                const query = document.getElementById('query').value;
                const res = await fetch('/api/v1/orchestrate', {
                  method: 'POST',
                  headers: {'Content-Type': 'application/json'},
                  body: JSON.stringify({query, session_id:'demo'})
                });
                document.getElementById('output').innerText = JSON.stringify(await res.json(), null, 2);
                refreshTrace();
              }

              async function refreshTrace() {
                const res = await fetch('/api/v1/traces?limit=200');
                const body = await res.json();
                document.getElementById('trace').innerText = JSON.stringify(body, null, 2);
              }

              refreshTrace();
            </script>
          </body>
        </html>
        """

    @app.post("/api/v1/orchestrate")
    async def orchestrate(request: ChatRequest) -> dict:
        return await orchestrator.run(query=request.query, session_id=request.session_id)

    return app
