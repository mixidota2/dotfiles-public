"""Installer regressions. Every invocation uses an isolated temporary HOME."""

import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
ORCA = Path(".orca/keybindings.json")


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="dotfiles-install-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home with spaces"
        self.home.mkdir()
        self.backups = self.root / "backups with spaces"
        self.target = self.home / ORCA
        self.target.parent.mkdir()
        self.backup = self.backups / ORCA

    def install(self, *args):
        env = dict(os.environ, HOME=str(self.home), DOTFILES_BACKUP_DIR=str(self.backups))
        result = subprocess.run(
            ["sh", str(REPO / "install.sh"), *args],
            env=env, text=True, capture_output=True, check=True,
        )
        return result.stdout

    def assert_orca_linked(self):
        self.assertTrue(self.target.is_symlink())
        self.assertEqual(os.readlink(self.target), str(REPO / "orca" / ORCA))

    def test_install_links_orca_and_preserves_other_orca_files(self):
        settings = self.target.parent / "settings.json"
        settings.write_text('{"local":true}\n')
        self.install()
        self.assert_orca_linked()
        self.assertEqual(settings.read_text(), '{"local":true}\n')
        self.assertFalse(self.backups.exists())

    def test_existing_file_is_backed_up_and_reinstall_is_idempotent(self):
        self.target.write_text('{"local-shortcut":"keep me"}\n')
        self.install()
        self.assert_orca_linked()
        self.assertEqual(self.backup.read_text(), '{"local-shortcut":"keep me"}\n')
        output = self.install()
        self.assertNotIn("backup  ", output)
        self.assertNotIn("link    ", output)
        self.assertEqual(list(self.backup.parent.iterdir()), [self.backup])

    def test_existing_symlinks_are_backed_up_without_touching_referent(self):
        for broken in (False, True):
            with self.subTest(broken=broken):
                if self.target.is_symlink():
                    self.target.unlink()
                other = self.root / ("missing.json" if broken else "other.json")
                if not broken:
                    other.write_text("original referent\n")
                self.target.symlink_to(other)
                self.install()
                self.assert_orca_linked()
                saved = self.backup.with_name(self.backup.name + ".1") if broken else self.backup
                self.assertTrue(saved.is_symlink())
                self.assertEqual(os.readlink(saved), str(other))
                if not broken:
                    self.assertEqual(other.read_text(), "original referent\n")
                else:
                    self.assertFalse(other.exists())

    def test_occupied_backup_names_are_never_replaced(self):
        self.backup.parent.mkdir(parents=True)
        self.backup.write_text("old backup\n")
        first = self.backup.with_name(self.backup.name + ".1")
        first.symlink_to(self.root / "missing-backup-target")
        second = self.backup.with_name(self.backup.name + ".2")
        second.mkdir()
        (second / "sentinel").write_text("old directory\n")
        referent = self.root / "backup-referent.json"
        referent.write_text("old symlink referent\n")
        third = self.backup.with_name(self.backup.name + ".3")
        third.symlink_to(referent)
        self.target.write_text("current settings\n")
        self.install()
        self.assert_orca_linked()
        self.assertEqual(self.backup.read_text(), "old backup\n")
        self.assertEqual(os.readlink(first), str(self.root / "missing-backup-target"))
        self.assertEqual((second / "sentinel").read_text(), "old directory\n")
        self.assertEqual(os.readlink(third), str(referent))
        self.assertEqual(referent.read_text(), "old symlink referent\n")
        self.assertEqual(self.backup.with_name(self.backup.name + ".4").read_text(), "current settings\n")

    def test_existing_directory_is_backed_up_intact(self):
        self.target.mkdir()
        (self.target / "sentinel").write_text("keep directory contents\n")
        self.install()
        self.assert_orca_linked()
        self.assertEqual((self.backup / "sentinel").read_text(), "keep directory contents\n")

    def test_dry_run_does_not_change_existing_file_or_backup(self):
        self.target.write_text("current settings\n")
        self.backup.parent.mkdir(parents=True)
        self.backup.write_text("old backup\n")
        before = sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*"))
        output = self.install("--dry-run")
        after = sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*"))
        self.assertEqual(before, after)
        self.assertFalse(self.target.is_symlink())
        self.assertEqual(self.target.read_text(), "current settings\n")
        self.assertEqual(self.backup.read_text(), "old backup\n")
        self.assertIn(str(self.backup) + ".1", output)
        self.assertIn(str(REPO / "orca" / ORCA), output)

    def test_package_destinations_are_unique_and_match_dry_run(self):
        script = (REPO / "install.sh").read_text()
        match = re.search(r"^for package in (.+); do$", script, re.MULTILINE)
        self.assertIsNotNone(match)
        packages = match.group(1).split()
        self.assertEqual(packages.count("orca"), 1)
        destinations = []
        for package in packages:
            self.assertTrue((REPO / package).is_dir(), package)
            destinations.extend(
                str(p.relative_to(REPO / package))
                for p in (REPO / package).rglob("*") if p.is_file()
            )
        self.assertEqual(len(destinations), len(set(destinations)))
        self.assertIn(str(ORCA), destinations)
        output = self.install("--dry-run")
        for relative in destinations:
            self.assertEqual(output.count(f"link    {self.home / relative} -> "), 1, relative)
        self.assertFalse(self.target.exists())
        self.assertFalse(self.backups.exists())


if __name__ == "__main__":
    unittest.main()
