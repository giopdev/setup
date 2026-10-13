import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".svg"}


def select_wallpaper(config_home, from_aether):
    saved = config_home / "hypr/current-wallpaper"
    if not from_aether and saved.is_file():
        return saved.resolve()
    backgrounds = config_home / "aether/theme/backgrounds"
    if not backgrounds.is_dir():
        return None
    images = sorted(path for path in backgrounds.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES)
    if not images:
        return None
    if shutil.which("aether"):
        try:
            result = subprocess.run(["aether", "status", "--json"], capture_output=True, text=True, timeout=5)
            status = json.loads(result.stdout) if result.returncode == 0 else {}
            selected = Path(status.get("wallpaper") or "")
            blurred = [path for path in images if re.fullmatch(re.escape(selected.stem) + r"-blurred-[0-9a-f]{8}\.jpg", path.name)]
            if len(blurred) == 1:
                return blurred[0]
            matching = backgrounds / selected.name
            if selected.name and matching in images:
                return matching
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
            pass
    if len(images) == 1:
        return images[0]
    raise ValueError("Multiple theme backgrounds found; open aether and apply the selected wallpaper to identify it.")


def save_wallpaper(config_home, wallpaper):
    target = config_home / "hypr/current-wallpaper"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink() and target.resolve() == wallpaper.resolve():
        return target
    if target.exists() and not target.is_symlink():
        raise ValueError(f"Refusing to overwrite an unmanaged file: {target}")
    temporary = target.with_name(f".current-wallpaper-{os.getpid()}")
    try:
        temporary.symlink_to(os.path.relpath(wallpaper, target.parent))
        temporary.replace(target)
    finally:
        if temporary.is_symlink():
            temporary.unlink()
    return target


def start_hyprpaper(config_home, state_home):
    if shutil.which("pgrep"):
        result = subprocess.run(["pgrep", "-u", str(os.getuid()), "-x", "hyprpaper"], capture_output=True)
        if result.returncode == 0:
            return
    if shutil.which("systemctl"):
        try:
            result = subprocess.run(["systemctl", "--user", "start", "hyprpaper.service"], capture_output=True, timeout=10)
            if result.returncode == 0:
                return
        except subprocess.TimeoutExpired:
            pass
    log = state_home / "setup/hyprpaper.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a") as stream:
        subprocess.Popen(
            ["hyprpaper", "--config", str(config_home / "hypr/hyprpaper.conf")],
            stdout=stream, stderr=stream, start_new_session=True,
        )


def apply_wallpaper(target):
    if "," in str(target):
        raise ValueError("hyprpaper IPC does not support commas in the config directory path")
    deadline = time.monotonic() + 5
    details = "hyprpaper did not become ready"
    while time.monotonic() < deadline:
        try:
            result = subprocess.run(
                ["hyprctl", "hyprpaper", "wallpaper", f",{target},cover"],
                capture_output=True, text=True, timeout=1,
            )
            if result.returncode == 0:
                return
            details = result.stderr.strip() or result.stdout.strip()
        except subprocess.TimeoutExpired:
            pass
        time.sleep(0.1)
    raise ValueError(f"Could not apply wallpaper: {details}")


def main():
    parser = argparse.ArgumentParser(description="Apply aether's wallpaper using hyprpaper and restore it at login.")
    parser.add_argument("--from-aether", action="store_true", help="Select the newly applied theme rather than the saved wallpaper")
    arguments = parser.parse_args()
    try:
        config_home = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config").resolve()
        state_home = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state").resolve()
        wallpaper = select_wallpaper(config_home, arguments.from_aether)
        if wallpaper is None:
            print("No aether wallpaper yet; apply a theme to initialize it.")
            return
        target = save_wallpaper(config_home, wallpaper)
        if not os.environ.get("WAYLAND_DISPLAY") or not os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
            print(f"Saved wallpaper for the next Hyprland login: {wallpaper}")
            return
        if not shutil.which("hyprpaper") or not shutil.which("hyprctl"):
            raise ValueError("Install hyprpaper and Hyprland with dependencies.sh first")
        start_hyprpaper(config_home, state_home)
        apply_wallpaper(target)
        print(f"Applied wallpaper: {wallpaper}")
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        print(f"Wallpaper update failed: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
