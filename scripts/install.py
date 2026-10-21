import argparse
import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

if sys.version_info < (3, 11):
    sys.exit("Python 3.11 or newer is required.")

import tomllib


REPO = Path(__file__).resolve().parents[1]
MODE_PATTERN = re.compile(r"(?:preferred|highres|highrr|[1-9]\d*x[1-9]\d*(?:@[1-9]\d*(?:\.\d+)?)?)")


def xdg_path(name, fallback):
    value = Path(os.environ.get(name) or fallback)
    if not value.is_absolute():
        raise ValueError(f"{name} must be an absolute path: {value}")
    value = value.resolve()
    if value == REPO or REPO in value.parents:
        raise ValueError(f"{name} cannot point inside this repository")
    return value


def ask(prompt, default):
    try:
        answer = input(f"{prompt} [{default}]: ").strip()
    except EOFError as error:
        raise ValueError("Monitor input required; use --monitor for unattended installation.") from error
    return answer or default


def validate_monitor(output, mode, position, scale):
    mode = mode.removesuffix("Hz")
    if not MODE_PATTERN.fullmatch(mode):
        raise ValueError(f"Invalid monitor mode: {mode}; use preferred or WIDTHxHEIGHT@HZ")
    if not re.fullmatch(r"auto(?:-(?:left|right|up|down))?|[-]?\d+x[-]?\d+", position):
        raise ValueError(f"Invalid monitor position: {position}; use auto or XxY")
    if scale != "auto":
        if not re.fullmatch(r"\d+(?:\.\d+)?", scale) or float(scale) <= 0:
            raise ValueError(f"Invalid monitor scale: {scale}; use auto or a positive number")
    if any(ord(character) < 32 for character in output):
        raise ValueError("Monitor names cannot contain control characters")
    return {"output": output, "mode": mode, "position": position, "scale": scale}


def detect_monitors():
    if not shutil.which("hyprctl"):
        return []
    try:
        result = subprocess.run(["hyprctl", "-j", "monitors", "all"], capture_output=True, text=True, timeout=5)
        monitors = json.loads(result.stdout) if result.returncode == 0 else []
        return monitors if isinstance(monitors, list) else []
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return []


def monitor_config(arguments, existing):
    if arguments.keep_monitors:
        if not existing.is_file():
            raise ValueError("--keep-monitors requires an existing hypr/monitors.lua")
        return None
    if arguments.monitor:
        monitors = [validate_monitor(*monitor) for monitor in arguments.monitor]
    elif arguments.dry_run:
        print("Monitor settings: installation will prompt (or use --monitor / --keep-monitors).")
        return None
    elif existing.is_file() and ask("Keep existing monitor settings? Y/n", "Y").lower() == "y":
        return None
    else:
        monitors = []
        detected = detect_monitors()
        for monitor in detected or [{}]:
            output = monitor.get("name")
            if output is None:
                output = ask("Monitor output (blank matches any monitor)", "")
            print(f"\nConfigure {output or 'any monitor'}")
            modes = list(dict.fromkeys(monitor.get("availableModes", [])))
            if modes:
                print("Available modes: " + ", ".join(mode.removesuffix("Hz") for mode in modes))
            default_mode = "preferred"
            if monitor.get("width") and monitor.get("height") and monitor.get("refreshRate"):
                default_mode = f"{monitor['width']}x{monitor['height']}@{monitor['refreshRate']:.6g}"
            mode = ask("Mode (or preferred / highres / highrr)", default_mode)
            position = ask("Position (auto or XxY)", "auto")
            scale = ask("Scale (auto or a positive number)", str(monitor.get("scale", "auto")))
            monitors.append(validate_monitor(output, mode, position, scale))
        if not detected:
            while ask("Add another monitor? y/N", "N").lower() == "y":
                monitors.append(validate_monitor(
                    ask("Monitor output", ""), ask("Mode", "preferred"),
                    ask("Position", "auto"), ask("Scale", "auto"),
                ))
    if len({monitor["output"] for monitor in monitors}) != len(monitors):
        raise ValueError("Each monitor output can only be configured once")
    return "\n".join(
        "hl.monitor({ " + ", ".join(f"{key} = {json.dumps(value, ensure_ascii=False)}" for key, value in monitor.items()) + " })"
        for monitor in monitors
    ) + "\n"


def load_colors(config_home):
    colors = json.loads((REPO / ".config/aether/fallback-colors.json").read_text())
    palette = config_home / "aether/theme/colors.toml"
    if palette.is_file():
        colors.update(tomllib.loads(palette.read_text()))
        for name, slot in (("black", 0), ("white", 7), ("bright_black", 8), ("bright_white", 15)):
            if f"color{slot}" in colors:
                colors[name] = colors[f"color{slot}"]
        print("Initializing generated colors from the current aether palette.")
    else:
        print("No aether palette yet; initializing fallback colors.")
    return colors


def render_template(content, colors):
    def replace(match):
        color = colors[match.group(1)]
        if not isinstance(color, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            raise ValueError(f"Invalid theme color: {match.group(1)}")
        return color.removeprefix("#") if match.group(2) else color
    return re.sub(r"\{(\w+)(\.strip)?\}", replace, content)


def operations(config_home, monitors):
    planned = [
        (Path.home() / ".bashrc", REPO / ".bashrc", None),
        (Path.home() / ".codex/AGENTS.md", REPO / ".codex/AGENTS.md", None),
        (Path.home() / ".claude/CLAUDE.md", REPO / ".codex/AGENTS.md", None),
    ]
    for relative in (
        "hypr/hyprpaper.conf", "hypr/apply-wallpaper.py",
        "waybar/config", "waybar/style.css", "waybar/updates.sh",
        "kitty/kitty.conf", "dunst/dunstrc", "zellij/config.kdl",
        "bash/fzf.sh",
        "pandoc/md-preview.css", "pandoc/mermaid.html",
        "nvim/init.lua", "nvim/nvim-pack-lock.json", "nvim/.stylua.toml",
    ):
        planned.append((config_home / relative, REPO / ".config" / relative, None))
    planned.append((config_home / "hypr/repo.lua", REPO / ".config/hypr/hyprland.lua", None))
    planned.append((config_home / "hypr/hyprland.lua", None, (REPO / ".config/hypr/loader.lua").read_text()))
    if monitors is not None:
        planned.append((config_home / "hypr/monitors.lua", None, monitors))
    colors = load_colors(config_home)
    for app in sorted((REPO / ".config/aether/custom").iterdir()):
        metadata = json.loads((app / "config.json").read_text())
        destination = metadata["destination"]
        if not destination.startswith("~/.config/"):
            raise ValueError(f"Unexpected template destination: {destination}")
        target = config_home / destination.removeprefix("~/.config/")
        generated = config_home / "aether/theme" / f"{app.name}-{metadata['template']}"
        rendered = render_template((app / metadata["template"]).read_text(), colors)
        planned.extend(((generated, None, rendered), (target, generated, None)))
        local_metadata = json.dumps({**metadata, "destination": str(target)}, indent=4) + "\n"
        planned.append((config_home / "aether/custom" / app.name / "config.json", None, local_metadata))
        for source in app.iterdir():
            if source.name != "config.json":
                planned.append((config_home / "aether/custom" / app.name / source.name, source, None))
    return planned


def preflight(planned, config_home):
    if config_home.exists() and not config_home.is_dir():
        raise ValueError(f"Expected a config directory: {config_home}")
    for target, source, content in planned:
        root = config_home if target.is_relative_to(config_home) else Path.home()
        for parent in target.parents:
            if parent == root:
                break
            if parent.is_symlink():
                raise ValueError(f"Refusing to write through directory symlink: {parent}. Use a real directory first.")
            if parent.exists() and not parent.is_dir():
                raise ValueError(f"Expected a directory: {parent}")
        if source is not None and not source.is_file() and not source.is_relative_to(config_home / "aether/theme"):
            raise ValueError(f"Missing source file: {source}")


def validate_hyprland(config_home, planned):
    if not shutil.which("Hyprland"):
        print("Hyprland not installed; skipping compositor validation.")
        return
    with tempfile.TemporaryDirectory(prefix="setup-verify-") as temporary:
        staging = Path(temporary)
        (staging / "hypr").mkdir()
        shutil.copyfile(REPO / ".config/hypr/loader.lua", staging / "hypr/hyprland.lua")
        shutil.copyfile(REPO / ".config/hypr/hyprland.lua", staging / "hypr/repo.lua")
        for name in ("monitors.lua", "aether-colors.lua"):
            target = config_home / "hypr" / name
            selected = next((item for item in planned if item[0] == target), None)
            content = None
            if selected:
                content = selected[2]
                if selected[1]:
                    content = next(item[2] for item in planned if item[0] == selected[1])
            elif target.is_file():
                content = target.read_text()
            if content is not None:
                (staging / "hypr" / name).write_text(content)
        for label in ("repository", "fallback"):
            if label == "fallback":
                (staging / "hypr/repo.lua").unlink()
            result = subprocess.run(
                ["Hyprland", "--verify-config", "-c", str(staging / "hypr/hyprland.lua")],
                env={**os.environ, "XDG_CONFIG_HOME": str(staging)}, capture_output=True, text=True, timeout=20,
            )
            if result.returncode or "config ok" not in result.stdout + result.stderr:
                raise ValueError(f"Hyprland {label} validation failed:\n" + result.stdout + result.stderr)
        print("Hyprland repository and fallback configurations validated before installation.")


class Installation:
    def __init__(self, config_home, state_home):
        self.config_home = config_home
        self.state_home = state_home
        self.backup = None
        self.changed = []
        self.created_directories = []

    def make_directory(self, directory):
        if not directory.exists():
            self.make_directory(directory.parent)
            directory.mkdir()
            self.created_directories.append(directory)

    def apply(self, target, source, content):
        if source is not None and target.is_symlink() and target.resolve() == source.resolve():
            return
        if content is not None and target.is_file() and not target.is_symlink() and target.read_text() == content:
            return
        saved = None
        if target.exists() or target.is_symlink():
            if self.backup is None:
                backups = self.state_home / "setup/backups"
                backups.mkdir(parents=True, exist_ok=True)
                prefix = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-")
                self.backup = Path(tempfile.mkdtemp(prefix=prefix, dir=backups))
            relative = target.relative_to(self.config_home) if target.is_relative_to(self.config_home) else Path("home") / target.relative_to(Path.home())
            saved = self.backup / relative
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(target), str(saved))
        self.changed.append((target, saved))
        self.make_directory(target.parent)
        if source is not None:
            target.symlink_to(os.path.relpath(source, target.parent))
        else:
            target.write_text(content)
        print(f"Installed {target}")

    def rollback(self):
        for target, saved in reversed(self.changed):
            if target.is_symlink() or target.is_file():
                target.unlink()
            if saved is not None:
                shutil.move(str(saved), str(target))
        for directory in reversed(self.created_directories):
            directory.rmdir()

    def finish(self):
        if self.backup:
            manifest = {"config_home": str(self.config_home), "home": str(Path.home()), "files": [
                {"destination": str(target), "backup": str(saved) if saved else None}
                for target, saved in self.changed
            ]}
            (self.backup / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
            print(f"Backups: {self.backup}")


def reload_session(config_home, state_home):
    if not os.environ.get("WAYLAND_DISPLAY"):
        print("No active Wayland session; configurations take effect at the next login.")
        return
    commands = []
    if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
        commands.append(["hyprctl", "reload"])
        commands.append(["python3", str(config_home / "hypr/apply-wallpaper.py"), "--from-aether"])
    if shutil.which("pgrep") and subprocess.run(["pgrep", "-x", "waybar"], capture_output=True).returncode == 0:
        commands.append(["bash", str(config_home / "aether/custom/waybar/post-apply.sh")])
    elif shutil.which("waybar"):
        started = False
        if shutil.which("systemctl"):
            try:
                result = subprocess.run(["systemctl", "--user", "start", "waybar.service"], check=False, timeout=15)
                started = result.returncode == 0
            except subprocess.TimeoutExpired:
                print("Warning: timed out starting the Waybar user service.", file=sys.stderr)
        if not started:
            log = state_home / "setup/waybar.log"
            log.parent.mkdir(parents=True, exist_ok=True)
            with log.open("a") as stream:
                subprocess.Popen(["waybar"], stdout=stream, stderr=stream, start_new_session=True)
    for app in ("dunst", "kitty"):
        commands.append(["bash", str(config_home / "aether/custom" / app / "post-apply.sh")])
    for command in commands:
        if not shutil.which(command[0]):
            print(f"Not installed; skipped: {command[0]}")
            continue
        try:
            result = subprocess.run(command, env={**os.environ, "XDG_CONFIG_HOME": str(config_home)}, check=False, timeout=15)
            if result.returncode:
                print(f"Warning: reload failed: {' '.join(command)}", file=sys.stderr)
        except (OSError, subprocess.TimeoutExpired) as error:
            print(f"Warning: reload failed: {error}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Install portable desktop, Neovim, and Bash dotfiles.")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without writing files or reloading applications")
    parser.add_argument("--no-reload", action="store_true", help="Install files without restarting or reloading the session")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--monitor", action="append", nargs=4, metavar=("OUTPUT", "MODE", "POSITION", "SCALE"), help="Configure one monitor; repeat for multiple outputs")
    selection.add_argument("--keep-monitors", action="store_true", help="Preserve existing machine-local monitor settings")
    arguments = parser.parse_args()
    if os.geteuid() == 0:
        parser.error("Run this installer as your normal user, not with sudo.")
    installation = None
    try:
        config_home = xdg_path("XDG_CONFIG_HOME", str(Path.home() / ".config"))
        state_home = xdg_path("XDG_STATE_HOME", str(Path.home() / ".local/state"))
        for directory in (state_home / "setup", state_home / "setup/backups"):
            if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
                raise ValueError(f"Expected a real state directory: {directory}")
        monitors = monitor_config(arguments, config_home / "hypr/monitors.lua")
        planned = operations(config_home, monitors)
        preflight(planned, config_home)
        if arguments.dry_run:
            for target, source, content in planned:
                print(f"{'Link' if source else 'Write'} {target}" + (f" -> {source}" if source else ""))
            return
        validate_hyprland(config_home, planned)
        installation = Installation(config_home, state_home)
        for operation in planned:
            installation.apply(*operation)
        installation.finish()
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired, KeyboardInterrupt) as error:
        if installation:
            installation.rollback()
        print(f"Installation cancelled: {error}", file=sys.stderr)
        sys.exit(1)
    if not arguments.no_reload:
        reload_session(config_home, state_home)
    print("Installation complete. Linked configs track repository edits; Hyprland uses defaults if the checkout is removed.")


if __name__ == "__main__":
    main()
