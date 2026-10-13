#!/usr/bin/env bash

set -euo pipefail

FONT_PACKAGES=(
  fontconfig
  ttf-jetbrains-mono-nerd
  ttf-3270-nerd
  noto-fonts
  noto-fonts-cjk
  noto-fonts-emoji
)

PACKAGES=(
  "${FONT_PACKAGES[@]}"
  python
  git
  base-devel
  curl
  unzip
  tree-sitter-cli
  ripgrep
  eza
  starship
  fzf
  pandoc-cli
  hyprland
  hyprpaper
  hypridle
  hyprlock
  hyprlauncher
  thunar
  grim
  slurp
  wl-clipboard
  brightnessctl
  neovim
  waybar
  dunst
  kitty
  zellij
  playerctl
  wireplumber
  pavucontrol
  network-manager-applet
  wofi
)

echo "Installing SETUP Dependencies..."
if (( EUID == 0 )); then
  pacman -S --needed --noconfirm "${PACKAGES[@]}"
else
  sudo pacman -S --needed --noconfirm "${PACKAGES[@]}"
fi
fc-cache -f
echo "done"
