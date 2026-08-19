FROM python:3.14-slim
WORKDIR /app
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv
COPY agents/mcp-servers/metrics-server/requirements.lock.txt .
RUN uv pip install --system --no-cache -r requirements.lock.txt
COPY agents/mcp-servers/metrics-server/ ./agents/mcp-servers/metrics-server/
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser
# stdio-transport tool, no HTTP port to probe — verify our code + deps still
# import cleanly inside the running container instead.
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "from mcp.server.mcpserver import MCPServer" || exit 1
CMD ["python", "agents/mcp-servers/metrics-server/server.py"]
