# orchestration-api

FastAPI BFF — receives requests from the Portal UI (Backstage), acting as an
MCP Client: calls Claude, and Claude calls tools through the MCP servers in
`agents/mcp-servers/`.

## Run locally

```bash
cd services/orchestration-api
pip install -r requirements.txt
uvicorn main:app --reload
```

Open `http://localhost:8000/healthz` to check it's up. Chat endpoint: `POST /chat`.

## Structure

- `main.py` — creates the app, mounts routers
- `routers/` — routes that handle requests from the UI (currently `chat.py`)
- `core/` — config, shared clients (Claude client, MCP client will be added once implemented)
