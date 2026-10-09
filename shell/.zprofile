# Homebrew locations for Apple Silicon and Intel Macs.
if [[ -x /opt/homebrew/bin/brew ]]; then
  eval "$(/opt/homebrew/bin/brew shellenv)"
elif [[ -x /usr/local/bin/brew ]]; then
  eval "$(/usr/local/bin/brew shellenv)"
fi

# User-local tools take precedence over system installations.
export PATH="$HOME/.local/bin:$PATH"

# Default terminal editor, also used by Yazi's text opener.
export EDITOR="micro"
export VISUAL="$EDITOR"
