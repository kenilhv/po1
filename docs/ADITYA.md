# Aditya (Person 2) — TrueFoundry handoff from Kenil

## MCP server (register in TrueFoundry MCP Gateway)

```
URL:  http://<KENIL_IP>:8001/sse
Name: invoice-os-mcp
```

Kenil starts it:
```powershell
cd backend
.\.venv\Scripts\python -m invoice_mcp.server --port 8001
```

Full tool + agent map: `backend/docs/agents_mcp_registry.json`

## 6 agents — register in Agent Gateway

| Agent ID | Tier | Model | MCP tools | Your guardrails |
|----------|------|-------|-----------|-----------------|
| `invoice_parser` | L1 | cheap (llama-3.1-8b) | none | token budget |
| `po_matcher` | L1 | cheap | `lookup_purchase_order` | read-only |
| `duplicate_detector` | L1 | cheap | `check_duplicate_payment` | read-only |
| `fraud_signal` | L2 | expensive (llama-3.3-70b) | `check_vendor_fraud_signals` | read-only |
| `risk_scorer` | L2 | expensive | none | no tools |
| `approval_router` | L3 | cheap | `write_audit_log` | **BLOCK `submit_payment`** |

## Critical guardrail (demo moment)

**`submit_payment`** must be blocked at MCP Gateway unless human approval token present.

Router agent never pays — only routes to AUTO_APPROVED / PENDING_CFO / BLOCKED.

## LLM (later — not now)

Kenil uses Groq open models directly. When ready, swap `LLM_PROVIDER=truefoundry` in `.env`:

```
LLM_PROVIDER=truefoundry
OPENAI_API_BASE=<your gateway /v1>
OPENAI_API_KEY=<key>
```

## Test MCP reachable

```bash
curl http://<KENIL_IP>:8001/sse
```

## Architecture

```
PDF → invoice_parser → [po_matcher | duplicate_detector | fraud_signal] → risk_scorer → approval_router
                              ↓ all tools via MCP server :8001
                         TrueFoundry MCP Gateway (your guardrails)
```
