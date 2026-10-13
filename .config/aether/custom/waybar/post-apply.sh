#!/usr/bin/env bash

set -euo pipefail

if pgrep -x waybar >/dev/null; then
    pkill -USR2 -x waybar
fi
