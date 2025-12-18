# Deployment Guide

## fly.io (recommended)

### First-time setup

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login
fly auth login

# Launch (creates fly.toml if needed, but don't deploy yet)
fly launch --no-deploy
# - Choose a unique app name (or use auto-generated)
# - Choose a region (defaults work fine)
# - Say NO to Postgres/Redis (we use in-memory store for MVP)
```

### Set secrets (required for LLM features)

```bash
# OpenAI
fly secrets set OPENAI_API_KEY=sk-...

# Or Anthropic
fly secrets set ANTHROPIC_API_KEY=sk-ant-...

# Optional: specify models
fly secrets set AITRIAGE_ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
fly secrets set AITRIAGE_OPENAI_MODEL=gpt-4o-mini

# Optional: set default provider for llm=auto
fly secrets set AITRIAGE_LLM_PROVIDER=anthropic

# Optional: set weights for auto mode
fly secrets set AITRIAGE_LLM_WEIGHTS="openai:3,anthropic:1"
```

### Deploy

```bash
# Build + push + deploy
fly deploy

# Open in browser
fly open

# View logs
fly logs

# Check status
fly status
```

### Update deployment

```bash
# After making code changes, redeploy:
fly deploy

# To update secrets:
fly secrets set KEY=new_value
```

### Scaling

```bash
# Auto-scale (default in fly.toml)
# - Machines stop when idle (min_machines_running = 0)
# - Auto-start on first request

# To keep 1 machine always running:
fly scale count 1 --max-per-region 2

# To see current scaling:
fly scale show
```

### Troubleshooting

**"Connection refused" or 502 errors:**
- Check logs: `fly logs`
- Verify health check passes: `fly checks list`
- Ensure internal_port in fly.toml matches the app (8000)

**LLM not working:**
- Verify secrets: `fly secrets list`
- Check you have credits/valid keys for the provider

**Frontend not loading:**
- Ensure the frontend was built in Docker (check build logs)
- The backend serves static files from `/static` when it exists

## Docker (local testing)

```bash
# Build
docker build -t aitriage:local .

# Run (with env vars)
docker run --rm -p 8000:8000 \
  -e OPENAI_API_KEY=sk-... \
  aitriage:local

# Or use .env file
docker run --rm -p 8000:8000 \
  --env-file backend/.env \
  aitriage:local

# Visit http://localhost:8000
```

## Notes

- The Dockerfile uses **multi-stage build**:
  - Stage 1: Bun builds the Astro frontend
  - Stage 2: Python runtime serves FastAPI + static frontend
- fly.io **persistent volumes are NOT used** (in-memory incident store)
  - For a real deployment, you'd add Redis or Postgres
- **Cost**: With `min_machines_running=0`, fly.io free tier should cover light usage

