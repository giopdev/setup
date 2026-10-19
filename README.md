<img width="1036" height="380" alt="ascii-art-text" src="https://github.com/user-attachments/assets/449594aa-1c4d-4256-b455-4732593df60e" />

Dotfiles for an Arch Linux desktop using Hyprland, Waybar, Kitty, Zellij,
Bash, Dunst, and Neovim, with aether integration for desktop colors and wallpapers.

## Install

With Git and sudo installed, run as your normal user:

```sh
git clone https://github.com/giopdev/setup.git "$HOME/setup" && cd "$HOME/setup" && ./dependencies.sh && ./install.sh
```

The installer symlinks configs to the checkout, backs up existing files, and asks
for monitor settings. Edit the checkout to update your settings. Removing it
disables these custom configs; a small local loader keeps Hyprland usable by
falling back to its system defaults (or a minimal desktop if none are available).
Install aether separately to manage themes and wallpapers.

## Workspace bar visibility

**Super+B** toggles Waybar. When hidden, switching workspaces with **Super+0–9**,
**Super+scroll**, or **Super+Tab** reveals it until Super is released. A visible
bar stays visible; **Super+B** during a temporary reveal keeps it open.
This uses [Hyprland release bindings](https://wiki.hypr.land/Configuring/Binds/#bind-flags)
and [Waybar's visibility signal](https://man.archlinux.org/man/waybar.5.en#SIGNALS).
