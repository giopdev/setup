#!/usr/bin/env bash

set -euo pipefail

if pgrep -x dunst >/dev/null; then
    config_home=${XDG_CONFIG_HOME:-$HOME/.config}
    shopt -s nullglob
    configs=("$config_home/dunst/dunstrc" "$config_home/dunst/dunstrc.d/"*.conf)
    dunstctl reload "${configs[@]}"
fi
