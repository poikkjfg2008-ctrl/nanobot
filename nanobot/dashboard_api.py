"""FastAPI dashboard for nanobot agent interaction and trace inspection."""

from __future__ import annotations

from contextlib import suppress

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from nanobot.agent.loop import AgentLoop
from nanobot.bus.queue import MessageBus
from nanobot.config.loader import load_config
from nanobot.observability.tool_trace import ToolTraceStore


class ChatRequest(BaseModel):
    message: str
    session_id: str = "dashboard:web"


def _make_provider(config):
    model = config.agents.defaults.model
    provider_name = config.get_provider_name(model)

    from nanobot.providers.registry import find_by_name

    spec = find_by_name(provider_name) if provider_name else None
    if not spec:
        raise RuntimeError("No provider matched. Configure providers.ollama or providers.vllm")

    p = config.get_provider(model)
    if not (p and p.api_base):
        raise RuntimeError(f"Missing api_base for provider '{spec.name}'.")

    if spec.name == "ollama":
        from nanobot.providers.ollama_provider import OllamaProvider

        return OllamaProvider(
            api_key=p.api_key if p else "ollama",
            api_base=config.get_api_base(model),
            default_model=model,
        )

    from nanobot.providers.litellm_provider import LiteLLMProvider

    return LiteLLMProvider(
        api_key=p.api_key if p else "dummy",
        api_base=config.get_api_base(model),
        default_model=model,
        extra_headers=p.extra_headers if p else None,
        provider_name=provider_name,
    )


def _build_agent_loop() -> AgentLoop:
    config = load_config()
    provider = _make_provider(config)
    bus = MessageBus()

    return AgentLoop(
        bus=bus,
        provider=provider,
        workspace=config.workspace_path,
        model=config.agents.defaults.model,
        temperature=config.agents.defaults.temperature,
        max_tokens=config.agents.defaults.max_tokens,
        max_iterations=config.agents.defaults.max_tool_iterations,
        memory_window=config.agents.defaults.memory_window,
        brave_api_key=config.tools.web.search.api_key or None,
        exec_config=config.tools.exec,
        restrict_to_workspace=config.tools.restrict_to_workspace,
        mcp_servers=config.tools.mcp_servers,
        channels_config=config.channels,
    )


def create_app(agent_loop: AgentLoop | None = None) -> FastAPI:
    loop = agent_loop or _build_agent_loop()
    trace_store = ToolTraceStore()

    app = FastAPI(title="Nanobot Agent Dashboard", version="0.1.0")

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        with suppress(Exception):
            await loop.close_mcp()

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/traces")
    async def traces(limit: int = 200) -> dict:
        return {"items": trace_store.tail(limit=max(1, min(limit, 1000)))}

    @app.post("/api/v1/chat")
    async def chat(request: ChatRequest) -> dict[str, str]:
        response = await loop.process_direct(request.message, session_key=request.session_id)
        return {"response": response}

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        return """
        <html>
          <head>
            <title>Nanobot Agent Dashboard</title>
            <style>
              body { font-family: sans-serif; max-width: 1180px; margin: 2rem auto; }
              .row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
              textarea, pre, input { width: 100%; box-sizing: border-box; }
              pre { background:#f3f3f3; padding:1rem; min-height: 280px; overflow:auto; }
              button { margin-right: 8px; }
            </style>
          </head>
          <body>
            <h2>Nanobot Agent Dashboard</h2>
            <div class='row'>
              <div>
                <h3>交互调试</h3>
                <label>Session ID</label>
                <input id='session_id' value='dashboard:web'/>
                <br/><br/>
                <textarea id='message' rows='8'>帮我总结一下今天要做的工作，并给出执行优先级。</textarea>
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
                const message = document.getElementById('message').value;
                const session_id = document.getElementById('session_id').value || 'dashboard:web';
                const res = await fetch('/api/v1/chat', {
                  method: 'POST',
                  headers: {'Content-Type': 'application/json'},
                  body: JSON.stringify({message, session_id})
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

    return app
