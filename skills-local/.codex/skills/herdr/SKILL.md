---
name: herdr
description: Herdr terminal workspace manager usage guide. Use when operating Herdr, configuring Herdr keybindings, workspaces/tabs/panes, agents, sessions, persistence, remote attach, integrations, or troubleshooting Herdr behavior.
---

# Herdr Usage Skill

Use this skill when the user asks about Herdr usage, configuration, keyboard shortcuts, sessions, workspaces/tabs/panes, agent state, integrations, remote access, or troubleshooting.

Primary reference: `references/herdr-guide.md`.

## Quick Principles

- Herdr is a **terminal workspace manager for AI coding agents**.
- It runs as a **background server + terminal client** by default.
- The server owns panes and process state; clients attach/detach and render the UI.
- Detaching/closing the client does **not** stop panes or agents. Stopping the server does.
- Structure is: **session → workspace → tab → pane → process/agent**.
- Herdr is **mouse-native**; keyboard bindings are optional.
- Default keyboard model is prefix-first (`ctrl+b`) to avoid stealing keys from shells/editors.
- For prefix-free direct bindings, prefer chords that survive OS + terminal + shell layers; official docs recommend `ctrl+alt` as the safest general family.

## Always Check Local Configuration First

Before answering shortcut questions, inspect the local config because custom keybindings override defaults:

```bash
herdr --default-config
[ -f ~/.config/herdr/config.toml ] && cat ~/.config/herdr/config.toml
```

This dotfiles repository provides the following macOS mapping in `herdr/.config/herdr/config.toml`; verify the installed `~/.config/herdr/config.toml` before relying on it:

- Herdr config uses `alt` for the physical **Option** key.
- cmux-style `Cmd` shortcuts are mapped to Herdr `Option` shortcuts.
- `Ctrl+Option+arrow` is used for pane movement so plain `Option+left/right` remains available for word movement.

## Useful Commands

```bash
herdr                         # launch or attach default local session
herdr --session <name>         # use/create named session
herdr session list             # list sessions
herdr session attach <name>    # attach named session
herdr server stop              # stop server and panes
herdr server reload-config     # apply config changes
herdr --default-config         # print full default config
herdr update                   # update Herdr
herdr --remote <ssh-target>    # attach to remote Herdr server through SSH
```

CLI control surfaces:

```bash
herdr workspace list|create|focus|rename|close
herdr tab list|create|focus|rename|close
herdr pane list|split|focus|resize|zoom|rename|read|send-text|send-keys|close
herdr agent list|explain|start|attach|rename
herdr integration status
herdr integration install <agent>
```

## Common Workflow

1. Start Herdr from a project directory:
   ```bash
   herdr
   ```
2. Use one workspace per repo/task/investigation.
3. Use tabs for views such as `agents`, `logs`, `server`, `review`.
4. Use panes for real terminals: shells, servers, tests, agents.
5. Start agents normally inside panes (`pi`, `codex`, `claude`, etc.); Herdr detects supported agents.
6. Watch the sidebar for agent rollups: `blocked`, `working`, `done`, `idle`, `unknown`.
7. Detach with the configured detach binding or close the terminal; reattach with `herdr`.
8. Use `herdr server stop` only when you intend to terminate the session processes.

## Shared macOS Shortcut Preferences

When editing `~/.config/herdr/config.toml`, preserve the user's design:

```toml
[keys]
prefix = "ctrl+b"

new_workspace = "alt+n"
previous_workspace = "alt+shift+up"
next_workspace = "alt+shift+down"
workspace_picker = "alt+p"
rename_workspace = "alt+shift+r"
close_workspace = "alt+shift+w"

new_tab = "alt+t"
previous_tab = "alt+shift+left"
next_tab = "alt+shift+right"
rename_tab = "alt+r"
close_tab = "alt+w"

split_vertical = "alt+d"
split_horizontal = "alt+shift+d"
focus_pane_left = "ctrl+alt+left"
focus_pane_right = "ctrl+alt+right"
focus_pane_up = "ctrl+alt+up"
focus_pane_down = "ctrl+alt+down"
rename_pane = "ctrl+alt+r"

toggle_sidebar = "alt+b"
new_worktree = "alt+shift+g"
zoom = "ctrl+alt+enter"
```

After editing, run:

```bash
herdr server reload-config
```

## Troubleshooting Checklist

- Keybinding does nothing: check OS/terminal interception first, then Herdr config diagnostics via `herdr server reload-config`.
- Plain `alt` chords on macOS may be affected by terminal Option-key behavior. In WezTerm, check `send_composed_key_when_left_alt_is_pressed` / `send_composed_key_when_right_alt_is_pressed`.
- Agent state wrong: use `herdr agent explain <target>`.
- Config confusion: run `herdr --default-config` and compare to `~/.config/herdr/config.toml`.
- Remote clipboard/image behavior differs depending on whether Herdr is run inside SSH vs `herdr --remote`; local desktop clipboard bridging is for `herdr --remote`.

## Detailed Reference

Read `references/herdr-guide.md` for official-docs-derived details on concepts, keyboard model, configuration, sessions/restore, remote workflows, agents, and command reference.
