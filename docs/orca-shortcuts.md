# Orca shortcuts (macOS)

The baseline is the configuration already in this repository, not another app's current defaults:

- [`cmux.json`](../cmux/.config/cmux/cmux.json) explicitly assigns Cmd+Shift+Up/Down to workspace navigation and Cmd+Shift+Left/Right to tab navigation.
- [`Herdr config`](../herdr/.config/herdr/config.toml) describes its Option bindings as the cmux Cmd shortcuts mapped to Option. Orca keeps Cmd for these operations, rather than claiming Option keys used by terminal applications.
- Existing Orca bindings are preserved. The only added entries explicitly pin the supported workspace-delete and browser-tab actions described below.

`Mod` means Cmd on macOS. All overrides remain in `platforms.darwin`; Linux, Windows, and common overrides remain empty.

| Operation | Orca key | Supported action | Mapping |
| --- | --- | --- | --- |
| Previous / next workspace | Cmd+Shift+Up / Down | `worktree.navigateUp` / `worktree.navigateDown` | Existing cmux navigation; Herdr has the same keys with Option |
| Create workspace | Cmd+N; Cmd+Shift+N also retained | `workspace.create` | Herdr's Option+N translated to Cmd; existing Orca alias retained |
| Delete workspace | Cmd+Shift+Backspace | `workspace.delete` | Orca-specific exception: opens the workspace-deletion confirmation |
| Previous / next tab, all types | Cmd+Shift+Left / Right | `tab.previousAllTypes` / `tab.nextAllTypes` | Existing cmux navigation; existing Cmd+Shift+[ / ] aliases retained |
| Create terminal tab | Cmd+T | `tab.newTerminal` | Herdr's Option+T translated to Cmd |
| Close active tab | Cmd+W | `tab.close` | Herdr's Option+W translated to Cmd |
| Split terminal right / down | Cmd+D / Cmd+Shift+D | `terminal.splitRight` / `terminal.splitDown` | Herdr's Option+D / Option+Shift+D translated to Cmd |
| Open browser tab | Cmd+Shift+B | `tab.newBrowser` | No browser-opening binding is recorded in this repository's cmux or Herdr config; explicitly retain Orca's supported default |

## Deliberate differences

Orca's workspace deletion removes a worktree, so it is not equivalent to closing a cmux/Herdr workspace. The documented flow targets the workspace hovered in the sidebar and asks for confirmation. Review the target and deletion options before confirming. There is no separate non-destructive `workspace.close` action in the checked Orca keybinding registry.

Herdr uses Option+Shift+W to close a workspace. Orca already uses Cmd+Shift+W to close the active terminal pane. That existing binding is deliberately preserved instead of replacing a familiar pane-close shortcut with worktree deletion.

Existing Ctrl+1–9 tab selection and Cmd+Option+arrow pane cycling also remain unchanged. Orca exposes next/previous pane cycling, not Herdr's four directional focus actions; the arrows do not imply directional navigation in Orca.

## Install and existing settings

`./install.sh --dry-run` now includes `~/.orca/keybindings.json`. The normal installer links that one file. It does not install the Orca application or manage the rest of `~/.orca`.

If a local keybindings file or symlink already exists, the installer backs it up before linking the repository version. It does not merge local-only shortcuts into this file. Compare the dry-run output and your current file before installing if you have additional overrides. Existing backups are preserved using `.1`, `.2`, and subsequent suffixes when needed. Re-running against the correct symlink does nothing.

## Verification and sources

Verified against Orca's official docs and source at commit [`59b9bdeb`](https://github.com/stablyai/orca/tree/59b9bdeb901538a5e1e0cb731fd2f4a85148dff2):

- [Settings reference](https://www.onorca.dev/docs/settings): keybindings path and workspace-deletion confirmation.
- [Tabs and split layouts](https://www.onorca.dev/docs/model/tabs-panes-splits): tab navigation and split behavior.
- [Browser documentation](https://www.onorca.dev/docs/browser/overview): per-worktree browser tabs.
- [Action registry: workspace](https://github.com/stablyai/orca/blob/59b9bdeb901538a5e1e0cb731fd2f4a85148dff2/src/shared/keybindings/definitions-core-1.ts), [tabs/browser](https://github.com/stablyai/orca/blob/59b9bdeb901538a5e1e0cb731fd2f4a85148dff2/src/shared/keybindings/definitions-core-2.ts), and [terminal splits](https://github.com/stablyai/orca/blob/59b9bdeb901538a5e1e0cb731fd2f4a85148dff2/src/shared/keybindings/definitions-core-4.ts): supported action IDs.
- [File parser](https://github.com/stablyai/orca/blob/59b9bdeb901538a5e1e0cb731fd2f4a85148dff2/src/main/keybindings/keybinding-file-parser.ts): version 1, common/platform sections, binding validation, and conflict handling.

The repository's tests cover the maintained mapping and safe installation. During this change, the configuration was also checked with the official parser and effective-binding conflict detector, including inherited defaults. This is static validation; the installed Orca version and real macOS keyboard behavior still need an application-level check.
