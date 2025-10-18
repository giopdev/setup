#!/usr/bin/env bash

PACKAGES=(
  adobe-source-code-pro-fonts
  adwaita-fonts
  cantarell-fonts
  fontconfig
  gnu-free-fonts
  gsfonts
  lib32-fontconfig
  libfontenc
  libxfont2
  noto-fonts
  noto-fonts-cjk
  noto-fonts-emoji
  powerline-fonts
  python-fonttools
  sdl2_ttf
  ttf-carlito
  ttf-dejavu
  ttf-jetbrains-mono
  ttf-jetbrains-mono-nerd
  ttf-liberation
  ttf-nerd-fonts-symbols-common
  ttf-nerd-fonts-symbols-mono
  woff2-font-awesome
  xorg-fonts-encodings
  python3
  neovim
  swww
  waybar
  dunst
  kitty
  wofi
  python-tkinter
  python-pillow
)

echo "Updating System..."
yay --noconfirm

echo "Installing SETUP Dependencies..."
sudo pacman -S --needed --noconfirm "${PACKAGES[@]}"
echo "done"
