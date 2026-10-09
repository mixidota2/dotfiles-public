"""Portable ledger regressions using synthetic files and stubbed model calls only."""

import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[1]
RUNNER = REPO / "skills-local/.codex/skills/create-validated-skill/scripts/run_eval.py"
SPEC = importlib.util.spec_from_file_location("run_eval", RUNNER)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)
RUN_ID = "20260101T000000Z"


class EvalPortabilityTests(unittest.TestCase):
    def setUp(self):
        if runner.yaml is None:
            self.fail("PyYAML is required for evaluation-record regression tests")
        self.temp = tempfile.TemporaryDirectory(prefix="eval-portability-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def run_fixture(self, home_name, results_mode="default", outcome="pass"):
        home = self.root / home_name
        skill = home / "checkout 日本語" / "skills" / "example-skill"
        invocation = home / "working directory"
        invocation.mkdir(parents=True)
        task_id = "事例 sample"
        runner.write_yaml(skill / "evals/eval.yaml", {
            "tasks": ["tasks/日本語 task.yaml"],
            "routing": {
                "profiles": ["isolated"],
                "cases": ["routing/positive.yaml"],
                "thresholds": {"positive_activation_rate": 1.0},
            },
        })
        runner.write_yaml(skill / "evals/tasks/日本語 task.yaml", {
            "id": task_id, "kind": "typical", "scenario": "Synthetic scenario",
            "requirements": [{
                "id": "r1", "critical": True, "description": "Validate output",
                "text": {"regex_any": ["validation"]},
                "semantic": {"rubric": "Observable validation"},
            }],
        })
        runner.write_yaml(skill / "evals/routing/positive.yaml", {
            "kind": "positive", "expected_activation": True,
            "cases": [{"id": "route sample", "critical": True, "prompt": "Synthetic route"}],
        })
        legacy = {
            "id": "legacy", "results_dir": "/legacy-machine/home/old-person/run",
            "behavior_trials": [{"output_path": "behavior/old.json"}],
        }
        ledger_path = skill / "evals/ledger.yaml"
        runner.write_yaml(ledger_path, {"skill": skill.name, "automated_runs": [legacy]})
        inside = skill / "custom 結果"
        outside = home / "external 結果"
        paths = {
            "relative-inside": os.path.relpath(inside, invocation),
            "absolute-inside": str(inside),
            "relative-outside": os.path.relpath(outside, invocation),
            "absolute-outside": str(outside),
            "tilde-outside": "~/external 結果",
        }
        args = [str(RUNNER), str(skill), "--mode", "all"]
        if results_mode != "default":
            args += ["--results-dir", paths[results_mode]]
        if outcome == "empty-trials":
            args += ["--case", "not-selected"]
        snapshots = {}

        def fake_codex(**kwargs):
            output = kwargs["output_path"]
            output.parent.mkdir(parents=True, exist_ok=True)
            is_semantic = kwargs["output_schema"] == runner.GRADER_SCHEMA
            failed = outcome == "failed" and not is_semantic
            if is_semantic:
                value = {"requirements": [{
                    "id": "r1", "verdict": "pass", "evidence": "validation present",
                }]}
            else:
                value = {} if outcome == "empty-output" else {
                    "deliverable": "validation",
                    "phase_trace": {"Execution": {"status": "complete"}},
                    "retries": {"count": 2},
                }
            if not failed:
                output.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
                snapshots[output] = output.read_bytes()
            # Absolute activation evidence must remain local, not enter path fields.
            event = {"type": "item.completed", "item": {
                "type": "command_execution", "command": f"cat {skill}/SKILL.md",
            }}
            kwargs["events_path"].write_text(json.dumps(event) + "\n", encoding="utf-8")
            kwargs["stderr_path"].write_text("synthetic failure" if failed else "", encoding="utf-8")
            return 124 if failed else 0

        stdout = io.StringIO()
        previous_cwd = Path.cwd()
        try:
            os.chdir(invocation)
            with (
                mock.patch.dict(os.environ, {"HOME": str(home)}),
                mock.patch.object(runner.sys, "argv", args),
                mock.patch.object(runner, "utc_stamp", return_value=RUN_ID),
                mock.patch.object(runner.time, "perf_counter", return_value=1.0),
                mock.patch.object(runner, "run_codex", side_effect=fake_codex) as codex,
                mock.patch.object(runner, "isolated_codex_home", side_effect=AssertionError("no credentials")),
                mock.patch.object(runner.subprocess, "run", side_effect=AssertionError("no real executor")),
                contextlib.redirect_stdout(stdout),
            ):
                exit_code = runner.main()
        finally:
            os.chdir(previous_cwd)
        ledger = runner.load_yaml(ledger_path)
        self.assertEqual(ledger["automated_runs"][0], legacy)
        self.assertEqual(len(ledger["automated_runs"]), 2)
        record = ledger["automated_runs"][-1]
        cli = json.loads(stdout.getvalue())
        run_dir = Path(cli["results_dir"])
        summary = runner.load_yaml(run_dir / "summary.yaml")
        self.assertEqual(summary["results_dir"], str(run_dir))
        for path, contents in snapshots.items():
            self.assertEqual(path.read_bytes(), contents)
        serialized = json.dumps(record, ensure_ascii=False)
        self.assertNotIn(str(home), serialized)
        self.assertNotIn(home_name, serialized)
        self.assertNotIn(str(self.root), serialized)
        self.assertEqual(exit_code, 1 if outcome == "failed" else 0)
        if outcome == "empty-trials":
            self.assertEqual(codex.call_count, 0)
            self.assertEqual(record["behavior_trials"], [])
            self.assertEqual(record["routing_trials"], [])
        else:
            self.assertEqual(cli["behavior_trial_count"], 1)
            self.assertEqual(cli["routing_trial_count"], 1)
            trial = record["behavior_trials"][0]
            self.assertEqual(trial["unresolved_artifacts"], [])
            self.assertEqual(trial["output_path"], f"behavior/{task_id}/with_skill/trial-1/executor-output.json")
            self.assertEqual(trial["events_path"], f"behavior/{task_id}/with_skill/trial-1/executor-events.jsonl")
            self.assertEqual(summary["behavior_trials"][0]["output_path"], str(run_dir / trial["output_path"]))
            if outcome == "failed":
                self.assertEqual(codex.call_count, 2)  # no semantic call after failure
                self.assertEqual(trial["executor_exit_code"], 124)
                self.assertIsNone(trial["semantic_exit_code"])
                self.assertEqual(trial["requirements"][0]["evidence"], "missing semantic grade")
                self.assertFalse(record["routing_gates"]["isolated"]["pass"])
            else:
                self.assertEqual(codex.call_count, 3)
                self.assertEqual(trial["verdict"], "pass")
                self.assertEqual(record["behavior_summary"]["with_skill"]["trials"], 1)
        return record, summary, skill

    def test_same_evaluation_is_identical_across_homes_and_result_locations(self):
        for mode in ("default", "relative-inside", "absolute-inside", "relative-outside", "absolute-outside", "tilde-outside"):
            with self.subTest(mode=mode):
                first, _, _ = self.run_fixture(f"alice {mode}", mode)
                second, _, _ = self.run_fixture(f"別ユーザー {mode}", mode)
                self.assertEqual(first, second)
                external = mode.endswith("outside")
                self.assertEqual(first["results_dir_scope"], "external" if external else "skill")
                expected = None if external else f"{'evals/results' if mode == 'default' else 'custom 結果'}/{RUN_ID}"
                self.assertEqual(first["results_dir"], expected)

    def test_failed_and_empty_runs_are_portable(self):
        for outcome in ("failed", "empty-trials", "empty-output"):
            with self.subTest(outcome=outcome):
                first, _, _ = self.run_fixture(f"alice {outcome}", outcome=outcome)
                second, _, _ = self.run_fixture(f"bob {outcome}", outcome=outcome)
                self.assertEqual(first, second)

    def test_external_artifacts_are_explicit_and_never_copied_or_modified(self):
        _, raw, skill = self.run_fixture("artifact owner")
        run_dir = Path(raw["results_dir"])
        outside = skill.parent / "private 日本語 evidence.json"
        outside.write_text("original file stays local", encoding="utf-8")
        # Include traversal and a symlink whose lexical path appears in scope.
        link = run_dir / "linked evidence.json"
        link.symlink_to(outside)
        raw["behavior_trials"][0]["output_path"] = str(link)
        raw["behavior_trials"][0]["events_path"] = str(run_dir / ".." / ".." / "outside.jsonl")
        before = copy.deepcopy(raw)
        files_before = sorted(str(p) for p in skill.parent.rglob("*"))
        compact = runner.compact_run_record(raw, skill)
        trial = compact["behavior_trials"][0]
        self.assertIsNone(trial["output_path"])
        self.assertIsNone(trial["events_path"])
        self.assertEqual(trial["unresolved_artifacts"], ["output_path", "events_path"])
        self.assertEqual(raw, before)
        self.assertEqual(outside.read_text(encoding="utf-8"), "original file stays local")
        self.assertEqual(sorted(str(p) for p in skill.parent.rglob("*")), files_before)
        self.assertNotIn(outside.name, json.dumps(compact, ensure_ascii=False))

    def test_symlinked_result_root_is_external(self):
        skill = self.root / "skill"
        outside = self.root / "external"
        skill.mkdir()
        outside.mkdir()
        link = skill / "results"
        link.symlink_to(outside, target_is_directory=True)
        self.assertIsNone(runner.contained_path(link / RUN_ID, skill))
        self.assertEqual(runner.contained_path(link / RUN_ID / "出力 file.json", link / RUN_ID), "出力 file.json")

    def test_evidence_failure_patterns_and_legacy_records_are_preserved(self):
        _, raw, skill = self.run_fixture("evidence owner")
        evidence = "Synthetic /home/example/private.txt evidence must remain verbatim"
        trial = raw["behavior_trials"][0]
        trial["verdict"] = "fail"
        trial["unclear_points"] = [{"issue": evidence, "general_fix_rule": "Keep diagnostic evidence"}]
        trial["requirements"][0]["combined_verdict"] = "fail"
        trial["requirements"][0]["semantic"] = {
            "verdict": "fail", "evidence": evidence, "general_fix_rule": "Preserve outcome",
        }
        original = copy.deepcopy(raw)
        ledger_path = skill / "evals/ledger.yaml"
        old = runner.load_yaml(ledger_path)["automated_runs"]
        runner.append_ledger(skill, raw)
        ledger = runner.load_yaml(ledger_path)
        self.assertEqual(ledger["automated_runs"][:-1], old)
        saved_trial = ledger["automated_runs"][-1]["behavior_trials"][0]
        self.assertEqual(saved_trial["requirements"][0]["evidence"], evidence)
        self.assertEqual(saved_trial["unclear_points"][0]["issue"], evidence)
        self.assertEqual(saved_trial["retry_count"], 2)
        self.assertEqual(len(ledger["failure_patterns"]), 2)
        self.assertEqual(raw, original)


if __name__ == "__main__":
    unittest.main()
