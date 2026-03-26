"""
heatmap.py
----------
Records gaze points during a session and renders a smooth heatmap
overlay on the keyboard using matplotlib + scipy gaussian_kde.
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde
import tkinter as tk
from PIL import Image, ImageTk
import io

CONFIG = {
    "MAX_POINTS": 10000,
    "HEATMAP_ALPHA": 0.65,
    "COLORMAP": "hot",
    "EXPORT_FILENAME": "gaze_heatmap.png",
    "RESOLUTION": 200,
    "WINDOW_TITLE": "Gaze Heatmap",
    "BG_COLOR": "#1a1a2e",
}


class GazeHeatmap:
    """
    Collects gaze (x, y) screen coordinates and renders a heatmap.
    """

    def __init__(self):
        self._points_x = []
        self._points_y = []

    # ── Public API ───────────────────────────────────────────────────────────

    def record(self, x, y):
        """Add a gaze point."""
        if len(self._points_x) < CONFIG["MAX_POINTS"]:
            self._points_x.append(float(x))
            self._points_y.append(float(y))

    def add_gaze_sample(self, x, y):
        """Alias for record()."""
        self.record(x, y)

    def clear(self):
        """Reset all recorded points."""
        self._points_x.clear()
        self._points_y.clear()

    def clear_samples(self):
        """Alias for clear()."""
        self.clear()

    def point_count(self):
        return len(self._points_x)

    def generate_heatmap(self, gaze_samples=None, key_positions=None):
        """
        Generate heatmap. Accepts optional gaze_samples list of (x, y) tuples.
        Returns PIL Image or None.
        """
        if gaze_samples:
            for x, y in gaze_samples:
                self.record(x, y)
        if len(self._points_x) < 10:
            return None
        return self._render(1920, 1080)

    def show_heatmap(self, parent_widget=None, screen_w=1920, screen_h=1080):
        """Render heatmap and display in a Tkinter Toplevel window."""
        if len(self._points_x) < 10:
            tk.messagebox.showinfo(
                "Heatmap", "Not enough gaze data yet. Keep using the keyboard."
            )
            return
        img = self._render(screen_w, screen_h)
        self._display_window(parent_widget or tk.Tk(), img)

    def show(self, parent_widget, screen_w, screen_h):
        """Alias for show_heatmap."""
        self.show_heatmap(parent_widget, screen_w, screen_h)

    def export_png(self, screen_w=1920, screen_h=1080):
        """Save heatmap as PNG file."""
        if len(self._points_x) < 10:
            return None
        img = self._render(screen_w, screen_h)
        img.save(CONFIG["EXPORT_FILENAME"])
        return CONFIG["EXPORT_FILENAME"]

    # ── Internal ─────────────────────────────────────────────────────────────

    def _render(self, screen_w, screen_h):
        """Compute gaussian KDE over recorded points and return a PIL Image."""
        xs = np.array(self._points_x)
        ys = np.array(self._points_y)

        res = CONFIG["RESOLUTION"]
        xi = np.linspace(0, screen_w, res)
        yi = np.linspace(0, screen_h, res)
        xi_grid, yi_grid = np.meshgrid(xi, yi)
        positions = np.vstack([xi_grid.ravel(), yi_grid.ravel()])

        try:
            kernel = gaussian_kde(np.vstack([xs, ys]))
            density = kernel(positions).reshape(res, res)
        except Exception:
            density, _, _ = np.histogram2d(
                xs, ys, bins=res,
                range=[[0, screen_w], [0, screen_h]]
            )
            density = density.T

        fig, ax = plt.subplots(figsize=(screen_w / 100, screen_h / 100), dpi=100)
        ax.imshow(
            density,
            extent=[0, screen_w, screen_h, 0],
            origin="upper",
            cmap=CONFIG["COLORMAP"],
            alpha=CONFIG["HEATMAP_ALPHA"],
            aspect="auto",
        )
        ax.set_xlim(0, screen_w)
        ax.set_ylim(screen_h, 0)
        ax.axis("off")
        fig.patch.set_facecolor("black")
        plt.tight_layout(pad=0)

        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0,
                    facecolor="black")
        plt.close(fig)
        buf.seek(0)
        return Image.open(buf).copy()

    def _display_window(self, parent, pil_image):
        """Show heatmap image in a Tkinter Toplevel."""
        win = tk.Toplevel(parent)
        win.title(CONFIG["WINDOW_TITLE"])
        win.configure(bg=CONFIG["BG_COLOR"])

        max_w = 900
        w, h = pil_image.size
        if w > max_w:
            ratio = max_w / w
            pil_image = pil_image.resize((max_w, int(h * ratio)), Image.LANCZOS)

        photo = ImageTk.PhotoImage(pil_image)
        lbl = tk.Label(win, image=photo, bg="black")
        lbl.image = photo
        lbl.pack()

        btn_frame = tk.Frame(win, bg=CONFIG["BG_COLOR"])
        btn_frame.pack(pady=8)

        tk.Button(
            btn_frame, text="Export PNG", font=("Arial", 11),
            bg="#4a90d9", fg="white", relief="flat", padx=12, pady=6,
            command=lambda: self._export_and_notify(win, pil_image)
        ).pack(side="left", padx=8)

        tk.Button(
            btn_frame, text="Clear Data", font=("Arial", 11),
            bg="#c0392b", fg="white", relief="flat", padx=12, pady=6,
            command=lambda: [self.clear(), win.destroy()]
        ).pack(side="left", padx=8)

        tk.Button(
            btn_frame, text="Close", font=("Arial", 11),
            bg="#555", fg="white", relief="flat", padx=12, pady=6,
            command=win.destroy
        ).pack(side="left", padx=8)

    def _export_and_notify(self, parent, pil_image):
        pil_image.save(CONFIG["EXPORT_FILENAME"])
        tk.messagebox.showinfo(
            "Exported", f"Heatmap saved as {CONFIG['EXPORT_FILENAME']}",
            parent=parent
        )


if __name__ == "__main__":
    hm = GazeHeatmap()
    import random
    for _ in range(200):
        hm.record(random.uniform(0, 1920), random.uniform(0, 1080))
    print(f"Points recorded: {hm.point_count()}")
    img = hm.generate_heatmap()
    if img:
        print(f"Heatmap generated: {img.size}")