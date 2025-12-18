import { Command } from "commander";
import { readFile } from "node:fs/promises";

const program = new Command();

program
  .name("ai-triage")
  .description("aiTriage CLI: ingest/correlate alerts and generate situation reports")
  .option("--api <url>", "API base URL", process.env.AITRIAGE_API_BASE_URL || "http://localhost:8000");

program
  .command("demo")
  .description("Run a built-in demo scenario on the backend")
  .argument("<scenario>", "Scenario name (saturation_only | full_outage)")
  .action(async (scenario: string) => {
    const opts = program.opts<{ api: string }>();
    const res = await fetch(`${opts.api}/api/scenarios/${encodeURIComponent(scenario)}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: "{}",
    });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}: ${await res.text()}`);
    }
    const data = (await res.json()) as any;
    process.stdout.write(JSON.stringify(data, null, 2) + "\n");
  });

program
  .command("ingest")
  .description("Ingest a sample payload file (single object or array of {provider,payload})")
  .requiredOption("--file <path>", "Path to JSON file")
  .action(async (cmd: { file: string }) => {
    const opts = program.opts<{ api: string }>();
    const raw = await readFile(cmd.file, "utf-8");
    const parsed = JSON.parse(raw);
    const items = Array.isArray(parsed) ? parsed : [parsed];

    const incidentIds: string[] = [];
    let events = 0;

    for (const item of items) {
      const body = {
        provider: item.provider ?? null,
        payload: item.payload ?? item,
      };
      const res = await fetch(`${opts.api}/api/ingest`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${await res.text()}`);
      }
      const data = (await res.json()) as any;
      for (const id of data.incidentIds || []) incidentIds.push(String(id));
      events += Number(data.eventsIngested || 0);
    }

    process.stdout.write(
      JSON.stringify({ incidentIds: Array.from(new Set(incidentIds)), eventsIngested: events }, null, 2) + "\n"
    );
  });

program
  .command("report")
  .description("Generate a situation report for an incident")
  .requiredOption("--incident <id>", "Incident id")
  .option("--format <fmt>", "text|markdown|json", "markdown")
  .option("--llm <mode>", "auto|off|openai|anthropic", "auto")
  .action(async (cmd: { incident: string; format: string; llm: string }) => {
    const opts = program.opts<{ api: string }>();
    const url = `${opts.api}/api/incidents/${encodeURIComponent(cmd.incident)}/report?format=${encodeURIComponent(
      cmd.format
    )}&llm=${encodeURIComponent(cmd.llm)}`;
    const res = await fetch(url, { method: "POST" });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}: ${await res.text()}`);
    }
    process.stdout.write(await res.text());
  });

program
  .command("tui")
  .description("Launch the interactive TUI (k9s-like)")
  .action(async () => {
    const opts = program.opts<{ api: string }>();
    process.env.AITRIAGE_API_BASE_URL = opts.api;
    // lazy import so non-TUI commands don't load ink
    const { runTui } = await import("./tui");
    await runTui();
  });

program.parseAsync(process.argv).catch((err) => {
  process.stderr.write(String(err?.stack || err) + "\n");
  process.exit(1);
});


