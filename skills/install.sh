#!/bin/sh
set -eu

if ! command -v npx >/dev/null 2>&1; then
  printf 'npx is required to install external skills.\n' >&2
  exit 1
fi

# tk usage instructions maintained alongside tasukura.
npx skills add mixidota2/tasukura \
  --global --agent codex --copy --yes --skill tk

printf 'tk skill installed. Pi reads the same skills through ~/.pi/agent/skills.\n'
