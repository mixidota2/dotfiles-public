# User-local tools installed by uv and similar installers.
[[ -f "$HOME/.local/bin/env" ]] && source "$HOME/.local/bin/env"
export PATH="$HOME/.local/bin:$PATH"

# Development tool versions.
if command -v mise >/dev/null 2>&1; then
  eval "$(mise activate zsh)"
fi

# Google Cloud SDK installed outside Homebrew.
gcloud_dir="$HOME/google-cloud-sdk"
[[ -f "$gcloud_dir/path.zsh.inc" ]] && source "$gcloud_dir/path.zsh.inc"
[[ -f "$gcloud_dir/completion.zsh.inc" ]] && source "$gcloud_dir/completion.zsh.inc"
unset gcloud_dir

# uv completion.
if command -v uvx >/dev/null 2>&1; then
  eval "$(uvx --generate-shell-completion zsh)"
fi

# Change the current shell directory when leaving Yazi.
function y() {
  local tmp cwd
  tmp="$(mktemp -t 'yazi-cwd.XXXXXX')"
  yazi "$@" --cwd-file="$tmp"
  if cwd="$(command cat -- "$tmp")" && [[ -n "$cwd" && "$cwd" != "$PWD" ]]; then
    builtin cd -- "$cwd"
  fi
  rm -f -- "$tmp"
}

# Cortex CLI completion is generated locally by Cortex.
[[ -s "$HOME/.zsh/completions/cortex.zsh" ]] && source "$HOME/.zsh/completions/cortex.zsh"

# Render a Markdown file full-screen, including Mermaid diagrams.
function mdview() {
  if (( $# != 1 )); then
    print -u2 "Usage: mdview <markdown-file>"
    return 2
  fi

  if [[ ! -f "$1" ]]; then
    print -u2 "mdview: not a file: $1"
    return 2
  fi

  command nvim -n \
    -c 'lua require("md-render").preview.show_pager({ max_width = vim.o.columns })' \
    -- "$1"
}
