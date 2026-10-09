#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
dry_run=false
install_tools=false

usage() {
  cat <<'EOF'
Usage: ./install.sh [--dry-run] [--tools]

  --dry-run  Print filesystem changes without applying them.
  --tools    Install Homebrew dependencies and tk as a uv tool when missing.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run) dry_run=true ;;
    --tools) install_tools=true ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'Unknown option: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

timestamp=$(date '+%Y%m%d-%H%M%S')
backup_root=${DOTFILES_BACKUP_DIR:-"$HOME/.dotfiles-backups/$timestamp"}

run() {
  if [ "$dry_run" = true ]; then
    printf '+'
    printf ' %s' "$@"
    printf '\n'
  else
    "$@"
  fi
}

link_file() {
  source=$1
  relative=${source#"$repo_dir/"}
  relative=${relative#*/}
  destination=$HOME/$relative

  if [ -L "$destination" ] && [ "$(readlink "$destination")" = "$source" ]; then
    printf 'linked  %s\n' "$destination"
    return
  fi

  if [ -e "$destination" ] || [ -L "$destination" ]; then
    backup=$backup_root/$relative
    # A repeated run (or a fixed backup root) must not replace an earlier backup.
    backup_suffix=0
    while [ -e "$backup" ] || [ -L "$backup" ]; do
      backup_suffix=$((backup_suffix + 1))
      backup=$backup_root/$relative.$backup_suffix
    done
    printf 'backup  %s -> %s\n' "$destination" "$backup"
    run mkdir -p "$(dirname "$backup")"
    run mv "$destination" "$backup"
  fi

  printf 'link    %s -> %s\n' "$destination" "$source"
  run mkdir -p "$(dirname "$destination")"
  run ln -s "$source" "$destination"
}

link_package() {
  package=$1
  find "$repo_dir/$package" -type f -print | while IFS= read -r source; do
    link_file "$source"
  done
}

install_user_tools() {
  if ! command -v brew >/dev/null 2>&1; then
    printf 'Homebrew is required to install Brewfile dependencies.\n' >&2
    exit 1
  fi
  run brew bundle --file "$repo_dir/Brewfile"

  if ! command -v uv >/dev/null 2>&1; then
    printf 'uv was not found after brew bundle.\n' >&2
    exit 1
  fi

  if command -v tk >/dev/null 2>&1; then
    printf 'tool    tk is already installed at %s\n' "$(command -v tk)"
  else
    run uv tool install git+https://github.com/mixidota2/tasukura.git
  fi
}

for package in shell cmux wezterm yazi nvim herdr orca pi codex tk skills-local; do
  link_package "$package"
done

# Pi and Codex share one skill installation.
pi_skills=$HOME/.pi/agent/skills
codex_skills=$HOME/.codex/skills
if [ ! -e "$pi_skills" ] && [ ! -L "$pi_skills" ]; then
  printf 'link    %s -> %s\n' "$pi_skills" "$codex_skills"
  run mkdir -p "$(dirname "$pi_skills")"
  run ln -s "$codex_skills" "$pi_skills"
fi

if [ "$install_tools" = true ]; then
  install_user_tools
fi

printf 'Done. Restart applications or reload their configuration.\n'
