# SRE Observability Review Skill

This directory contains an SRE Agent Skill for Claude and other AI assistants.

## Files

All files are at the root level (required by Claude):

- `SKILL.md` — Main skill instructions (required entry point)
- `EXAMPLES.md` — Detailed scenario walkthroughs
- `PLATFORMS.md` — Platform-specific guidance (Prometheus, Datadog, etc.)

## Creating the Skill Archive

To create a `.zip` for Claude:

```bash
zip -r sre-skill.zip SKILL.md EXAMPLES.md PLATFORMS.md
```

## Use with Anthropic Claude

### Direct Import

1. Create the zip archive (see above)
2. Import directly into Claude Projects or workspace

### Manual Setup

1. Create a new **Project** in Claude
2. Copy the contents of `SKILL.md` into the **system / instructions** field
3. Optionally add `EXAMPLES.md` and `PLATFORMS.md` as project knowledge
4. Save the project as something like **"SRE Observability Triage"**

### Via Claude API

Load `SKILL.md` as the system message:

```python
messages = [{"role": "system", "content": "<contents of SKILL.md>"}, ...]
```

## Use with ChatGPT (OpenAI)

### Custom GPT

1. Go to **Explore GPTs → Create**
2. Paste `SKILL.md` contents into **Instructions / System prompt**
3. Optionally upload `EXAMPLES.md` and `PLATFORMS.md` as knowledge
4. Name it **"SRE Observability Review Agent"** and save

### OpenAI API

Send `SKILL.md` as the `system` message in Chat Completions or set as assistant instructions.
