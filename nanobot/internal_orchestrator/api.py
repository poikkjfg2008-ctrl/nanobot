"""FastAPI entrypoint for the internal orchestration layer."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from nanobot.internal_orchestrator.agent import InternalToolAgent


class ChatRequest(BaseModel):
    query: str
    session_id: str = "default"


def create_app(agent: InternalToolAgent | None = None) -> FastAPI:
    orchestrator = agent or InternalToolAgent.from_defaults()
    app = FastAPI(title="Nanobot Internal Orchestrator", version="0.1.0")

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        return """
        <html>
          <head><title>Internal Orchestrator</title></head>
          <body style='font-family: sans-serif; max-width: 900px; margin: 2rem auto;'>
            <h2>Internal Tool Orchestrator</h2>
            <textarea id='query' rows='6' style='width:100%;'>帮我看下 ecommerce 今天销售额，并给出下周预测。</textarea>
            <br/><br/>
            <button onclick='send()'>提交</button>
            <pre id='output' style='background:#f3f3f3;padding:1rem;margin-top:1rem;'></pre>
            <script>
              async function send() {
                const query = document.getElementById('query').value;
                const res = await fetch('/api/v1/orchestrate', {
                  method: 'POST',
                  headers: {'Content-Type': 'application/json'},
                  body: JSON.stringify({query, session_id:'demo'})
                });
                document.getElementById('output').innerText = JSON.stringify(await res.json(), null, 2);
              }
            </script>
          </body>
        </html>
        """

    @app.post("/api/v1/orchestrate")
    async def orchestrate(request: ChatRequest) -> dict:
        return await orchestrator.run(query=request.query, session_id=request.session_id)

    return app
