#!/usr/bin/env bash
# Prints Waybar JSON describing pending repository and AUR (Arch User Repository) updates.
# Prints nothing below the threshold, which hides the module.

minimum_updates_to_show=10

count_lines() { grep -c . || true; }

# checkupdates (pacman-contrib) syncs a temporary database copy, leaving the system database untouched.
repository_update_count=$(checkupdates 2>/dev/null | count_lines)
aur_update_count=0
if command -v yay >/dev/null; then
  aur_update_count=$(yay -Qua 2>/dev/null | count_lines)
fi
total_update_count=$((repository_update_count + aur_update_count))

if ((total_update_count >= minimum_updates_to_show)); then
  printf '{"text": "󰏗 %d", "tooltip": "%d repository · %d AUR updates"}\n' \
    "$total_update_count" "$repository_update_count" "$aur_update_count"
fi
