from __future__ import annotations

import json
from typing import Any, Dict


def render_json(report: Dict[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True, default=str)


def render_text(report: Dict[str, Any]) -> str:
    impact = report.get("impact", {})
    lines: list[str] = []
    lines.append(f"aiTriage Situation Report — {report.get('service')} ({report.get('env')})")
    lines.append("")
    lines.append(f"Incident: {report.get('incidentId')}")
    lines.append(f"Status:   {report.get('status')}")
    lines.append(f"Impact:   {impact.get('impact')} (confidence {impact.get('confidence')})")
    lines.append("")
    lines.append("Summary")
    lines.append("------")
    lines.append(str(report.get("summary") or "").strip())
    lines.append("")

    lines.append("Signals")
    lines.append("-------")
    for sig in report.get("signals", []):
        obs = sig.get("observed")
        thr = sig.get("threshold")
        unit = sig.get("unit") or ""
        val = f"{obs}{unit}" if obs is not None else "n/a"
        tval = f"{thr}{unit}" if thr is not None else "n/a"
        lines.append(f"- {sig.get('signalType')}: {sig.get('state')} (trend {sig.get('trend')}) [{val} / {tval}]")

    lines.append("")
    lines.append("Suggested runbook steps")
    lines.append("-----------------------")
    for idx, step in enumerate(report.get("runbook", []), start=1):
        lines.append(f"{idx}. {step.get('title')}")
        for k in ("verify", "mitigate", "confirm"):
            items = step.get(k) or []
            if items:
                lines.append(f"   - {k}:")
                for it in items:
                    lines.append(f"     - {it}")
        cmds = step.get("exampleCommands") or []
        if cmds:
            lines.append("   - exampleCommands:")
            for c in cmds:
                lines.append(f"     - {c}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_markdown(report: Dict[str, Any]) -> str:
    impact = report.get("impact", {})
    md: list[str] = []
    md.append(f"## aiTriage Situation Report — `{report.get('service')}` (`{report.get('env')}`)")
    md.append("")
    md.append(f"- **Incident**: `{report.get('incidentId')}`")
    md.append(f"- **Status**: `{report.get('status')}`")
    md.append(f"- **Impact**: **{impact.get('impact')}** (confidence {impact.get('confidence')})")
    md.append(f"- **Classification**: `{impact.get('classification')}`")
    md.append("")
    md.append("### Summary")
    md.append("")
    md.append(str(report.get("summary") or "").strip() or "_No summary_")
    md.append("")

    md.append("### Signals")
    md.append("")
    for sig in report.get("signals", []):
        obs = sig.get("observed")
        thr = sig.get("threshold")
        unit = sig.get("unit") or ""
        val = f"{obs}{unit}" if obs is not None else "n/a"
        tval = f"{thr}{unit}" if thr is not None else "n/a"
        md.append(f"- **{sig.get('signalType')}**: `{sig.get('state')}` (trend `{sig.get('trend')}`) — `{val}` / `{tval}`")
    md.append("")

    md.append("### Suggested runbook steps")
    md.append("")
    for idx, step in enumerate(report.get("runbook", []), start=1):
        md.append(f"{idx}. **{step.get('title')}**")
        for k in ("verify", "mitigate", "confirm"):
            items = step.get(k) or []
            if items:
                md.append(f"   - **{k}**:")
                for it in items:
                    md.append(f"     - {it}")
        cmds = step.get("exampleCommands") or []
        if cmds:
            md.append("   - **exampleCommands**:")
            for c in cmds:
                md.append(f"     - `{c}`")
        md.append("")

    return "\n".join(md).rstrip() + "\n"


