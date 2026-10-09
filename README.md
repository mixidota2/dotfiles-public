# dotfiles

Personal macOS configuration for zsh, cmux, WezTerm, Neovim, Herdr, Orca, Pi, Codex, tk, and local agent skills.

## Install

Clone the repository to a directory of your choice, then link the configuration files. For example:

```sh
git clone <repository-url> ~/dotfiles
cd ~/dotfiles
./install.sh
```

Existing files and symlinks are moved to a timestamped directory under `~/.dotfiles-backups` before links are created. If a backup path already exists, a numeric suffix preserves both copies. Preview changes first with:

```sh
./install.sh --dry-run
```

Install Homebrew dependencies and user-level CLI tools on a fresh machine with:

```sh
./install.sh --tools
```

Restore external skills separately:

```sh
./skills/install.sh
```

## Source of truth

Files in this repository are the source of truth. Paths such as `~/.config/wezterm/wezterm.lua` are symbolic links into this repository, so normal edits appear directly in `git diff`.

Runtime state and credentials are intentionally excluded. In particular, Codex configuration and authentication, Pi authentication, sessions, histories, caches, SQLite databases, Herdr sessions, and `~/.local/share/tk/tasks.db` are not managed here.

Keep employer-specific services, project paths, credentials, and one-off approval rules outside this repository. Configure them locally for each computer or in the relevant project. The macOS keybindings, editor preferences, and reusable tools are shared across computers.

New skill evaluation ledger records use skill-relative result directories and run-relative artifact paths. External result directories and out-of-scope artifacts are explicitly marked without saving their absolute paths; see [the evaluation path contract](skills-local/.codex/skills/create-validated-skill/references/evaluation-schema.md#ledger-paths). Historical records are left unchanged. Artifacts remain local and may not exist on another computer. Review free-text evidence and local raw artifacts for sensitive content before committing or sharing them; path normalization does not anonymize their contents.

This repository starts from a reviewed file snapshot with a fresh Git history. Previously installed local configuration is not modified or scrubbed.

## Packages

- `shell`: portable zsh/profile setup, mise activation, CLI completions, Micro as the default editor, and the Yazi directory-changing wrapper.
- `yazi`: shows dotfiles by default and uses the shell's Micro editor setting.
- `nvim`: LazyVim for repository-level code reading and editing, with Octo enabled for GitHub pull request reviews. The managed LazyExtras cover JSON, Markdown, Python, TOML, and Graphviz/DOT. Micro remains the default `$EDITOR`.
- `cmux`: file-managed preferences only; sessions and window geometry remain local.
- `wezterm`: terminal appearance and keybindings.
- `herdr`: keybindings only; logs, sockets, and sessions remain local.
- `orca`: `~/.orca/keybindings.json` only; other Orca settings, sessions, and credentials remain local. See [the macOS shortcut mapping](docs/orca-shortcuts.md).
- `pi`: global instructions, preferences, and custom extensions.
- `codex`: global `AGENTS.md` instructions and reusable approval rules. `~/.codex/config.toml`, including project trust and generated settings, remains local to each computer.
- `tk`: configuration only. The CLI is installed as a uv tool and its task database remains local.
- `skills-local`: locally maintained skills. The external tk skill is restored by `skills/install.sh`.

The Brewfile installs the managed CLI tools and terminal applications, including Neovim and the command-line dependencies used by LazyVim and Octo.

## Checks

Run the installer and Orca configuration regression tests without touching your real home directory:

```sh
python3 -m unittest discover -s tests -v
```

The installer tests use temporary homes, do not pass `--tools`, and check backups, symlinks, repeated runs, dry runs, and duplicate destinations. Evaluation-record tests require PyYAML and stub all model execution; they use temporary homes and never read Codex credentials. The evaluator's built-in checks can also run without model calls:

```sh
python3 skills-local/.codex/skills/create-validated-skill/scripts/run_eval.py --self-test
```
