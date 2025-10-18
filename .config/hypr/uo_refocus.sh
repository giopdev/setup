#!/bin/bash

sleep .05
# Get the current workspace ID (just the number)
ws=$(hyprctl activeworkspace | awk '/workspace ID/ {print $3}')

# Check for a UO window in the current workspace
if hyprctl clients | awk -v ws="$ws" '
  $1 == "Window" { inwin=1; title=""; wspace="" }
  inwin && $1 == "title:" { title=substr($0, index($0,$2)) }
  inwin && $1 == "workspace:" { wspace=$2 }
  inwin && title ~ /^UO/ && wspace == ws { found=1 }
  /^$/ { inwin=0 }
  END { exit !found }
'; then
    dunstify found --timeout=100
    hyprctl dispatch cyclenext
    hyprctl dispatch cyclenext
fi
