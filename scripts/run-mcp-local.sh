#!/usr/bin/env bash
# Quickly run a single MCP server locally to test via the terminal (stdio transport).
# Usage: bash scripts/run-mcp-local.sh mlops   (or: k8s | metrics)
set -e

SERVER=$1
if [ -z "$SERVER" ]; then
  echo "Usage: bash scripts/run-mcp-local.sh <mlops|k8s|metrics>"
  exit 1
fi

case "$SERVER" in
  mlops)   DIR="agents/mcp-servers/mlops-server" ;;
  k8s)     DIR="agents/mcp-servers/k8s-server" ;;
  metrics) DIR="agents/mcp-servers/metrics-server" ;;
  *) echo "Unrecognized: $SERVER (only mlops|k8s|metrics are supported)"; exit 1 ;;
esac

echo "=== Installing dependencies for $SERVER-server ==="
pip install -q -r "$DIR/requirements.txt"

echo "=== Running $SERVER-server (PYTHONPATH=. so adapters/ can be imported) ==="
PYTHONPATH=. python "$DIR/server.py"
