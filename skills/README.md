# SRE Observability Review Skill

This repo includes an SRE Agent Skill packaged as `skills/sre-skill.zip`. It contains a single file:

- `observability-review.skill` — a structured instruction set you can paste into Claude or ChatGPT to improve the quality and consistency of SRE / observability outputs.

## 1. Download the skill

From GitHub:

1. Navigate to the `skills/` directory.
2. Download `sre-skill.zip`.
3. Unzip it locally to get `observability-review.skill`.

The `.skill` file is just text — you can open it in any editor.

## 2. Use with Anthropic Claude

### Via Claude UI (Projects / custom agent)

1. Open Claude in the browser.
2. Create a new **Project** (or equivalent “agent” space).
3. Open `observability-review.skill` and copy its entire contents.
4. Paste that text into the **system / instructions** field of the project.
5. Save the project as something like **“SRE Observability Triage”**.

Claude will now follow those instructions whenever you chat in that project (for triaging incidents, reviewing alert streams, etc.).

### Via Claude API

1. Load `observability-review.skill` as a string in your code.
2. Send it as the **system** message when calling the Claude Messages API, e.g.:

   - `messages = [{"role": "system", "content": "<contents of observability-review.skill>"}, …]`

3. Your user prompts can then focus on the concrete incident data (logs, metrics, alerts), while the skill guides how Claude structures its response.

## 3. Use with ChatGPT (OpenAI)

### Custom GPT (ChatGPT UI)

1. In ChatGPT, go to **Explore GPTs → Create**.
2. Under **Instructions / System prompt**, paste the full contents of `observability-review.skill`.
3. Name it something like **“SRE Observability Review Agent”** and save.

You now have a reusable GPT that applies the same SRE skill instructions.

### OpenAI API (Chat Completions / Assistants)

1. Read `observability-review.skill` into your app.
2. For **Chat Completions**, send it as the `system` message:

   - `messages = [{"role": "system", "content": "<skill text>"}, …]`

3. For the **Assistants API**, set the skill text as the assistant’s instructions/description when you create or update the assistant.

In both cases, the skill becomes the persistent high-level guidance for how the model should analyze and summarize observability data.


