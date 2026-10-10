#!/bin/sh
set -eu

if ! command -v npx >/dev/null 2>&1; then
  printf 'npx is required to install external skills.\n' >&2
  exit 1
fi

# tk usage instructions live in the standalone skills repository.
npx skills add mixidota2/tasukura-skills \
  --global --agent codex --copy --yes --skill tk

printf 'tk skill installed.\n'
