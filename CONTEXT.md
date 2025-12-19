# aiTriage - Project Context

This document provides comprehensive context about the aiTriage project for future development sessions.

## Project Overview

**aiTriage** is a portfolio project that ingests alerts from various observability tools (Prometheus, Datadog, BetterStack), correlates them based on saturation, errors, and latency signals, and generates concise "situation reports" with suggested runbook steps.

### Key Design Principle

> **High saturation alone is NOT necessarily an incident** if latency and errors stay normal. This is treated as a "capacity warning" rather than a major incident.

### Deployment

**Fly.io** - Single container, auto-scaling with GitHub integration for automatic deployments

## Architecture

### Tech Stack

- **Backend**: Python FastAPI (Python 3.x)
  - Uses `uv` for virtual environment and package management
  - SQLite3 for report caching and rate limiting (built into Python)
  - LLM integration via OpenAI (ChatGPT) and Anthropic (Claude) APIs
  
- **Frontend**: Astro SPA with React + Tailwind CSS + Shadcn/UI
  - Dark theme with yellow as primary color
  - Built with Bun
  - Served as static files by FastAPI backend in production

- **CLI**: Ink-based TUI (k9s-like interface)
  - Built with Bun/TypeScript
  - Interactive terminal UI for incident management

- **Deployment**: **Fly.io** - Single-container deployment via Dockerfile, multi-stage build, SQLite databases in persistent volumes. Configured with GitHub integration for automatic deployments on commit.

### Project Structure

```
aiTriage/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── api/         # API routes
│   │   ├── triage/       # Core logic (correlation, LLM, cache, rate limiting)
│   │   └── main.py       # FastAPI app initialization
│   ├── requirements.txt  # Python dependencies
│   └── .env.example     # Environment variable template
├── frontend/             # Astro SPA
│   ├── src/
│   │   ├── react/       # React components
│   │   └── api.ts       # API client
│   └── package.json
├── cli/                  # Ink TUI
├── samples/              # Sample provider payloads + demo scenarios
├── skills/               # SRE Agent Skill for LLMs
├── Dockerfile            # Multi-stage build for Fly.io
├── fly.toml             # Fly.io configuration
└── docker-compose.yml    # Local development (minimal)

```

## Core Features

### 1. Alert Ingestion & Normalization

- Supports multiple providers: Prometheus, Datadog, BetterStack
- Normalizes alerts into a common `AlertEvent` format
- Handles webhook payloads or direct JSON ingestion

### 2. Signal Correlation & Impact Assessment

The system correlates three key signals:
- **Saturation**: Resource utilization (CPU, memory, etc.)
- **Errors**: Error rates and failure metrics
- **Latency**: Response time and performance metrics

**Impact Assessment Logic:**
- **Major Impact**: Critical errors OR critical latency (customer-facing pain)
- **Minor Impact**: Warning-level signals OR high saturation with errors/latency issues
- **No Impact**: High saturation alone (capacity warning only)
- **None**: All signals normal

### 3. LLM-Powered Report Generation

- Generates situation reports in multiple formats: text, markdown, JSON
- Supports OpenAI (ChatGPT) and Anthropic (Claude) LLMs
- Configurable model selection and weights
- Deterministic fallback if LLM unavailable
- Cached reports (SQLite) to avoid duplicate API calls

**Default Models:**
- Anthropic: `claude-sonnet-4-5-20250929` (default)
- OpenAI: `gpt-4o-mini` (default)

### 4. Rate Limiting

- **3 LLM API calls per hour per IP address** (shared across OpenAI and Anthropic)
- Applied to `/api/chat` and `/api/incidents/{id}/report` endpoints
- Cached reports don't count toward the limit
- Rate-limited report requests fall back to deterministic output
- Rate-limited chat requests return `429 Too Many Requests`
- Admin endpoint: `/api/admin/unblock-ip?ip_address={ip}` to reset limits

### 5. Web UI (Astro SPA)

- Dark theme with yellow primary color
- Real-time incident updates via SSE
- Interactive incident management:
  - View incidents with impact/severity indicators
  - Generate reports (markdown/text/JSON)
  - Mark incidents as resolved/auto-closed/false-alert/accepted
  - SRE chat interface with suggested queries
  - LLM provider and model selection
- Glowing/flashing effects for "major" impact and "critical" severity

### 6. API Endpoints

**Core:**
- `POST /api/ingest` - Ingest alerts from providers
- `GET /api/incidents` - List incidents
- `GET /api/incidents/{id}` - Get incident details
- `POST /api/incidents/{id}/report` - Generate situation report
- `POST /api/incidents/{id}/resolution` - Update resolution status

**LLM & Chat:**
- `POST /api/chat` - SRE chat endpoint (free-form Q&A)
- `GET /api/llm/models` - List available LLM models

**Admin:**
- `POST /api/admin/unblock-ip` - Unblock/reset rate limit for IP

**Other:**
- `POST /api/scenarios/{scenario}` - Run demo scenarios
- `GET /api/stream` - SSE stream for real-time updates
- `GET /docs` - Swagger UI
- `GET /openapi.json` - OpenAPI 3.1 schema

## Current State

### What's Working

✅ **Core Functionality:**
- Alert ingestion and normalization
- Signal correlation with impact assessment
- LLM-powered report generation (OpenAI + Anthropic)
- Report caching (SQLite)
- Rate limiting (3 calls/hour/IP)
- Web UI with real-time updates
- Resolution status management
- SRE chat interface
- Admin endpoint for IP unblocking

✅ **Deployment:**
- Dockerfile for Fly.io deployment
- Multi-stage build (frontend + backend)
- SQLite databases in persistent volumes
- CORS configuration for production domain

✅ **Security:**
- Input sanitization for chat endpoint
- Rate limiting to prevent abuse
- Graceful error handling

### Technical Details

**Database Storage:**
- SQLite3 databases stored in `/app/cache/` (or `CACHE_DB_DIR` env var)
- `cache.db` - LLM-generated report cache
- `rate_limit.db` - Rate limit tracking

**Environment Variables:**
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` - LLM API keys
- `AITRIAGE_OPENAI_MODEL` / `AITRIAGE_ANTHROPIC_MODEL` - Model overrides
- `AITRIAGE_LLM_PROVIDER` - Default provider (openai/anthropic)
- `AITRIAGE_LLM_WEIGHTS` - Provider weights for auto mode
- `AITRIAGE_CORS_ORIGINS` - CORS allowed origins
- `CACHE_DB_DIR` - SQLite database directory (default: `backend`)

**Rate Limiting:**
- Limit: 3 LLM API calls per hour per IP
- Shared across all LLM providers
- Tracked in SQLite database
- Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `Retry-After`

## Key Files & Modules

### Backend Core

- `backend/app/main.py` - FastAPI app initialization
- `backend/app/api/router.py` - API route registration
- `backend/app/api/state.py` - Global state (store, engine, events)
- `backend/app/triage/correlation/impact.py` - Impact assessment logic
- `backend/app/triage/llm/` - LLM client implementations
- `backend/app/triage/cache.py` - SQLite report caching
- `backend/app/triage/rate_limit.py` - SQLite rate limiting

### Frontend

- `frontend/src/react/pages/IncidentsPage.tsx` - Main dashboard
- `frontend/src/react/api.ts` - API client
- `frontend/tailwind.config.mjs` - Tailwind + typography plugin

### Configuration

- `Dockerfile` - Multi-stage build for deployment
- `fly.toml` - Fly.io configuration
- `backend/.env.example` - Environment variable template

## Development Workflow

### Local Development

1. **Backend:**
   ```bash
   cd backend
   cp .env.example .env
   uv venv
   source .venv/bin/activate
   uv pip install -r requirements.txt -r requirements-dev.txt
   uvicorn app.main:app --reload --port 8000
   ```

2. **Frontend:**
   ```bash
   bun install
   cp frontend/.env.example frontend/.env
   bun run frontend:dev
   ```

3. **CLI:**
   ```bash
   bun run --cwd cli dev -- tui --api http://localhost:8000
   ```

### Deployment (Fly.io)

1. Set secrets:
   ```bash
   fly secrets set OPENAI_API_KEY=...
   fly secrets set ANTHROPIC_API_KEY=...
   fly secrets set AITRIAGE_CORS_ORIGINS=https://your-domain.com
   ```

2. Create persistent volume (optional, for cache/rate limit persistence):
   ```bash
   fly volumes create cache_data --size 1 --region iad
   ```

3. Deploy:
   ```bash
   fly deploy
   ```


## Design Decisions

### Why SQLite Instead of Redis?

- Simpler deployment (no separate service needed)
- Built into Python (no additional dependencies)
- Sufficient for caching and rate limiting use cases
- Works well with Fly.io persistent volumes

### Why Rate Limit LLM Calls Only?

- LLM API calls are the expensive operations (cost + latency)
- Other endpoints (ingest, list incidents) are lightweight
- Prevents abuse while keeping the API accessible

### Why Deterministic Fallback?

- Ensures the API always returns useful data
- Rate-limited report requests don't fail, they just skip LLM enhancement
- Better user experience than hard failures

## Future Considerations

### Potential Enhancements

- **Authentication**: Add API key or OAuth for admin endpoints
- **Persistent Storage**: Consider PostgreSQL for production incident storage
- **Multi-tenancy**: Support multiple organizations/users
- **Advanced Rate Limiting**: Per-user limits, tiered plans
- **Webhook Support**: Accept webhooks directly from observability tools
- **Alerting**: Send notifications when incidents are detected
- **Runbook Integration**: Link to external runbook systems

### Known Limitations

- In-memory incident store (resets on restart)
- SQLite rate limiting (not distributed across multiple instances)
- No authentication on admin endpoints (security concern for public deployments)
- Single-container deployment (no horizontal scaling for rate limits)

## Quick Reference

### Common Tasks

**Unblock an IP:**
```bash
curl -X POST "http://localhost:8000/api/admin/unblock-ip?ip_address=192.168.1.100"
```

**Generate a report:**
```bash
curl -X POST "http://localhost:8000/api/incidents/{id}/report?format=markdown&llm=auto"
```

**Chat with SRE agent:**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "My API latency is high. What should I check?"}'
```

**Run a demo scenario:**
```bash
curl -X POST http://localhost:8000/api/scenarios/saturation_only
```

### Important Notes

- Rate limiting is per-IP, so users behind NAT/proxies share limits
- Cached reports are invalidated when incidents are updated
- Rate limit database is separate from cache database
- Frontend API calls use relative paths in production (empty `API_BASE`)
- SQLite databases are created automatically on first use

## Contact & Resources

- **SRE Skill**: See `skills/README.md` for instructions on using the bundled SRE Agent Skill with Anthropic and ChatGPT
- **Deployment Docs**: See `docs/DEPLOYMENT.md` for detailed deployment instructions
- **Design Decisions**: See `docs/DECISIONS.md` for correlation/impact heuristics

---

**Last Updated**: 2025-12-19 (configured for Fly.io deployment with GitHub integration)

