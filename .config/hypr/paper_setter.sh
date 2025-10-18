#!/usr/bin/env bash
set -euo pipefail

# Config
DIR="${WALL_DIR:-$HOME/images_to_paper}"
LAST_FILE="${LAST_FILE:-$HOME/.cache/last_wallpaper}"
SWWW_ARGS=(--transition-type random --transition-duration 1.5 --transition-fps 144)

# Verbose toggle
DEBUG="${DEBUG:-0}"
log() { [ "$DEBUG" = "1" ] && echo "[debug]" "$@" >&2 || true; }

# Normalize DIR
DIR="$(realpath -m "$DIR")"
log "DIR=$DIR"

# Ensure directory exists
if [ ! -d "$DIR" ]; then
  notify-send "Wallpaper Picker" "Directory not found: $DIR"
  exit 1
fi

# Build list using case-insensitive extension matching without regex
shopt -s nullglob nocaseglob
pushd "$DIR" >/dev/null
IMAGES=()
for ext in jpg jpeg png webp bmp gif; do
  for f in *."$ext"; do
    [ -f "$f" ] && IMAGES+=("$DIR/$f")
  done
done
popd >/dev/null
shopt -u nullglob nocaseglob

# Fallback to recursive search if top-level empty
if [ "${#IMAGES[@]}" -eq 0 ]; then
  log "Top-level empty, scanning recursively"
  while IFS= read -r -d '' f; do
    IMAGES+=("$f")
  done < <(find "$DIR" -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.webp' -o -iname '*.bmp' -o -iname '*.gif' \) -print0 | sort -z)
fi

log "Found ${#IMAGES[@]} images"
if [ "${#IMAGES[@]}" -eq 0 ]; then
  notify-send "Wallpaper Picker" "No images found in $DIR"
  exit 0
fi

# Start previewer (imv) with socket
preview_socket="$(mktemp -u /tmp/imv-socket-XXXXXX)"
cleanup() { rm -f "$preview_socket"; }
trap cleanup EXIT

imv --socket="$preview_socket" --no-input -a "${IMAGES[0]}" >/dev/null 2>&1 &

imv_cmd() { imv-msg --socket "$preview_socket" "$@" >/dev/null 2>&1 || true; }

# Build wofi input: "basename<TAB>fullpath"
wofi_input="$(mktemp)"
for p in "${IMAGES[@]}"; do
  printf "%s\t%s\n" "$(basename "$p")" "$p"
done >"$wofi_input"

preview_then_choose() {
  local current="$1"
  imv_cmd open "$current"
  cat "$wofi_input" | \
    wofi --show dmenu --prompt "Set this wallpaper? (Enter=yes, Esc=cancel)" \
         --insensitive --cache-file /dev/null --hide-scroll --matching=fuzzy \
         --columns=1 --width 800 --height 200 \
         --select "$(basename "$current")"
}

choice_line="$(
  cat "$wofi_input" | \
    wofi --show dmenu --prompt "Pick wallpaper (Enter to preview)" \
         --insensitive --cache-file /dev/null --hide-scroll --matching=fuzzy \
         --columns=1 --width 800 --height 600
)"

[ -z "${choice_line:-}" ] && exit 0
choice_path="$(awk -F '\t' '{print $2}' <<<"$choice_line")"
[ -z "${choice_path:-}" ] && exit 0

confirmed_line="$(preview_then_choose "$choice_path")"
[ -z "${confirmed_line:-}" ] && exit 0
confirmed_path="$(awk -F '\t' '{print $2}' <<<"$confirmed_line")"
[ -z "${confirmed_path:-}" ] && exit 0

# Ensure swww is ready
if ! swww query >/dev/null 2>&1; then
  swww init || { notify-send "Wallpaper Picker" "Failed to init swww"; exit 1; }
fi

if swww img "$confirmed_path" "${SWWW_ARGS[@]}"; then
  mkdir -p "$(dirname "$LAST_FILE")"
  printf "%s" "$confirmed_path" >"$LAST_FILE"
  notify-send "Wallpaper Set" "$(basename "$confirmed_path")"
else
  notify-send "Wallpaper Picker" "Failed to set wallpaper"
fi
