#!/usr/bin/env bash

set -euo pipefail

if pgrep -x kitty >/dev/null; then
    pkill -USR1 -x kitty
fi
