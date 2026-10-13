# Repository Guide

Arch Linux dotfiles for Hyprland, Waybar, Kitty, Zellij, Bash, Dunst, Neovim,
and Pandoc, with aether-managed desktop colors and wallpapers.

- Store app configs under `.config/<app>/` and home-directory dotfiles at the repo root.
- Add managed files to `operations()` in `scripts/install.py` and packages to `dependencies.sh`.
- Use file-level symlinks, portable paths, and the installer's existing backup behavior.
- Keep generated theme files and machine-specific monitor settings outside the repo.
- Put aether templates and apply hooks under `.config/aether/custom/<app>/`.
- Preserve the independent Hyprland loader and its fallback when the checkout is missing.
- Keep changes focused, configs minimal, and documentation brief and self-contained.
- Validate changed configs with targeted checks; use `./install.sh --dry-run` to preview installation.
- Do not commit or push unless requested.
