# navigator-orchestrator

MCP server that orchestrates multi-tool workflows against [rhoai-mcp](https://github.com/opendatahub-io/rhoai-mcp). Uses LangGraph for workflow execution and state management, connecting to rhoai-mcp over MCP protocol as a client.

The orchestrator serves as the single MCP entry point for consumers (Lightspeed Core Stack, Claude Code, etc.). It exposes high-level workflow tools for multi-step operations and proxies all other rhoai-mcp tools through transparently.

## Architecture

```
Consumer ──MCP──▶ navigator-orchestrator (port 8001) ──MCP──▶ rhoai-mcp (port 8000)
```

Three layers:

1. **MCP Client** — connects to rhoai-mcp, calls tools, returns typed results
2. **LangGraph Engine** — executes workflow graphs with interrupt/resume for wizard-style user interaction
3. **Workflow Registry** — pluggable collection of workflow definitions, each a LangGraph `StateGraph`

## Tools

The orchestrator exposes two kinds of tools:

**Workflow tools** — multi-step operations with interrupt points for user input:

| Tool | Description |
|------|-------------|
| `start_model_recommendation` | Begin model recommendation workflow |
| `resume_workflow` | Continue a paused workflow with user input |
| `cancel_workflow` | Cancel a running workflow |
| `list_workflows` | List available workflows |

**Passthrough tools** — all rhoai-mcp tools not covered by a workflow, forwarded unchanged.

### Interrupt Protocol

When a workflow needs user input, the tool returns `status: "awaiting_input"` with structured data describing what's needed:

```json
{
    "status": "awaiting_input",
    "thread_id": "abc-123",
    "step": "review_specs",
    "prompt": "Review the technical specs for your use case.",
    "data": {"latency_p99": "100ms", "max_batch_size": 32},
    "editable_fields": ["latency_p99", "max_batch_size"]
}
```

The consumer calls `resume_workflow(thread_id, user_input)` to continue. This repeats until the workflow returns `status: "complete"`.

## Running

```bash
uv sync
uv run python -m navigator_orchestrator
```

Requires a running rhoai-mcp instance.

## Deployment

### Container

Build and run with Podman (or Docker):

```bash
make build
make run
```

Override defaults:

```bash
make run PORT=9001 RHOAI_MCP_URL=http://rhoai-mcp:8000/mcp
```

### Kubernetes / Kind

```bash
kustomize build deploy/kustomize/overlays/kind | kubectl apply -f -
```

The Kind overlay uses `imagePullPolicy: Never` for locally-built images and exposes the service as `NodePort`.

### OpenShift

```bash
kustomize build deploy/kustomize/overlays/openshift | oc apply -f -
```

The OpenShift overlay uses `ghcr.io/amito/navigator-orchestrator:latest`, creates a TLS-terminated Route, and removes explicit security context IDs to work with OpenShift's SCC.

## Configuration

Environment variables (prefix `ORCHESTRATOR_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `ORCHESTRATOR_RHOAI_MCP_URL` | `http://localhost:8000/mcp` | rhoai-mcp endpoint |
| `ORCHESTRATOR_HOST` | `0.0.0.0` | Bind address |
| `ORCHESTRATOR_PORT` | `8001` | Listen port |

## Development

```bash
uv sync --dev
uv run pytest -q
uv run ruff check .
uv run ruff format .
```

## Project Structure

```
src/navigator_orchestrator/
├── __main__.py              # Entry point, composition root
├── config.py                # Pydantic settings
├── server.py                # MCP server tool routing
├── mcp_client.py            # MCP client wrapper (to rhoai-mcp)
├── auth.py                  # Token passthrough utilities
├── passthrough.py           # Tool discovery and passthrough
└── workflows/
    ├── types.py             # WorkflowResult, WorkflowInfo
    ├── registry.py          # WorkflowRegistry
    ├── engine.py            # WorkflowEngine (interrupt/resume)
    └── model_recommendation.py  # Model recommendation workflow
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
