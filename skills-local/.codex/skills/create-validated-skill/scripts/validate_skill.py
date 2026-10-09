#!/usr/bin/env python3
"""Validate a Codex skill and its behavioral evaluation scaffold."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK_RE = re.compile(r"\[[^\]]+\]\((?!https?://|#)([^)]+)\)")
ALLOWED_FRONTMATTER = {"name", "description"}


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md must start with YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("SKILL.md frontmatter is not closed")
    values: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if not line.strip():
            continue
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not match:
            raise ValueError(f"unsupported frontmatter line: {line}")
        values[match.group(1)] = match.group(2).strip()
    return values, text[end + 5 :]


def validate(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        return ["SKILL.md is missing"]

    text = skill_file.read_text(encoding="utf-8")
    try:
        frontmatter, body = parse_frontmatter(text)
    except ValueError as exc:
        return [str(exc)]

    unknown = set(frontmatter) - ALLOWED_FRONTMATTER
    if unknown:
        errors.append(f"frontmatter has unsupported keys: {', '.join(sorted(unknown))}")
    name = frontmatter.get("name", "")
    description = frontmatter.get("description", "")
    if not NAME_RE.fullmatch(name) or len(name) > 64:
        errors.append("frontmatter name must be lowercase kebab-case and at most 64 characters")
    if name != skill_dir.name:
        errors.append(f"frontmatter name {name!r} does not match directory {skill_dir.name!r}")
    if not description or len(description) > 1024:
        errors.append("description must be 1-1024 characters")
    if "TODO" in description or "TODO" in body:
        errors.append("SKILL.md contains unresolved TODO text")

    for link in LINK_RE.findall(body):
        path = (skill_dir / link.split("#", 1)[0]).resolve()
        if not path.exists():
            errors.append(f"linked resource does not exist: {link}")

    eval_dir = skill_dir / "evals"
    required = [
        eval_dir / "eval.yaml",
        eval_dir / "ledger.yaml",
        eval_dir / "tasks" / "typical.yaml",
        eval_dir / "tasks" / "edge.yaml",
        eval_dir / "tasks" / "negative.yaml",
        eval_dir / "routing" / "positive.yaml",
        eval_dir / "routing" / "negative.yaml",
        eval_dir / "routing" / "near-miss.yaml",
    ]
    for path in required:
        if not path.is_file():
            errors.append(f"required evaluation file is missing: {path.relative_to(skill_dir)}")

    if (eval_dir / "eval.yaml").is_file():
        manifest = (eval_dir / "eval.yaml").read_text(encoding="utf-8")
        manifest_name = re.search(r"(?m)^name:\s*(\S+)\s*$", manifest)
        if not manifest_name or manifest_name.group(1) != name:
            errors.append("evals/eval.yaml name must match the skill name")
        for token in (
            "version: 2",
            "routing:",
            "profiles:",
            "thresholds:",
            "positive_activation_rate:",
            "negative_false_activation_rate:",
            "near_miss_false_activation_rate:",
        ):
            if token not in manifest:
                errors.append(f"evals/eval.yaml is missing {token}")

    if eval_dir.is_dir():
        for path in sorted(eval_dir.rglob("*.yaml")):
            if "TODO" in path.read_text(encoding="utf-8"):
                errors.append(f"{path.relative_to(skill_dir)} contains unresolved TODO text")

    tasks_dir = eval_dir / "tasks"
    if tasks_dir.is_dir():
        task_files = sorted(tasks_dir.glob("*.yaml"))
        if not task_files:
            errors.append("evals/tasks contains no YAML scenarios")
        for path in task_files:
            task = path.read_text(encoding="utf-8")
            for key in ("id:", "kind:", "scenario:", "requirements:"):
                if key not in task:
                    errors.append(f"{path.relative_to(skill_dir)} is missing {key}")
            for key in ("critical: true", "description:", "text:", "regex_any:", "semantic:", "rubric:"):
                if key not in task:
                    errors.append(f"{path.relative_to(skill_dir)} is missing grader field {key}")

    routing_dir = eval_dir / "routing"
    if routing_dir.is_dir():
        expected = {
            "positive.yaml": ("kind: positive", "expected_activation: true"),
            "negative.yaml": ("kind: negative", "expected_activation: false"),
            "near-miss.yaml": ("kind: near-miss", "expected_activation: false"),
        }
        for filename, tokens in expected.items():
            path = routing_dir / filename
            if not path.is_file():
                continue
            routing = path.read_text(encoding="utf-8")
            for token in (*tokens, "cases:", "id:", "prompt:"):
                if token not in routing:
                    errors.append(f"{path.relative_to(skill_dir)} is missing {token}")

    for relative in ("assets/executor-output.schema.json", "assets/semantic-grade.schema.json"):
        path = skill_dir / relative
        if path.is_file():
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                errors.append(f"{relative} is invalid JSON: {exc}")

    forbidden = {"README.md", "CHANGELOG.md", "INSTALL.md"}
    for filename in forbidden:
        if (skill_dir / filename).exists():
            errors.append(f"unnecessary auxiliary file present: {filename}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("skill_directory", type=Path)
    args = parser.parse_args()
    skill_dir = args.skill_directory.expanduser().resolve()
    errors = validate(skill_dir)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"validated {skill_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
