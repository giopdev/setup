#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, Future

import tkinter as tk
from PIL import Image, ImageTk, ImageSequence

# Theme
COL_BG = "#1f1f1f"
COL_FRAME = "#1f1f1f"
COL_HOVER = "#2b2b2b"
COL_OVERLAY_BG = "#1f1f1f"
COL_PREVIEW_BG = "#3a3a3a"

# Config
WALL_DIR = os.environ.get("WALL_DIR", str(Path.home() / "images_to_paper"))
LAST_FILE = os.environ.get(
    "LAST_FILE", str(Path.home() / ".cache" / "last_wallpaper")
)
SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
THUMB_SIZE: Tuple[int, int] = (360, 203)
COLUMNS = int(os.environ.get("COLUMNS", "4"))
SWWW_ARGS = [
    "--transition-type",
    os.environ.get("SWWW_TRANSITION", "random"),
    "--transition-duration",
    os.environ.get("SWWW_DURATION", "1.5"),
    "--transition-fps",
    os.environ.get("SWWW_FPS", "144"),
]

RESAMPLE = Image.BILINEAR

# Threading
MAX_WORKERS = 4
# Dedicated background prefetch worker for animations
PREFETCH_WORKERS = 6


def find_images(dir_path: Path) -> List[Path]:
    if not dir_path.exists():
        return []
    out: List[Path] = []
    for p in sorted(dir_path.rglob("*")):
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXT:
            out.append(p)
    return out


def _resize_cover_16x9(im: Image.Image, size: tuple[int, int]) -> Image.Image:
    # Scale to fill and center-crop to exactly the requested size, preserving aspect
    target_w, target_h = size
    im2 = im.copy()
    if im2.mode not in ("RGB", "RGBA"):
        im2 = im2.convert("RGB")

    src_w, src_h = im2.size
    # Compute scale to cover the target box
    scale = max(target_w / src_w, target_h / src_h)
    new_w, new_h = int(round(src_w * scale)), int(round(src_h * scale))
    im2 = im2.resize((new_w, new_h), RESAMPLE)

    # Center-crop to target size
    left = max(0, (new_w - target_w) // 2)
    top = max(0, (new_h - target_h) // 2)
    im2 = im2.crop((left, top, left + target_w, top + target_h))

    # If RGBA, composite onto a solid background to avoid Tk transparency issues
    if im2.mode == "RGBA":
        bg = Image.new("RGB", (target_w, target_h), (43, 43, 43))
        bg.paste(im2, (0, 0), im2)
        return bg
    return im2


def build_static_thumb(path: Path, size: tuple[int, int]) -> ImageTk.PhotoImage:
    try:
        im = Image.open(path)
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGB")
        frame = _resize_cover_16x9(im, size)
    except Exception:
        frame = Image.new("RGB", size, (70, 70, 70))
    return ImageTk.PhotoImage(frame)


def load_animation_frames(
    path: Path, size: tuple[int, int]
) -> tuple[list[ImageTk.PhotoImage], list[int]]:
    try:
        im = Image.open(path)
        is_animated = getattr(im, "is_animated", False)
        n = getattr(im, "n_frames", 1)
        if not is_animated or n <= 1:
            frame = build_static_thumb(path, size)
            return [frame], [1000]
        frames: list[ImageTk.PhotoImage] = []
        durs: list[int] = []
        for frame in ImageSequence.Iterator(im):
            if frame.mode not in ("RGB", "RGBA"):
                frame = frame.convert("RGBA")
            dur = frame.info.get("duration", im.info.get("duration", 100))
            if not isinstance(dur, int) or dur <= 0:
                dur = 100
            framed = _resize_cover_16x9(frame, size)
            frames.append(ImageTk.PhotoImage(framed))
            durs.append(int(dur))
        if not frames:
            frame = build_static_thumb(path, size)
            return [frame], [1000]
        return frames, durs
    except Exception:
        frame = build_static_thumb(path, size)
        return [frame], [1000]


def ensure_swww_ready() -> bool:
    try:
        subprocess.run(
            ["swww", "query"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except Exception:
        try:
            subprocess.run(["swww", "init"], check=True)
            return True
        except subprocess.CalledProcessError:
            return False


def set_wallpaper(path: Path) -> bool:
    if not ensure_swww_ready():
        return False
    cmd = ["swww", "img", str(path), *SWWW_ARGS]
    try:
        subprocess.run(cmd, check=True)
        Path(LAST_FILE).parent.mkdir(parents=True, exist_ok=True)
        Path(LAST_FILE).write_text(str(path))
        return True
    except subprocess.CalledProcessError:
        return False


class TileAnim:
    def __init__(self, label: tk.Label):
        self.label = label
        self.frames: list[ImageTk.PhotoImage] = []
        self.durations: list[int] = []
        self.idx = 0
        self.job: Optional[str] = None
        self.active = False

    def set_frames(
        self, frames: list[ImageTk.PhotoImage], durations: list[int]
    ):
        self.frames = frames
        self.durations = durations
        self.idx = 0

    def start(self):
        if not self.frames:
            return
        self.active = True
        self._tick()

    def stop(self):
        self.active = False
        if self.job is not None:
            try:
                self.label.after_cancel(self.job)
            except Exception:
                pass
            self.job = None

    def _tick(self):
        if not self.active or not self.frames:
            return
        self.label.configure(image=self.frames[self.idx])
        delay = self.durations[self.idx] if self.durations else 100
        self.idx = (self.idx + 1) % len(self.frames)
        self.job = self.label.after(delay, self._tick)


class PreviewAnim:
    def __init__(self, label: tk.Label):
        self.label = label
        self.frames: list[ImageTk.PhotoImage] = []
        self.durations: list[int] = []
        self.idx = 0
        self.job: Optional[str] = None
        self.active = False

    def set_frames(
        self, frames: list[ImageTk.PhotoImage], durations: list[int]
    ):
        self.frames = frames
        self.durations = durations
        self.idx = 0

    def start(self):
        if not self.frames:
            return
        self.active = True
        self._tick()

    def stop(self):
        self.active = False
        if self.job is not None:
            try:
                self.label.after_cancel(self.job)
            except Exception:
                pass
            self.job = None

    def _tick(self):
        if not self.active or not self.frames:
            return
        self.label.configure(image=self.frames[self.idx])
        delay = self.durations[self.idx] if self.durations else 100
        self.idx = (self.idx + 1) % len(self.frames)
        self.job = self.label.after(delay, self._tick)


class PickerApp:
    def __init__(self, root: tk.Tk, files: List[Path]):
        self.root = root
        self.root.title("Wallpaper Picker")
        self.root.geometry("1680x1050")
        self.root.configure(bg=COL_BG)

        self.executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
        self.prefetch_executor = ThreadPoolExecutor(
            max_workers=PREFETCH_WORKERS)

        # Canvas (no visible scrollbar)
        self.canvas = tk.Canvas(
            root, highlightthickness=0, bg=COL_BG, bd=0, relief="flat"
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        self._bind_scrolling()

        # Grid frame
        self.grid_frame = tk.Frame(
            self.canvas, bg=COL_BG, bd=0, highlightthickness=0)
        self.frame_id = self.canvas.create_window(
            (0, 0), window=self.grid_frame, anchor="nw")

        # Overlay preview container (initially hidden)
        self.overlay = tk.Frame(
            self.canvas, bg=COL_OVERLAY_BG, bd=0, highlightthickness=0)
        self.overlay_id = self.canvas.create_window(
            (0, 0), window=self.overlay, anchor="nw", state="hidden")

        # Inside overlay: centered preview box
        self.preview_wrap = tk.Frame(
            self.overlay, bg=COL_PREVIEW_BG, bd=0, highlightthickness=0)
        self.preview_wrap.place(relx=0.5, rely=0.5, anchor="center")
        self.preview_label = tk.Label(
            self.preview_wrap, bg=COL_PREVIEW_BG, bd=0)
        self.preview_label.pack()
        self.preview_anim = PreviewAnim(self.preview_label)
        self.preview_loading_future: Optional[Future] = None

        # Track current preview state to avoid race conditions
        self.current_preview_path: Optional[Path] = None
        self.current_preview_token: int = 0  # increment each preview open

        # Close overlay on Esc or click/right-click anywhere on overlay/preview
        root.bind("<Escape>", self._esc_handler)
        for w in (self.overlay, self.preview_wrap, self.preview_label):
            w.bind("<Button-3>", lambda e: self.hide_preview())
            w.bind("<Button-1>", lambda e: self.hide_preview())

        # Consume scroll events while overlay is visible (lock scrolling)
        for w in (self.overlay, self.preview_wrap, self.preview_label):
            w.bind("<MouseWheel>", lambda e: "break")
            w.bind("<Button-4>", lambda e: "break")
            w.bind("<Button-5>", lambda e: "break")

        self.files = files
        self.thumb_cache: dict[Path, ImageTk.PhotoImage] = {}
        self.anim_labels: list[tk.Label] = []

        # Cache for animated frames: key = (path, size_tuple)
        self.anim_cache: dict[
            tuple[Path, tuple[int, int]],
            tuple[list[ImageTk.PhotoImage], list[int]],
        ] = {}

        self.populate()
        self._start_background_prefetch()

        # Pause/resume animations with focus
        root.bind("<FocusOut>", self.pause_all)
        root.bind("<FocusIn>", self.resume_all)

        # Shutdown threads on close
        root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _esc_handler(self, _e):
        if self.is_preview_visible():
            self.hide_preview()
        else:
            self._on_close()

    def _on_close(self):
        try:
            if self.preview_loading_future:
                self.preview_loading_future.cancel()
        except Exception:
            pass
        for ex in (self.executor, self.prefetch_executor):
            try:
                ex.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass
        self.root.destroy()

    def _bind_scrolling(self):
        # Rebind canvas/global scrolling
        self.canvas.bind_all("<MouseWheel>", self.on_wheel)
        self.canvas.bind_all(
            "<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind_all(
            "<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))

    def _unbind_scrolling(self):
        # Remove canvas/global scrolling while overlay is visible
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _visible_region(self) -> tuple[int, int, int, int]:
        x0 = int(self.canvas.canvasx(0))
        y0 = int(self.canvas.canvasy(0))
        x1 = int(self.canvas.canvasx(self.canvas.winfo_width()))
        y1 = int(self.canvas.canvasy(self.canvas.winfo_height()))
        return x0, y0, x1, y1

    def _position_overlay_to_view(self):
        x0, y0, x1, y1 = self._visible_region()
        w = max(1, x1 - x0)
        h = max(1, y1 - y0)
        self.canvas.itemconfig(self.overlay_id, width=w, height=h)
        self.canvas.coords(self.overlay_id, x0, y0)
        margin = 40
        max_w = max(100, w - 2 * margin)
        max_h = max(100, h - 2 * margin)
        self.preview_wrap.configure(width=max_w, height=max_h)

    def on_canvas_configure(self, _event):
        self.canvas.itemconfig(self.frame_id, width=self.canvas.winfo_width())
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        if self.is_preview_visible():
            self._position_overlay_to_view()

    def on_wheel(self, event):
        if self.is_preview_visible():
            return
        delta = -1 if event.delta < 0 else 1
        self.canvas.yview_scroll(-int(delta), "units")

    def pause_all(self, _e=None):
        for lbl in self.anim_labels:
            anim: TileAnim = getattr(lbl, "_anim", None)
            if anim:
                anim.stop()

    def resume_all(self, _e=None):
        for lbl in self.anim_labels:
            anim: TileAnim = getattr(lbl, "_anim", None)
            if anim:
                anim.start()

    def populate(self):
        for w in self.grid_frame.winfo_children():
            w.destroy()
        self.anim_labels.clear()

        for idx, p in enumerate(self.files):
            r = idx // COLUMNS
            c = idx % COLUMNS

            card = tk.Frame(self.grid_frame, bg=COL_FRAME,
                            bd=0, highlightthickness=0)
            card.grid(row=r, column=c, padx=10, pady=10, sticky="nsew")

            inner = tk.Frame(card, bg=COL_BG, bd=0, highlightthickness=0)
            inner.pack(padx=1, pady=1)

            img_lbl = tk.Label(inner, bg=COL_BG, bd=0, cursor="hand2")
            img_lbl.pack()

            if p not in self.thumb_cache:
                self.thumb_cache[p] = build_static_thumb(p, THUMB_SIZE)
            img_lbl.configure(image=self.thumb_cache[p])

            # Right-click: preview overlay
            img_lbl.bind("<Button-3>", lambda _e, fp=p: self.show_preview(fp))

            # Animated load in background
            if p.suffix.lower() in (".gif", ".webp"):
                anim = TileAnim(img_lbl)
                img_lbl._anim = anim
                self.anim_labels.append(img_lbl)

                key = (p, THUMB_SIZE)
                if key in self.anim_cache:
                    frames, durs = self.anim_cache[key]
                    anim.set_frames(frames, durs)
                    anim.start()
                else:
                    def done_cb(fut: Future, lbl=img_lbl, a=anim, path=p, k=key):
                        try:
                            frames, durs = fut.result()
                        except Exception:
                            frames, durs = [self.thumb_cache[path]], [1000]

                        def apply_frames():
                            if not lbl.winfo_exists():
                                return
                            a.set_frames(frames, durs)
                            a.start()
                            self.anim_cache[k] = (frames, durs)

                        lbl.after(0, apply_frames)

                    fut = self.executor.submit(
                        load_animation_frames, p, THUMB_SIZE)
                    fut.add_done_callback(done_cb)
            else:
                img_lbl._anim = None

            def on_destroy(_e, lbl=img_lbl):
                a: TileAnim = getattr(lbl, "_anim", None)
                if a:
                    a.stop()

            img_lbl.bind("<Destroy>", on_destroy)

            img_lbl.bind("<Enter>", lambda _e,
                         w=card: w.configure(bg=COL_HOVER))
            img_lbl.bind("<Leave>", lambda _e,
                         w=card: w.configure(bg=COL_FRAME))

            def on_click(_e=None, fp=p):
                set_wallpaper(fp)
                self._on_close()

            img_lbl.bind("<Button-1>", on_click)

        for cc in range(COLUMNS):
            self.grid_frame.grid_columnconfigure(cc, weight=1)

        self.root.after(0, lambda: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))

    # Overlay preview
    def is_preview_visible(self) -> bool:
        return self.canvas.itemcget(self.overlay_id, "state") != "hidden"

    def show_preview(self, path: Path):
        # Show overlay at current viewport
        self.canvas.itemconfigure(self.overlay_id, state="normal")
        # Disable global/canvas scrolling while preview is open
        self._unbind_scrolling()
        self._position_overlay_to_view()

        # Track current preview and token
        self.current_preview_path = path
        self.current_preview_token += 1
        token = self.current_preview_token

        # Determine target preview size (within margins)
        w = int(self.canvas.itemcget(self.overlay_id, "width"))
        h = int(self.canvas.itemcget(self.overlay_id, "height"))
        margin = 40
        box_w = max(100, w - 2 * margin)
        box_h = max(100, h - 2 * margin)

        # Stop any prior preview animation and pending jobs
        self.preview_anim.stop()
        if self.preview_loading_future:
            try:
                self.preview_loading_future.cancel()
            except Exception:
                pass
            self.preview_loading_future = None

        # 1) Show static preview immediately (cover + center-crop)
        try:
            im = Image.open(path)
            if im.mode not in ("RGB", "RGBA"):
                im = im.convert("RGB")
            im = _resize_cover_16x9(im, (box_w, box_h))
        except Exception:
            im = Image.new("RGB", (box_w, box_h), COL_PREVIEW_BG)
        static_photo = ImageTk.PhotoImage(im)
        self.preview_label.configure(image=static_photo)
        self.preview_label.image = static_photo

        # 2) If animated, load frames in background and replace (cover) with cache
        if path.suffix.lower() in (".gif", ".webp"):
            key = (path, (box_w, box_h))
            if key in self.anim_cache:
                # Only apply if still the same preview request
                if self.is_preview_visible() and token == self.current_preview_token:
                    frames, durs = self.anim_cache[key]
                    self.preview_anim.set_frames(frames, durs)
                    self.preview_anim.start()
            else:
                fut = self.executor.submit(
                    load_animation_frames, path, (box_w, box_h))
                self.preview_loading_future = fut

                def done_cb(f: Future, k=key, expected_token=token, expected_path=path):
                    try:
                        frames, durs = f.result()
                    except Exception:
                        frames, durs = [], []

                    def apply():
                        # Abort if overlay not visible, or token/path mismatch (stale)
                        if (
                            not self.is_preview_visible()
                            or expected_token != self.current_preview_token
                            or self.current_preview_path != expected_path
                            or not frames
                        ):
                            return
                        self.preview_anim.set_frames(frames, durs)
                        self.preview_anim.start()
                        self.anim_cache[k] = (frames, durs)

                    self.preview_label.after(0, apply)

                fut.add_done_callback(done_cb)

    def hide_preview(self):
        self.preview_anim.stop()
        if self.preview_loading_future:
            try:
                self.preview_loading_future.cancel()
            except Exception:
                pass
            self.preview_loading_future = None
        # Clear current preview tracking
        self.current_preview_path = None
        self.current_preview_token += 1  # invalidate any in-flight callbacks
        # Re-enable global/canvas scrolling
        self._bind_scrolling()
        self.canvas.itemconfigure(self.overlay_id, state="hidden")
        self.preview_label.configure(image=None)
        self.preview_label.image = None
    # End overlay

    # Background prefetch of animations for thumbnails and previews
    def _start_background_prefetch(self):
        anim_paths = [p for p in self.files if p.suffix.lower()
                      in (".gif", ".webp")]
        if not anim_paths:
            return

        # Estimate a preview target size based on initial window size (minus margins)
        try:
            self.root.update_idletasks()
            canvas_w = self.canvas.winfo_width() or 1280
            canvas_h = self.canvas.winfo_height() or 800
        except Exception:
            canvas_w, canvas_h = 1280, 800
        margin = 40
        preview_size = (max(100, canvas_w - 2 * margin),
                        max(100, canvas_h - 2 * margin))

        # Submit prefetch jobs to dedicated executor
        def prefetch_one(path: Path):
            results = {}
            try:
                # Thumbnail cache
                k_thumb = (path, THUMB_SIZE)
                if k_thumb not in self.anim_cache:
                    frames_t, durs_t = load_animation_frames(path, THUMB_SIZE)
                    results[k_thumb] = (frames_t, durs_t)

                # Preview cache
                k_prev = (path, preview_size)
                if k_prev not in self.anim_cache:
                    frames_p, durs_p = load_animation_frames(
                        path, preview_size)
                    results[k_prev] = (frames_p, durs_p)
            except Exception:
                pass
            return results

        futures = [self.prefetch_executor.submit(
            prefetch_one, p) for p in anim_paths]

        # When each job completes, store into cache on the main thread to keep references safe
        def handle_done(fut: Future):
            try:
                res = fut.result()
            except Exception:
                res = {}
            if not res:
                return

            def apply():
                for k, v in res.items():
                    if k not in self.anim_cache:
                        self.anim_cache[k] = v

            self.root.after(0, apply)

        for fut in futures:
            fut.add_done_callback(handle_done)


def main():
    wall_dir = Path(WALL_DIR).expanduser()
    files = find_images(wall_dir)
    if not files:
        print(f"No images found in {wall_dir}", file=sys.stderr)
        sys.exit(1)

    root = tk.Tk()
    try:
        root.wm_attributes("-type", "dialog")
    except Exception:
        pass
    root.bind("<Escape>", lambda e: root.destroy())

    app = PickerApp(root, files)
    root.mainloop()


if __name__ == "__main__":
    main()
