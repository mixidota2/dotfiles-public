"""External skill installer checks use a stub npx and an isolated HOME."""

from pathlib import Path
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]


class SkillsInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="dotfiles-skills-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home with spaces"
        self.home.mkdir()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.args_file = self.root / "npx-args"
        self.npx = self.bin / "npx"
        self.npx.write_text(
            "#!/bin/sh\n"
            "printf '%s\\n' \"$@\" > \"$NPX_ARGS_FILE\"\n"
            'exit "${NPX_EXIT_CODE:-0}"\n'
        )
        self.npx.chmod(0o755)

    def install(self, exit_code=0):
        return subprocess.run(
            ["/bin/sh", str(REPO / "skills/install.sh")],
            env={
                "HOME": str(self.home),
                "PATH": str(self.bin),
                "NPX_ARGS_FILE": str(self.args_file),
                "NPX_EXIT_CODE": str(exit_code),
            },
            text=True, capture_output=True,
        )

    def test_installs_tk_from_standalone_repository(self):
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.args_file.read_text().splitlines(), [
            "skills", "add", "mixidota2/tasukura-skills",
            "--global", "--agent", "codex", "--copy", "--yes", "--skill", "tk",
        ])
        self.assertIn("tk skill installed.", result.stdout)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_failed_install_does_not_report_success(self):
        result = self.install(exit_code=17)
        self.assertEqual(result.returncode, 17)
        self.assertNotIn("tk skill installed", result.stdout)

    def test_missing_npx_fails_before_install(self):
        self.npx.unlink()
        result = self.install()
        self.assertEqual(result.returncode, 1)
        self.assertIn("npx is required", result.stderr)
        self.assertFalse(self.args_file.exists())
        self.assertNotIn("tk skill installed", result.stdout)


if __name__ == "__main__":
    unittest.main()

