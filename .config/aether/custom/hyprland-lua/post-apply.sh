#!/usr/bin/env bash

set -euo pipefail

if [[ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]]; then
    hyprctl reload
fi

config_home=${XDG_CONFIG_HOME:-$HOME/.config}
python3 "$config_home/hypr/apply-wallpaper.py" --from-aether
