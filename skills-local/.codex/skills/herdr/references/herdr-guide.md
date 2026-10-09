# Herdr Guide

This reference was prepared from the official Herdr documentation at `https://herdr.dev/docs/` and local CLI help (`herdr --help`, `herdr --default-config`).

## Design Philosophy

Herdr is a terminal workspace manager for AI coding agents. It keeps real terminal processes running and adds structure around them.

Core ideas:

- **Real terminals, not abstractions**: panes are actual terminal processes. Herdr renders output and sends input back to the process.
- **Persistent server model**: by default Herdr is a background server plus one or more clients. The server owns panes/processes; clients attach, detach, and render.
- **Agent-first visibility**: Herdr detects coding agents and rolls their state up to panes, tabs, and workspaces so you can see what needs attention without polling terminals manually.
- **Mouse-native, keyboard-optional**: Herdr can be operated with mouse clicks, split dragging, context menus, and drag-select copy. Keyboard is an optional layer.
- **Prefix-first defaults**: default keybindings use a tmux-like prefix to avoid stealing common shell/editor shortcuts.
- **Remote-friendly**: it works when run inside SSH like tmux, and also supports `herdr --remote <host>` as a local thin client to a remote server.

## Mental Model

### Session

A persistent Herdr server namespace. `herdr` attaches to the default session. Named sessions are separate runtime namespaces:

```bash
herdr session list
herdr session attach work
herdr --session work
```

Use workspaces first. Use named sessions only when you need separate panes, sockets, and persisted runtime state.

### Workspace

Top-level project container. Use one workspace per repo, task, or investigation.

A workspace owns tabs and panes. Agent state rolls up to the workspace row in the sidebar.

### Tab

A layout inside a workspace. Use tabs to separate views such as `agents`, `logs`, `server`, and `review`.

### Pane

A real terminal. Panes can be split right/down, renamed, read from CLI, sent input, and closed.

### Agent

A process Herdr recognizes inside a pane. Supported agents run normally as terminal processes, but Herdr can classify their state.

Agent states:

| State | Meaning |
|---|---|
| `blocked` | Agent needs input, approval, or a decision |
| `working` | Agent is actively running |
| `done` | Agent finished and has not been looked at yet |
| `idle` | Agent is finished/waiting and has been seen |
| `unknown` | Herdr cannot confidently classify state |

## Local Work

Start Herdr from the project directory:

```bash
herdr
```

Herdr starts or attaches to the local background session automatically. Run shells, servers, tests, and agents normally inside panes.

Detach the client; panes keep running. Reattach later:

```bash
herdr
```

Stop the entire session and panes:

```bash
herdr server stop
```

## Remote Work

### Run Herdr inside SSH

```bash
ssh you@server
herdr
```

This behaves like a terminal multiplexer. The Herdr server and panes run on the remote machine. Good for simple remote use and phone/tablet SSH clients.

### Local thin client to remote Herdr

```bash
herdr --remote workbox
herdr --remote ssh://you@server:2222
```

The local client connects over SSH, starts/attaches to a remote Herdr server, and streams the UI locally. Use this when you want remote sessions to feel local, including local desktop features such as image clipboard paste bridging.

Important distinction: if you SSH first and run `herdr` on the server, Herdr runs entirely on the server and cannot read your local desktop clipboard.

## Keyboard Model

Default prefix is `ctrl+b`. `prefix+c` means: press `ctrl+b`, release, then press `c`.

Why prefix exists: a terminal multiplexer sits between your terminal and programs inside it. Programs already use most keys. Prefix reserves one key so Herdr does not break shells/editors.

Show active bindings inside Herdr:

```text
prefix+?
```

Default common keys:

| Action | Default |
|---|---|
| New tab | `prefix+c` |
| Split right | `prefix+v` |
| Split down | `prefix+minus` |
| Move panes | `prefix+h/j/k/l` |
| Workspace navigation | `prefix+w` |
| New workspace | `prefix+shift+n` |
| Detach | `prefix+q` |
| Zoom pane | `prefix+z` |
| Close pane | `prefix+x` |
| Next/previous tab | `prefix+n` / `prefix+p` |
| Jump tab 1-9 | `prefix+1..9` |
| Rename tab | `prefix+shift+t` |
| Close tab | `prefix+shift+x` |
| Rename workspace | `prefix+shift+w` |
| Close workspace | `prefix+shift+d` |
| Goto picker | `prefix+g` |
| Toggle sidebar | `prefix+b` |

### Going Prefix-Free

Herdr supports direct bindings such as `ctrl+alt+n`. But direct chords must survive OS, outer terminal, and pane program layers.

Official guidance: `ctrl+alt` is the safest general family because it is mostly untouched by terminals and avoids macOS Option-key composition issues. Avoid chords already claimed by desktops/terminals, especially on Linux (`ctrl+alt+arrows`, `ctrl+alt+t`, `ctrl+alt+f1..f12`, etc.).

On macOS, Herdr config uses `alt` for the physical **Option** key. Plain Option chords may depend on terminal settings.

## Configuration

Config path:

```bash
~/.config/herdr/config.toml
```

Print defaults:

```bash
herdr --default-config
```

Reload running server after edits:

```bash
herdr server reload-config
```

Invalid values fall back to safe defaults and show warnings/diagnostics.

### Keybinding Syntax

Examples:

```toml
[keys]
prefix = "ctrl+b"
new_tab = "prefix+c"
next_tab = ["prefix+n", "ctrl+alt+]"]
focus_pane_left = "ctrl+alt+left"
switch_tab = "prefix+1..9"
```

Accepted strings include plain keys, modifiers (`ctrl`, `shift`, `alt`, `cmd`, `super`), special keys (`enter`, `tab`, `esc`, `left`, `right`, `up`, `down`), punctuation names (`minus`, `comma`, `ampersand`, `plus`, `backtick`), and ranges such as `1..9` for indexed jumps.

Avoid unmodified direct printable keys because they intercept typing. Plain keys are appropriate only inside navigate-mode-specific fields.

Optional actions unset by default include `previous_workspace`, `next_workspace`, `last_pane`, `open_worktree`, `remove_worktree`, `switch_workspace`, and `focus_agent`.

### Terminal Defaults

```toml
[terminal]
default_shell = ""
shell_mode = "auto"
new_cwd = "follow"
```

- `default_shell`: executable for new interactive panes. Empty means `$SHELL`, then `/bin/sh`.
- `shell_mode`: `auto`, `login`, or `non_login`. `auto` uses login shells on macOS.
- `new_cwd`: `follow`, `home`, `current`, or a fixed path.

### Worktrees

```toml
[worktrees]
directory = "~/.herdr/worktrees"
```

Herdr can create/open/delete Git worktree checkouts from workspace rows. Worktree children behave like normal workspaces. Deleting a worktree checkout uses `git worktree remove`; branches are not deleted.

## Session State and Restore

### Detach/Reattach

Processes keep running. Layout, recent screen, and agent conversation all remain live because the original processes never stopped.

### Server Restart

Original processes are gone. Herdr restores saved shape: workspaces, tabs, panes, cwd, layout, focus. Ordinary panes restart as new shells in saved directories.

### Pane Screen History

Optional, off by default because it may store secrets. Restores recent terminal contents after full server restart, not the old process.

```toml
[experimental]
pane_history = true
```

Stored near `session.json`; treat as terminal history.

### Native Agent Session Restore

Enabled by default. Some integrations report native session references so Herdr can resume agent conversations after server restart.

```toml
[session]
resume_agents_on_restore = true
```

Check integrations:

```bash
herdr integration status
herdr integration install <agent>
```

### Live Handoff

Experimental opt-in for updates or remote attach flows that replace a running server while trying to keep pane processes alive:

```bash
herdr update --handoff
herdr --remote workbox --handoff
```

## Agent Detection and Integrations

Herdr supports automatic detection for common coding agents. Unsupported agents still run normally; they just may not get rich state.

Detection sources include foreground process, screen manifests, terminal title/progress evidence, and optional integrations.

Install integrations for agents you use:

```bash
herdr integration install claude
herdr integration install codex
herdr integration install pi
herdr integration status
```

Use `HERDR_AGENT=<agent>` when wrappers/VMs hide the real process from `/proc`:

```bash
HERDR_AGENT=claude fence -- claude
```

Troubleshoot wrong state:

```bash
herdr agent explain <target>
herdr agent explain --file screen.txt --agent codex --json
```

Start an agent from CLI:

```bash
herdr agent start reviewer --cwd ~/project --split right -- pi
herdr agent start docs --workspace w1 --tab w1:t1 -- codex
```

Attach directly to one agent terminal:

```bash
herdr agent attach reviewer
herdr agent attach reviewer --takeover
```

Detach direct attach with `ctrl+b q`; send literal `ctrl+b` with `ctrl+b ctrl+b`.

## CLI Reference Essentials

Top-level:

```bash
herdr
herdr --session <name>
herdr --remote <ssh-target> [--session <name>]
herdr update [--handoff]
herdr channel set <stable|preview>
herdr server stop
herdr server reload-config
herdr config reset-keys
```

Workspace:

```bash
herdr workspace list
herdr workspace create [--cwd PATH] [--label TEXT] [--focus|--no-focus]
herdr workspace get <workspace_id>
herdr workspace focus <workspace_id>
herdr workspace rename <workspace_id> <label>
herdr workspace close <workspace_id>
```

Tab:

```bash
herdr tab list [--workspace <workspace_id>]
herdr tab create [--workspace <workspace_id>] [--cwd PATH] [--label TEXT] [--focus|--no-focus]
herdr tab get <tab_id>
herdr tab focus <tab_id>
herdr tab rename <tab_id> <label>
herdr tab close <tab_id>
```

Pane:

```bash
herdr pane list [--workspace <workspace_id>]
herdr pane current [--pane ID|--current]
herdr pane focus --direction left|right|up|down [--pane ID|--current]
herdr pane resize --direction left|right|up|down [--amount FLOAT] [--pane ID|--current]
herdr pane zoom [<pane_id>|--pane ID|--current] [--toggle|--on|--off]
herdr pane split [<pane_id>|--pane ID|--current] --direction right|down [--ratio FLOAT] [--cwd PATH] [--focus|--no-focus]
herdr pane rename <pane_id> <label>|--clear
herdr pane read <pane_id> [--source visible|recent|recent-unwrapped] [--lines N] [--format text|ansi]
herdr pane send-text <pane_id> <text>
herdr pane send-keys <pane_id> <key> [key ...]
herdr pane close <pane_id>
```

## Troubleshooting

### Key does nothing

1. Check local config and reload diagnostics:
   ```bash
   herdr server reload-config
   ```
2. Check whether the OS or outer terminal consumes the chord.
3. On macOS, plain Option may compose characters depending on terminal settings. Prefer `ctrl+alt` or adjust terminal config.
4. Compare with defaults:
   ```bash
   herdr --default-config
   ```

### Agent state wrong

```bash
herdr agent explain <target>
herdr integration status
```

### Remote clipboard mismatch

- `ssh server` then `herdr`: Herdr runs remotely and cannot read local desktop clipboard.
- `herdr --remote server`: local thin client can bridge local desktop features such as image clipboard paste.

### Need reset keybindings

```bash
herdr config reset-keys
herdr server reload-config
```

This backs up `config.toml`, removes custom key sections, and returns to built-in defaults.
