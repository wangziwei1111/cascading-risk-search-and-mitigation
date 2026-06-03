from __future__ import annotations

import json
from pathlib import Path


FIGURE1_STEPS = [
    "initialize generation and load scenario",
    "sample initial N-k outage",
    "identify islands",
    "balance generation and load inside each island",
    "run power flow",
    "terminate if power flow fails",
    "agent selects action",
    "apply proactive line opening",
    "process islands again",
    "run power flow again",
    "detect overloaded lines",
    "sample overload trips with paper beta rule",
    "terminate if no new trip occurs",
    "advance to next generation if new trips occur",
]


def paper_trace_from_env(env, policy_name: str = "do_nothing") -> dict:
    return {
        "paper_figure": "Figure 1",
        "policy": policy_name,
        "system": env.case.get("name", ""),
        "initial_outages": env.initial_outages,
        "flow_steps": FIGURE1_STEPS,
        "trace": env.trace,
    }


def save_paper_trace(trace: dict, json_path: Path, md_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(trace, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# Figure 1 Cascade Flow Trace",
        "",
        "This is a same-environment trace for the paper cascade mitigation flow.",
        "",
        f"System: `{trace.get('system', '')}`",
        f"Policy: `{trace.get('policy', '')}`",
        f"Initial outages: `{trace.get('initial_outages', [])}`",
        "",
        "## Paper Flow Steps",
        "",
    ]
    lines.extend(f"{idx}. {step}" for idx, step in enumerate(trace["flow_steps"], start=1))
    lines.extend(["", "## Episode Trace", ""])
    for row in trace["trace"]:
        lines.append(
            f"- generation {row['generation']}: action={row.get('action')}, "
            f"valid={row.get('action_valid')}, opened={row.get('proactive_opened_line')}, "
            f"new trips={row.get('newly_failed_lines')}, pf_converged={row.get('pf_converged')}, "
            f"terminal_reason={row.get('terminal_reason')}, reward={row.get('reward'):.4f}"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

