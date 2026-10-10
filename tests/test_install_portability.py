"""Independent installer fixtures; tool commands are always local shell stubs."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
SYSTEM_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"
TK_SOURCE = "git+https://github.com/mixidota2/tasukura.git"


class InstallerPortabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="dotfiles-portability-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "checkout with spaces"
        self.repo.mkdir()
        for name in ("install.sh", "Brewfile"):
            shutil.copy2(REPO / name, self.repo / name)
        # This contract is independent of install.sh's package list and filter.
        self.files = {
            "shell/.zshrc": ".zshrc",
            "cmux/.config/cmux/preferences.json": ".config/cmux/preferences.json",
            "wezterm/.config/wezterm/wezterm.lua": ".config/wezterm/wezterm.lua",
            "yazi/.config/yazi/yazi.toml": ".config/yazi/yazi.toml",
            "nvim/.config/nvim/init.lua": ".config/nvim/init.lua",
            "herdr/.config/herdr/keybindings.json": ".config/herdr/keybindings.json",
            "orca/.orca/keybindings.json": ".orca/keybindings.json",
            "pi/.pi/agent/AGENTS.md": ".pi/agent/AGENTS.md",
            "codex/.codex/AGENTS.md": ".codex/AGENTS.md",
            "tk/.config/tk/config.toml": ".config/tk/config.toml",
            "skills-local/.codex/skills/new-skill/.settings": ".codex/skills/new-skill/.settings",
            "skills-local/.codex/skills/new-skill/scripts/fresh.py": ".codex/skills/new-skill/scripts/fresh.py",
            "shell/.config/new-tool/new file.json": ".config/new-tool/new file.json",
            "shell/.config/new-tool/cache-policy.json": ".config/new-tool/cache-policy.json",
        }
        for source in self.files:
            self.write_source(source)
        self.home = self.root / "home with spaces"
        self.home.mkdir()
        self.backups = self.root / "backups"
        self.bin = self.root / "bin"
        self.bin.mkdir()
        # Only required OS utilities are exposed, never a host brew, uv or tk.
        for name in ("cat", "date", "dirname", "find", "readlink", "mkdir", "mv", "ln"):
            source = shutil.which(name, path=SYSTEM_PATH)
            self.assertIsNotNone(source, name)
            (self.bin / name).symlink_to(source)
        self.log = self.root / "tool-calls"

    def write_source(self, relative):
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture\n")

    def write_tool(self, name, body="exit 0\n"):
        path = self.bin / name
        path.write_text(
            "#!/bin/sh\n"
            f"printf '{name}\\n' >> \"$TOOL_CALLS\"\n"
            "printf '%s\\n' \"$@\" >> \"$TOOL_CALLS\"\n"
            + body
        )
        path.chmod(0o755)
        return path

    def install(self, *args):
        return subprocess.run(
            ["/bin/sh", str(self.repo / "install.sh"), *args],
            env={
                "HOME": str(self.home),
                "DOTFILES_BACKUP_DIR": str(self.backups),
                "PATH": str(self.bin),
                "TOOL_CALLS": str(self.log),
                "TEST_BIN": str(self.bin),
            },
            text=True, capture_output=True,
        )

    def test_only_real_configuration_files_are_planned_and_linked(self):
        cruft = (
            "shell/.DS_Store",
            "shell/.config/new-tool/.DS_Store",
            "skills-local/.codex/skills/new-skill/scripts/__pycache__/run_eval.cpython-312.pyc",
            "skills-local/.codex/skills/new-skill/scripts/__pycache__/nested/metadata.txt",
            "skills-local/.codex/skills/new-skill/scripts/old.pyc",
            "skills-local/.codex/skills/new-skill/scripts/old.pyo",
        )
        for source in cruft:
            self.write_source(source)
        existing = self.home / ".DS_Store"
        existing.write_text("local metadata\n")
        expected = {
            str(self.home / destination): str(self.repo / source)
            for source, destination in self.files.items()
        }
        expected[str(self.home / ".pi/agent/skills")] = str(self.home / ".codex/skills")
        preview = self.install("--dry-run")
        self.assertEqual(preview.returncode, 0, preview.stderr)
        planned = [line for line in preview.stdout.splitlines() if line.startswith("link    ")]
        self.assertCountEqual(planned, [f"link    {dst} -> {src}" for dst, src in expected.items()])
        self.assertEqual(list(self.home.iterdir()), [existing])
        self.assertFalse(self.backups.exists())
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        actual = {str(path): os.readlink(path) for path in self.home.rglob("*") if path.is_symlink()}
        self.assertEqual(actual, expected)
        self.assertEqual(existing.read_text(), "local metadata\n")
        self.assertFalse(self.backups.exists())
        for source in cruft:
            self.assertEqual((self.repo / source).read_text(), "fixture\n")

    def test_dry_run_plans_tk_after_brew_without_uv(self):
        self.write_tool("brew", "exit 99\n")
        result = self.install("--dry-run", "--tools")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"+ brew bundle --file {self.repo / 'Brewfile'}", result.stdout)
        self.assertIn(f"+ uv tool install {TK_SOURCE}", result.stdout)
        self.assertLess(result.stdout.index("+ brew bundle"), result.stdout.index("+ uv tool install"))
        self.assertFalse(self.log.exists())
        self.assertEqual(list(self.home.iterdir()), [])
        self.assertFalse(self.backups.exists())

    def test_dry_run_never_executes_existing_tools(self):
        for tool in ("brew", "uv", "tk"):
            self.write_tool(tool, "exit 99\n")
        result = self.install("--dry-run", "--tools")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("tk is already installed", result.stdout)
        self.assertNotIn("+ uv tool install", result.stdout)
        self.assertFalse(self.log.exists())

    def test_tools_still_require_brew(self):
        for args in (("--dry-run", "--tools"), ("--tools",)):
            with self.subTest(args=args):
                result = self.install(*args)
                self.assertEqual(result.returncode, 1)
                self.assertIn("Homebrew is required", result.stderr)
                self.assertNotIn("Done.", result.stdout)
                self.assertFalse(self.log.exists())

    def test_real_tools_fail_when_brew_does_not_provide_uv(self):
        self.write_tool("brew")
        result = self.install("--tools")
        self.assertEqual(result.returncode, 1)
        self.assertIn("uv was not found after brew bundle", result.stderr)
        self.assertEqual(self.log.read_text().splitlines(), ["brew", "bundle", "--file", str(self.repo / "Brewfile")])
        self.assertNotIn("Done.", result.stdout)

    def test_failed_brew_stops_before_uv(self):
        self.write_tool("brew", "exit 17\n")
        self.write_tool("uv")
        result = self.install("--tools")
        self.assertEqual(result.returncode, 17)
        self.assertNotIn("uv", self.log.read_text().splitlines())
        self.assertNotIn("Done.", result.stdout)

    def test_real_tools_can_use_uv_provided_by_brew(self):
        self.write_tool("uv").rename(self.bin / "future-uv")
        self.write_tool("brew", 'mv "$TEST_BIN/future-uv" "$TEST_BIN/uv"\n')
        result = self.install("--tools")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.log.read_text().splitlines(), [
            "brew", "bundle", "--file", str(self.repo / "Brewfile"),
            "uv", "tool", "install", TK_SOURCE,
        ])
        self.assertIn("Done.", result.stdout)

    def test_failed_uv_install_is_reported(self):
        self.write_tool("brew")
        self.write_tool("uv", "exit 23\n")
        result = self.install("--tools")
        self.assertEqual(result.returncode, 23)
        self.assertNotIn("Done.", result.stdout)

    def test_real_tools_skip_existing_tk(self):
        for tool in ("brew", "uv", "tk"):
            self.write_tool(tool)
        result = self.install("--tools")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("tk is already installed", result.stdout)
        self.assertEqual(self.log.read_text().splitlines(), ["brew", "bundle", "--file", str(self.repo / "Brewfile")])


if __name__ == "__main__":
    unittest.main()
