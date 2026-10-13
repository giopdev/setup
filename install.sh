#!/usr/bin/env bash

set -euo pipefail

if ! command -v python3 >/dev/null; then
  echo "Python 3.11 or newer is required. Install your distro's Python package first." >&2
  exit 1
fi

repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec python3 "$repo_dir/scripts/install.py" "$@"
