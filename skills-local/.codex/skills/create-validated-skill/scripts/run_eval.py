#!/usr/bin/env python3
"""Run reproducible Codex routing and behavioral evaluations for a skill."""

from __future__ import annotations

import argparse
import concurrent.futures
import contextlib
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Iterator

try:
    import yaml
except ImportError:  # pragma: no cover - exercised by CLI error handling
    yaml = None


ROOT = Path(__file__).resolve().parent.parent
EXECUTOR_SCHEMA = ROOT / "assets" / "executor-output.schema.json"
GRADER_SCHEMA = ROOT / "assets" / "semantic-grade.schema.json"


def load_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML is required; run with: uv run --with pyyaml python scripts/run_eval.py ...")
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a YAML mapping: {path}")
    return value


def write_yaml(path: Path, value: Any) -> None:
    if yaml is None:
        raise RuntimeError("PyYAML is required")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False, allow_unicode=True), encoding="utf-8")


def utc_stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


@contextlib.contextmanager
def isolated_codex_home(
    source_home: Path, skill_dir: Path | None
) -> Iterator[Path]:
    with tempfile.TemporaryDirectory(prefix="validated-skill-codex-home.") as raw:
        home = Path(raw)
        auth = source_home / "auth.json"
        if not auth.is_file():
            raise RuntimeError(f"Codex auth file not found: {auth}")
        (home / "auth.json").symlink_to(auth)
        if skill_dir is not None:
            skills = home / "skills"
            skills.mkdir()
            (skills / skill_dir.name).symlink_to(skill_dir.resolve())
        yield home


def run_codex(
    *,
    prompt: str,
    output_schema: Path,
    output_path: Path,
    events_path: Path,
    stderr_path: Path,
    codex_bin: str,
    source_home: Path,
    skill_dir: Path | None,
    profile: str,
    model: str | None,
    timeout_seconds: int,
) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    workdir = output_path.parent / "workspace"
    workdir.mkdir(exist_ok=True)
    cmd = [
        codex_bin,
        "exec",
        "--ephemeral",
        "--json",
        "--color",
        "never",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "--output-schema",
        str(output_schema),
        "--output-last-message",
        str(output_path),
        "--cd",
        str(workdir),
    ]
    if model:
        cmd.extend(["--model", model])

    env = os.environ.copy()
    with contextlib.ExitStack() as stack:
        if profile == "isolated":
            home = stack.enter_context(isolated_codex_home(source_home, skill_dir))
            env["CODEX_HOME"] = str(home)
            cmd.append("--ignore-user-config")
        elif profile != "normal":
            raise ValueError(f"unknown profile: {profile}")
        cmd.append(prompt)
        with events_path.open("w", encoding="utf-8") as events:
            try:
                proc = subprocess.run(
                    cmd,
                    stdout=events,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=env,
                    timeout=timeout_seconds,
                )
            except subprocess.TimeoutExpired as exc:
                stderr_path.write_text(
                    f"executor timed out after {timeout_seconds}s\n{exc.stderr or ''}",
                    encoding="utf-8",
                )
                return 124
        stderr_path.write_text(proc.stderr, encoding="utf-8")
        return proc.returncode


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def event_strings(path: Path) -> list[str]:
    values: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        values.append(json.dumps(event, ensure_ascii=False))
    return values


def event_metrics(path: Path) -> dict[str, Any]:
    tool_uses = 0
    usage: dict[str, Any] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item", {})
        if event.get("type") == "item.completed" and item.get("type") in {
            "command_execution",
            "mcp_tool_call",
            "web_search",
        }:
            tool_uses += 1
        if event.get("type") == "turn.completed" and isinstance(event.get("usage"), dict):
            usage = event["usage"]
    return {"tool_uses": tool_uses, "usage": usage}


def detect_activation(events_path: Path, skill_name: str) -> tuple[bool, list[str]]:
    needle = f"skills/{skill_name}/SKILL.md"
    evidence: list[str] = []
    for event in event_strings(events_path):
        lowered = event.lower()
        toolish = any(token in lowered for token in ("tool", "command_execution", "exec_command"))
        if toolish and needle in event.replace("\\\\", "/"):
            evidence.append(event[:1000])
    return bool(evidence), evidence


def text_grade(output: dict[str, Any], requirement: dict[str, Any]) -> dict[str, Any]:
    corpus = json.dumps(output, ensure_ascii=False)
    config = requirement.get("text", {})
    patterns = config.get("regex_any", [])
    matches = [pattern for pattern in patterns if re.search(pattern, corpus)]
    return {
        "verdict": "pass" if matches else "fail",
        "matched_patterns": matches,
        "patterns": patterns,
    }


def executor_contract_prompt(user_prompt: str, skill_dir: Path | None) -> str:
    skill_clause = (
        f"Use the skill at {skill_dir.resolve()} when applicable. " if skill_dir is not None else ""
    )
    return f"""Act as a fresh executor for this user request.

User request:
{user_prompt}

{skill_clause}Do not inspect evaluation definitions, expected answers, or ledger files
under the target skill's evals/ directory. The assigned runner workspace and output
paths are allowed even if their parent path contains evals/results. Complete the
request as far as the read-only environment permits; otherwise follow any explicit
narrative-evaluation instruction in the scenario and mark genuinely blocked work
honestly.

In the structured final response, return the deliverable plus a phase trace for
Understanding, Planning, Execution, and Formatting. For every unclear point use
Issue / Cause / General Fix Rule. List discretionary fill-ins, retries, and
uncompleted work. Do not grade yourself against any hidden checklist.
"""


def semantic_grade(
    *,
    task: dict[str, Any],
    executor_output: dict[str, Any],
    trial_dir: Path,
    args: argparse.Namespace,
) -> tuple[dict[str, Any], int]:
    requirements = [
        {
            "id": req["id"],
            "critical": bool(req.get("critical")),
            "description": req["description"],
            "rubric": req["semantic"]["rubric"],
        }
        for req in task["requirements"]
    ]
    prompt = f"""Act only as an evaluator. Do not use or inspect the target skill.

Scenario:
{task['scenario']}

Hidden requirements:
{json.dumps(requirements, ensure_ascii=False, indent=2)}

Executor output:
{json.dumps(executor_output, ensure_ascii=False, indent=2)}

Judge each requirement as pass, fail, or unclear using observable evidence. Do not
accept the executor's self-reported success without confirming it in the
deliverable. For every fail or unclear verdict, return Issue / Cause / General Fix
Rule. Return one result for every requirement id.
"""
    output = trial_dir / "semantic-grade.json"
    events = trial_dir / "semantic-events.jsonl"
    stderr = trial_dir / "semantic-stderr.txt"
    code = run_codex(
        prompt=prompt,
        output_schema=GRADER_SCHEMA,
        output_path=output,
        events_path=events,
        stderr_path=stderr,
        codex_bin=args.codex_bin,
        source_home=args.source_codex_home,
        skill_dir=None,
        profile="isolated",
        model=args.model,
        timeout_seconds=args.timeout_seconds,
    )
    return (read_json(output) if output.is_file() else {"requirements": []}), code


def merge_requirement_grades(
    task: dict[str, Any], output: dict[str, Any], semantic: dict[str, Any]
) -> list[dict[str, Any]]:
    semantic_by_id = {item.get("id"): item for item in semantic.get("requirements", [])}
    results: list[dict[str, Any]] = []
    for requirement in task["requirements"]:
        req_id = requirement["id"]
        text = text_grade(output, requirement)
        sem = semantic_by_id.get(req_id, {"verdict": "unclear", "evidence": "missing semantic grade"})
        sem_verdict = sem.get("verdict", "unclear")
        text_required = bool(requirement.get("text", {}).get("required", False))
        surface_disagreement = sem_verdict == "pass" and text["verdict"] != "pass"
        if sem_verdict == "fail":
            combined = "fail"
        elif sem_verdict == "pass":
            combined = "unclear" if text_required and surface_disagreement else "pass"
        else:
            combined = "unclear"
        results.append(
            {
                "id": req_id,
                "critical": bool(requirement.get("critical")),
                "description": requirement["description"],
                "text": text,
                "semantic": sem,
                "surface_disagreement": surface_disagreement,
                "combined_verdict": combined,
            }
        )
    return results


def routing_cases(skill_dir: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for relative in manifest["routing"]["cases"]:
        group = load_yaml(skill_dir / "evals" / relative)
        for case in group["cases"]:
            result.append({**case, "kind": group["kind"], "expected_activation": group["expected_activation"]})
    return result


def run_routing(skill_dir: Path, manifest: dict[str, Any], run_dir: Path, args: argparse.Namespace) -> list[dict[str, Any]]:
    trials = args.trials or manifest["routing"].get("trials_per_case", 1)
    cases = [
        case for case in routing_cases(skill_dir, manifest)
        if not args.case or case["id"] in args.case
    ]
    jobs = [
        (profile, case, trial)
        for profile in args.profile
        for case in cases
        for trial in range(1, trials + 1)
    ]

    def execute(job: tuple[str, dict[str, Any], int]) -> dict[str, Any]:
        profile, case, trial = job
        trial_dir = run_dir / "routing" / profile / case["id"] / f"trial-{trial}"
        output = trial_dir / "executor-output.json"
        events = trial_dir / "executor-events.jsonl"
        stderr = trial_dir / "executor-stderr.txt"
        code = run_codex(
            prompt=executor_contract_prompt(case["prompt"], None),
            output_schema=EXECUTOR_SCHEMA,
            output_path=output,
            events_path=events,
            stderr_path=stderr,
            codex_bin=args.codex_bin,
            source_home=args.source_codex_home,
            skill_dir=skill_dir,
            profile=profile,
            model=args.model,
            timeout_seconds=args.timeout_seconds,
        )
        activated, evidence = detect_activation(events, skill_dir.name)
        if code != 0:
            verdict = "error"
        else:
            verdict = "pass" if activated == bool(case["expected_activation"]) else "fail"
        result = {
            "case": case["id"],
            "kind": case["kind"],
            "critical": bool(case.get("critical")),
            "profile": profile,
            "trial": trial,
            "expected_activation": bool(case["expected_activation"]),
            "observed_activation": activated,
            "verdict": verdict,
            "exit_code": code,
            "output_path": str(output),
            "events_path": str(events),
            "activation_evidence": evidence,
        }
        write_yaml(trial_dir / "result.yaml", result)
        return result

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(execute, jobs))
    return sorted(results, key=lambda item: (item["profile"], item["kind"], item["case"], item["trial"]))


def run_behavior(skill_dir: Path, manifest: dict[str, Any], run_dir: Path, args: argparse.Namespace) -> list[dict[str, Any]]:
    trials = args.trials or manifest.get("trials_per_task", 1)
    tasks = []
    task_paths = list(manifest["tasks"])
    if args.include_holdout:
        task_paths.extend(manifest.get("holdout", []))
    for relative in task_paths:
        task = load_yaml(skill_dir / "evals" / relative)
        if args.case and task["id"] not in args.case:
            continue
        tasks.append(task)
    configs = ["with_skill", "without_skill"] if args.baseline else ["with_skill"]
    jobs = [
        (task, config, trial)
        for task in tasks
        for config in configs
        for trial in range(1, trials + 1)
    ]

    def execute(job: tuple[dict[str, Any], str, int]) -> dict[str, Any]:
        task, config, trial = job
        trial_dir = run_dir / "behavior" / task["id"] / config / f"trial-{trial}"
        output_path = trial_dir / "executor-output.json"
        events = trial_dir / "executor-events.jsonl"
        stderr = trial_dir / "executor-stderr.txt"
        started = time.perf_counter()
        code = run_codex(
            prompt=executor_contract_prompt(
                task["scenario"], skill_dir if config == "with_skill" else None
            ),
            output_schema=EXECUTOR_SCHEMA,
            output_path=output_path,
            events_path=events,
            stderr_path=stderr,
            codex_bin=args.codex_bin,
            source_home=args.source_codex_home,
            skill_dir=skill_dir if config == "with_skill" else None,
            profile="isolated",
            model=args.model,
            timeout_seconds=args.timeout_seconds,
        )
        duration_ms = round((time.perf_counter() - started) * 1000)
        metrics = event_metrics(events)
        output = read_json(output_path) if output_path.is_file() else {}
        semantic_skipped = code != 0
        if semantic_skipped:
            # An executor failure already makes the trial fail. Grading an empty or
            # partial artifact adds latency and can double the timeout without
            # producing useful evidence.
            semantic = {"requirements": []}
            semantic_code = None
        else:
            semantic, semantic_code = semantic_grade(
                task=task, executor_output=output, trial_dir=trial_dir, args=args
            )
        grades = merge_requirement_grades(task, output, semantic)
        critical_ok = code == 0 and semantic_code == 0 and all(
            item["combined_verdict"] == "pass" for item in grades if item["critical"]
        )
        result = {
            "task": task["id"],
            "kind": task["kind"],
            "config": config,
            "trial": trial,
            "verdict": "pass" if critical_ok else "fail",
            "executor_exit_code": code,
            "semantic_exit_code": semantic_code,
            "semantic_skipped": semantic_skipped,
            "output_path": str(output_path),
            "events_path": str(events),
            "executor_duration_ms": duration_ms,
            "executor_tool_uses": metrics["tool_uses"],
            "executor_usage": metrics["usage"],
            "phase_trace": output.get("phase_trace", {}),
            "unclear_points": output.get("unclear_points", []),
            "discretionary_fill_ins": output.get("discretionary_fill_ins", []),
            "retries": output.get("retries", {}),
            "requirements": grades,
        }
        write_yaml(trial_dir / "result.yaml", result)
        return result

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(execute, jobs))
    return sorted(
        results,
        key=lambda item: (item["kind"], item["task"], item["config"], item["trial"]),
    )


def behavior_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for config in sorted({item["config"] for item in results}):
        subset = [item for item in results if item["config"] == config]
        requirements = [
            requirement
            for item in subset
            for requirement in item.get("requirements", [])
        ]
        summary[config] = {
            "trials": len(subset),
            "task_pass_rate": (
                sum(item["verdict"] == "pass" for item in subset) / len(subset)
                if subset else 0.0
            ),
            "requirement_pass_rate": (
                sum(item["combined_verdict"] == "pass" for item in requirements)
                / len(requirements)
                if requirements else 0.0
            ),
            "average_duration_ms": (
                sum(item.get("executor_duration_ms", 0) for item in subset) / len(subset)
                if subset else 0.0
            ),
            "average_tool_uses": (
                sum(item.get("executor_tool_uses", 0) for item in subset) / len(subset)
                if subset else 0.0
            ),
        }
    return summary


def baseline_delta(summary: dict[str, Any]) -> dict[str, Any]:
    with_skill = summary.get("with_skill")
    without_skill = summary.get("without_skill")
    if not with_skill or not without_skill:
        return {}
    return {
        "task_pass_rate": with_skill["task_pass_rate"] - without_skill["task_pass_rate"],
        "requirement_pass_rate": (
            with_skill["requirement_pass_rate"] - without_skill["requirement_pass_rate"]
        ),
        "average_duration_ms": (
            with_skill["average_duration_ms"] - without_skill["average_duration_ms"]
        ),
        "average_tool_uses": (
            with_skill["average_tool_uses"] - without_skill["average_tool_uses"]
        ),
    }


def routing_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    by_profile: dict[str, Any] = {}
    for profile in sorted({item["profile"] for item in results}):
        subset = [item for item in results if item["profile"] == profile]
        kinds: dict[str, Any] = {}
        for kind in ("positive", "negative", "near-miss"):
            group = [item for item in subset if item["kind"] == kind]
            if not group:
                continue
            activations = sum(bool(item["observed_activation"]) for item in group)
            kinds[kind] = {
                "trials": len(group),
                "activation_rate": activations / len(group),
                "pass_rate": sum(item["verdict"] == "pass" for item in group) / len(group),
            }
        by_profile[profile] = kinds
    return by_profile


def routing_gates(results: list[dict[str, Any]], manifest: dict[str, Any]) -> dict[str, Any]:
    thresholds = manifest["routing"]["thresholds"]
    summary = routing_summary(results)
    gates: dict[str, Any] = {}
    for profile, kinds in summary.items():
        positive = kinds.get("positive", {})
        negative = kinds.get("negative", {})
        near_miss = kinds.get("near-miss", {})
        critical_positive = [
            item for item in results
            if item["profile"] == profile and item["kind"] == "positive" and item["critical"]
        ]
        checks = {
            "executor_processes": all(
                item["exit_code"] == 0 for item in results if item["profile"] == profile
            ),
        }
        # A targeted --case rerun should gate only the kinds it actually ran.
        # Treating omitted groups as failures makes the supported regression
        # workflow report a false overall failure.
        if positive:
            checks["critical_positive_activation"] = all(
                item["observed_activation"] and item["exit_code"] == 0
                for item in critical_positive
            )
            checks["positive_activation_rate"] = (
                positive["activation_rate"] >= thresholds["positive_activation_rate"]
            )
        if negative:
            checks["negative_false_activation_rate"] = (
                negative["activation_rate"] <= thresholds["negative_false_activation_rate"]
            )
        if near_miss:
            checks["near_miss_false_activation_rate"] = (
                near_miss["activation_rate"]
                <= thresholds["near_miss_false_activation_rate"]
            )
        gates[profile] = {"checks": checks, "pass": all(checks.values())}
    return gates


def contained_path(path: Path, root: Path) -> str | None:
    """Return a portable path, or explicitly omit an out-of-scope reference."""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


def compact_run_record(run_record: dict[str, Any], skill_dir: Path) -> dict[str, Any]:
    results_root = Path(run_record["results_dir"])
    results_dir = contained_path(results_root, skill_dir)

    def relative_artifact(path: str) -> str | None:
        return contained_path(Path(path), results_root)

    routing_trials = [
        {
            "case": item["case"],
            "kind": item["kind"],
            "critical": item["critical"],
            "profile": item["profile"],
            "trial": item["trial"],
            "expected_activation": item["expected_activation"],
            "observed_activation": item["observed_activation"],
            "verdict": item["verdict"],
            "exit_code": item["exit_code"],
        }
        for item in run_record["routing_trials"]
    ]
    behavior_trials = []
    for item in run_record["behavior_trials"]:
        artifacts = {
            field: relative_artifact(item[field])
            for field in ("output_path", "events_path")
        }
        requirements = []
        for requirement in item.get("requirements", []):
            semantic = requirement.get("semantic", {})
            req = {
                "id": requirement["id"],
                "critical": requirement["critical"],
                "combined_verdict": requirement["combined_verdict"],
                "text_verdict": requirement.get("text", {}).get("verdict", requirement.get("text_verdict", "unclear")),
                "semantic_verdict": semantic.get("verdict", requirement.get("semantic_verdict", "unclear")),
            }
            if req["combined_verdict"] != "pass":
                req["evidence"] = semantic.get("evidence", requirement.get("evidence", ""))
                req["general_fix_rule"] = semantic.get("general_fix_rule", requirement.get("general_fix_rule", ""))
            requirements.append(req)
        behavior_trials.append({
            "task": item["task"],
            "kind": item["kind"],
            "config": item.get("config", "with_skill"),
            "trial": item["trial"],
            "verdict": item["verdict"],
            "executor_exit_code": item["executor_exit_code"],
            "semantic_exit_code": item["semantic_exit_code"],
            **artifacts,
            "unresolved_artifacts": [field for field, path in artifacts.items() if path is None],
            "executor_duration_ms": item.get("executor_duration_ms", 0),
            "executor_tool_uses": item.get("executor_tool_uses", 0),
            "phase_status": {
                phase: (value.get("status", "unknown") if isinstance(value, dict) else value)
                for phase, value in (item.get("phase_trace") or item.get("phase_status", {})).items()
            },
            "unclear_points": [
                {
                    "issue": issue.get("issue", ""),
                    "general_fix_rule": issue.get("general_fix_rule", ""),
                }
                for issue in item.get("unclear_points", [])
            ],
            "retry_count": item.get("retries", {}).get("count", item.get("retry_count", 0)),
            "requirements": requirements,
        })
    return {
        "id": run_record["id"],
        "mode": run_record["mode"],
        "model": run_record["model"],
        "results_dir": results_dir,
        "results_dir_scope": "skill" if results_dir is not None else "external",
        "routing_summary": run_record["routing_summary"],
        "routing_gates": run_record["routing_gates"],
        "routing_trials": routing_trials,
        "behavior_summary": run_record.get("behavior_summary", {}),
        "baseline_delta": run_record.get("baseline_delta", {}),
        "behavior_trials": behavior_trials,
    }


def update_failure_patterns(ledger: dict[str, Any], run_record: dict[str, Any]) -> None:
    patterns = ledger.setdefault("failure_patterns", [])
    by_rule = {item["general_fix_rule"]: item for item in patterns}
    occurrences = []
    for trial in run_record["behavior_trials"]:
        if trial.get("config", "with_skill") != "with_skill":
            continue
        for issue in trial.get("unclear_points", []):
            occurrences.append((trial, "executor", issue))
        for requirement in trial.get("requirements", []):
            semantic = requirement.get("semantic", {})
            if semantic.get("verdict") in ("fail", "unclear") and semantic.get("general_fix_rule"):
                occurrences.append((trial, requirement["id"], semantic))
    for trial, source, issue in occurrences:
        rule = issue.get("general_fix_rule", "").strip()
        if not rule:
            continue
        pattern = by_rule.get(rule)
        if pattern is None:
            pattern = {
                "general_fix_rule": rule,
                "example_issue": issue.get("issue", ""),
                "seen_in": [],
            }
            patterns.append(pattern)
            by_rule[rule] = pattern
        pattern["seen_in"].append({
            "run": run_record["id"],
            "task": trial["task"],
            "trial": trial["trial"],
            "source": source,
        })


def append_ledger(skill_dir: Path, run_record: dict[str, Any]) -> None:
    ledger_path = skill_dir / "evals" / "ledger.yaml"
    ledger = load_yaml(ledger_path) if ledger_path.is_file() else {"skill": skill_dir.name}
    update_failure_patterns(ledger, run_record)
    ledger.setdefault("automated_runs", []).append(compact_run_record(run_record, skill_dir))
    write_yaml(ledger_path, ledger)


def self_test() -> int:
    requirement = {
        "id": "x",
        "critical": True,
        "description": "mentions validation",
        "text": {"regex_any": ["(?i)validat"]},
        "semantic": {"rubric": "mentions validation"},
    }
    output = {"deliverable": "Run validation."}
    assert text_grade(output, requirement)["verdict"] == "pass"
    task = {"requirements": [requirement]}
    semantic = {"requirements": [{"id": "x", "verdict": "pass", "evidence": "present"}]}
    assert merge_requirement_grades(task, output, semantic)[0]["combined_verdict"] == "pass"
    summary = behavior_summary([
        {
            "config": "with_skill",
            "verdict": "pass",
            "requirements": [{"combined_verdict": "pass"}],
            "executor_duration_ms": 10,
            "executor_tool_uses": 1,
        },
        {
            "config": "without_skill",
            "verdict": "fail",
            "requirements": [{"combined_verdict": "fail"}],
            "executor_duration_ms": 5,
            "executor_tool_uses": 0,
        },
    ])
    assert baseline_delta(summary)["task_pass_rate"] == 1.0
    manifest = {
        "routing": {
            "thresholds": {
                "critical_positive_activation_rate": 1.0,
                "positive_activation_rate": 0.9,
                "negative_false_activation_rate": 0.05,
                "near_miss_false_activation_rate": 0.1,
            }
        }
    }
    targeted = [{
        "profile": "isolated",
        "kind": "near-miss",
        "critical": False,
        "observed_activation": False,
        "exit_code": 0,
        "verdict": "pass",
    }]
    assert routing_gates(targeted, manifest)["isolated"]["pass"] is True
    print("run_eval self-test passed")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("skill_directory", nargs="?", type=Path)
    parser.add_argument("--mode", choices=("routing", "behavior", "all"), default="all")
    parser.add_argument("--profile", action="append", choices=("isolated", "normal"))
    parser.add_argument("--trials", type=int)
    parser.add_argument("--case", action="append")
    parser.add_argument("--results-dir", type=Path)
    parser.add_argument("--source-codex-home", type=Path, default=Path.home() / ".codex")
    parser.add_argument("--codex-bin", default="codex")
    parser.add_argument("--model")
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--include-holdout", action="store_true")
    parser.add_argument("--baseline", action="store_true")
    parser.add_argument("--no-ledger", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.self_test:
        return self_test()
    if args.skill_directory is None:
        print("error: skill_directory is required", file=sys.stderr)
        return 2
    if args.trials is not None and args.trials < 1:
        print("error: --trials must be positive", file=sys.stderr)
        return 2
    if args.jobs < 1:
        print("error: --jobs must be positive", file=sys.stderr)
        return 2
    if args.timeout_seconds < 1:
        print("error: --timeout-seconds must be positive", file=sys.stderr)
        return 2
    if args.baseline and args.mode == "routing":
        print("error: --baseline applies only to behavior evaluation", file=sys.stderr)
        return 2
    skill_dir = args.skill_directory.expanduser().resolve()
    manifest = load_yaml(skill_dir / "evals" / "eval.yaml")
    args.source_codex_home = args.source_codex_home.expanduser().resolve()
    args.profile = args.profile or manifest.get("routing", {}).get("profiles", ["isolated"])
    run_id = utc_stamp()
    results_root = (args.results_dir or skill_dir / "evals" / "results").expanduser().resolve()
    run_dir = results_root / run_id
    routing: list[dict[str, Any]] = []
    behavior: list[dict[str, Any]] = []
    if args.mode in ("routing", "all"):
        routing = run_routing(skill_dir, manifest, run_dir, args)
    if args.mode in ("behavior", "all"):
        behavior = run_behavior(skill_dir, manifest, run_dir, args)
    behavior_stats = behavior_summary(behavior)
    record = {
        "id": run_id,
        "mode": args.mode,
        "model": args.model or "default",
        "results_dir": str(run_dir),
        "routing_summary": routing_summary(routing),
        "routing_gates": routing_gates(routing, manifest) if routing else {},
        "routing_trials": routing,
        "behavior_summary": behavior_stats,
        "baseline_delta": baseline_delta(behavior_stats),
        "behavior_trials": behavior,
    }
    write_yaml(run_dir / "summary.yaml", record)
    if not args.no_ledger:
        append_ledger(skill_dir, record)
    routing_failed = any(not gate["pass"] for gate in record["routing_gates"].values())
    behavior_failed = any(
        item["verdict"] != "pass" and item.get("config") == "with_skill"
        for item in behavior
    )
    failed = routing_failed or behavior_failed
    print(json.dumps({
        "id": run_id,
        "results_dir": str(run_dir),
        "routing_gates": record["routing_gates"],
        "routing_trial_count": len(routing),
        "behavior_trial_count": len(behavior),
        "behavior_summary": record["behavior_summary"],
        "baseline_delta": record["baseline_delta"],
    }, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
