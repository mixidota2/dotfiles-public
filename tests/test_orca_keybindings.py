"""Regression checks for the small, documented Orca override set.

Action IDs and format were verified against stablyai/orca 59b9bdeb.
See docs/orca-shortcuts.md for the upstream parser and registry links.
"""

import json
from pathlib import Path
import unittest


REPO = Path(__file__).resolve().parents[1]


class OrcaKeybindingTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((REPO / "orca/.orca/keybindings.json").read_text())
        self.mac = self.config["platforms"]["darwin"]

    def test_version_and_platform_scope(self):
        self.assertEqual(set(self.config), {"version", "keybindings", "platforms"})
        self.assertEqual(self.config["version"], 1)
        self.assertEqual(self.config["keybindings"], {})
        self.assertEqual(set(self.config["platforms"]), {"darwin", "linux", "win32"})
        self.assertEqual(self.config["platforms"]["linux"], {})
        self.assertEqual(self.config["platforms"]["win32"], {})

    def test_requested_mapping_and_preserved_bindings(self):
        self.assertEqual(self.mac, {
            "workspace.create": ["Mod+N", "Mod+Shift+N"],
            "workspace.delete": ["Mod+Shift+Backspace"],
            "worktree.navigateUp": ["Mod+Shift+ArrowUp"],
            "worktree.navigateDown": ["Mod+Shift+ArrowDown"],
            "tab.newTerminal": ["Mod+T"],
            "tab.newBrowser": ["Mod+Shift+B"],
            "tab.close": ["Mod+W"],
            "tab.nextAllTypes": ["Mod+Shift+ArrowRight", "Mod+Shift+BracketRight"],
            "tab.previousAllTypes": ["Mod+Shift+ArrowLeft", "Mod+Shift+BracketLeft"],
            "tab.selectByIndex": ["Ctrl+1"],
            "terminal.closePane": ["Mod+Shift+W"],
            "terminal.splitRight": ["Mod+D"],
            "terminal.splitDown": ["Mod+Shift+D"],
            "terminal.focusNextPane": ["Mod+Alt+ArrowRight", "Mod+Alt+ArrowDown"],
            "terminal.focusPreviousPane": ["Mod+Alt+ArrowLeft", "Mod+Alt+ArrowUp"],
        })

    def test_navigation_matches_existing_cmux_overrides(self):
        cmux = json.loads((REPO / "cmux/.config/cmux/cmux.json").read_text())
        pairs = {
            "prevSidebarTab": "worktree.navigateUp",
            "nextSidebarTab": "worktree.navigateDown",
            "prevSurface": "tab.previousAllTypes",
            "nextSurface": "tab.nextAllTypes",
        }
        for source, target in pairs.items():
            translated = self.mac[target][0].lower().replace("mod+", "cmd+").replace("arrow", "")
            self.assertEqual(translated, cmux["shortcuts"]["bindings"][source])

    def test_no_duplicate_explicit_chords(self):
        # Upstream effective-default collision checks are a separate verification;
        # this local regression protects the explicit override set without network.
        chords = [chord for bindings in self.mac.values() for chord in bindings]
        self.assertEqual(len(chords), len(set(chords)))
        self.assertNotIn("Mod+Shift+W", self.mac["workspace.delete"])


if __name__ == "__main__":
    unittest.main()
