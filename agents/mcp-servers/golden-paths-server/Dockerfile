# Multi-stage — dependencies resolved in `builder`, only the installed
# site-packages copied into the final image; uv and pip's build cache never
# ship in the final image.
FROM python:3.12-slim AS builder
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY agents/mcp-servers/golden-paths-server/requirements.lock.txt .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --target /deps -r requirements.lock.txt

FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*
COPY --from=builder /deps /usr/local/lib/python3.12/site-packages
RUN useradd --create-home --uid 1000 appuser
COPY --chown=appuser:appuser agents/mcp-servers/golden-paths-server/ ./agents/mcp-servers/golden-paths-server/
USER appuser
ENV PYTHONPATH=/app
EXPOSE 9002
# streamable-http transport — a bare GET/POST against /mcp without a valid
# MCP session legitimately returns 4xx, so probe TCP reachability rather than
# expecting a 200 (that would false-fail a healthy server).
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import socket; socket.create_connection(('localhost', 9002), timeout=3)" || exit 1
CMD ["python", "agents/mcp-servers/golden-paths-server/server.py"]
