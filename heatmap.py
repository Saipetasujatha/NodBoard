"""
Gaze Heatmap - Visual Gaze Analysis Tool

This module generates and displays heatmaps of user gaze patterns
to help analyze typing efficiency and identify problem areas.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
from scipy.stats import gaussian_kde
import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image, ImageTk
import io
import os

# Configuration constants
CONFIG = {
    'heatmap_resolution': 100,  # pixels per unit
    'gaussian_bandwidth': 0.05,  # KDE bandwidth
    'color_map': 'hot',  # matplotlib colormap
    'alpha': 0.7,  # heatmap transparency
    'min_samples': 10,  # minimum gaze samples for heatmap
}

class GazeHeatmap:
    """
    Generates and displays gaze heatmaps for analysis.
    """

    def __init__(self):
        """Initialize gaze heatmap generator."""
        self.gaze_samples = []
        self.keyboard_bounds = None
        self.heatmap_image = None

        # Custom colormap for better visibility
        self.create_custom_colormap()

    def create_custom_colormap(self):
        """Create a custom colormap for heatmaps."""
        # Colors: blue (low) -> green -> yellow -> red (high)
        colors = [
            (0.0, 0.0, 1.0),  # Blue
            (0.0, 1.0, 0.0),  # Green
            (1.0, 1.0, 0.0),  # Yellow
            (1.0, 0.0, 0.0),  # Red
        ]
        self.custom_cmap = LinearSegmentedColormap.from_list("gaze_heatmap", colors, N=256)

    def add_gaze_sample(self, x, y):
        """
        Add a gaze sample to the collection.

        Args:
            x, y: Normalized gaze coordinates (0-1)
        """
        self.gaze_samples.append((x, y))

    def set_keyboard_bounds(self, key_positions):
        """
        Set keyboard layout for heatmap overlay.

        Args:
            key_positions: Dict of {key_text: (x, y)} positions
        """
        if not key_positions:
            return

        # Calculate keyboard bounds
        positions = list(key_positions.values())
        x_coords = [pos[0] for pos in positions]
        y_coords = [pos[1] for pos in positions]

        self.keyboard_bounds = {
            'x_min': min(x_coords),
            'x_max': max(x_coords),
            'y_min': min(y_coords),
            'y_max': max(y_coords),
            'key_positions': key_positions
        }

    def generate_heatmap(self, gaze_samples=None, key_positions=None):
        """
        Generate heatmap from gaze samples.

        Args:
            gaze_samples: List of (x, y) gaze coordinates
            key_positions: Dict of key positions for overlay

        Returns:
            PIL Image or None: Generated heatmap image
        """
        if gaze_samples:
            self.gaze_samples = gaze_samples

        if key_positions:
            self.set_keyboard_bounds(key_positions)

        if len(self.gaze_samples) < CONFIG['min_samples']:
            print(f"Not enough gaze samples for heatmap. Need at least {CONFIG['min_samples']}, got {len(self.gaze_samples)}")
            return None

        try:
            # Convert samples to numpy array
            samples = np.array(self.gaze_samples)

            # Create grid for evaluation
            if self.keyboard_bounds:
                x_min, x_max = self.keyboard_bounds['x_min'], self.keyboard_bounds['x_max']
                y_min, y_max = self.keyboard_bounds['y_min'], self.keyboard_bounds['y_max']

                # Add some padding
                padding = 0.1
                x_range = x_max - x_min
                y_range = y_max - y_min
                x_min -= x_range * padding
                x_max += x_range * padding
                y_min -= y_range * padding
                y_max += y_range * padding
            else:
                x_min, x_max = 0, 1
                y_min, y_max = 0, 1

            # Create evaluation grid
            x_grid, y_grid = np.mgrid[x_min:x_max:CONFIG['heatmap_resolution']*1j,
                                     y_min:y_max:CONFIG['heatmap_resolution']*1j]

            # Perform kernel density estimation
            try:
                kde = gaussian_kde(samples.T, bw_method=CONFIG['gaussian_bandwidth'])
                z = kde.evaluate(np.vstack([x_grid.ravel(), y_grid.ravel()]))
                z = z.reshape(x_grid.shape)
            except np.linalg.LinAlgError:
                # Fallback for singular matrix
                print("KDE failed, using histogram-based heatmap")
                z = self._generate_histogram_heatmap(samples, x_grid, y_grid)

            # Create figure
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.set_xlim(x_min, x_max)
            ax.set_ylim(y_min, y_max)

            # Plot heatmap
            heatmap = ax.imshow(
                z.T,
                extent=[x_min, x_max, y_min, y_max],
                origin='lower',
                cmap=self.custom_cmap,
                alpha=CONFIG['alpha'],
                aspect='auto'
            )

            # Add colorbar
            cbar = plt.colorbar(heatmap, ax=ax)
            cbar.set_label('Gaze Density')

            # Overlay keyboard layout if available
            if self.keyboard_bounds:
                self._overlay_keyboard(ax)

            # Set labels and title
            ax.set_xlabel('X Coordinate')
            ax.set_ylabel('Y Coordinate')
            ax.set_title(f'Gaze Heatmap ({len(self.gaze_samples)} samples)')

            # Convert to PIL Image
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            self.heatmap_image = Image.open(buf)
            plt.close(fig)

            return self.heatmap_image

        except Exception as e:
            print(f"Error generating heatmap: {e}")
            return None

    def _generate_histogram_heatmap(self, samples, x_grid, y_grid):
        """Fallback histogram-based heatmap generation."""
        # Create 2D histogram
        hist, x_edges, y_edges = np.histogram2d(
            samples[:, 0], samples[:, 1],
            bins=CONFIG['heatmap_resolution'],
            range=[[x_grid.min(), x_grid.max()], [y_grid.min(), y_grid.max()]]
        )

        # Smooth the histogram
        from scipy import ndimage
        hist_smooth = ndimage.gaussian_filter(hist, sigma=1)

        return hist_smooth

    def _overlay_keyboard(self, ax):
        """Overlay keyboard layout on the heatmap."""
        if not self.keyboard_bounds:
            return

        key_positions = self.keyboard_bounds['key_positions']

        # Draw key outlines
        key_size = 0.03  # Approximate key size (normalized)

        for key_text, (x, y) in key_positions.items():
            # Draw key rectangle
            rect = patches.Rectangle(
                (x - key_size/2, y - key_size/2),
                key_size, key_size,
                linewidth=1,
                edgecolor='black',
                facecolor='none',
                alpha=0.7
            )
            ax.add_patch(rect)

            # Add key label
            ax.text(x, y, key_text,
                   ha='center', va='center',
                   fontsize=8, fontweight='bold',
                   bbox=dict(boxstyle="round,pad=0.1",
                           facecolor="white",
                           alpha=0.8))

    def show_heatmap(self, parent_window=None):
        """
        Display the heatmap in a window.

        Args:
            parent_window: Parent Tkinter window
        """
        if not self.heatmap_image:
            if not self.generate_heatmap():
                tk.messagebox.showerror("Error", "Failed to generate heatmap. Not enough gaze data.")
                return

        # Create heatmap window
        heatmap_window = tk.Toplevel(parent_window) if parent_window else tk.Tk()
        heatmap_window.title("Gaze Heatmap Analysis")
        heatmap_window.geometry("1000x700")

        # Convert PIL image to Tkinter format
        photo = ImageTk.PhotoImage(self.heatmap_image)

        # Create canvas and display image
        canvas = tk.Canvas(heatmap_window, width=photo.width(), height=photo.height())
        canvas.pack(fill=tk.BOTH, expand=True)
        canvas.create_image(0, 0, anchor=tk.NW, image=photo)

        # Keep reference to prevent garbage collection
        canvas.image = photo

        # Add control buttons
        button_frame = ttk.Frame(heatmap_window)
        button_frame.pack(fill=tk.X, pady=5)

        def save_heatmap():
            filename = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
            )
            if filename:
                self.heatmap_image.save(filename)
                tk.messagebox.showinfo("Saved", f"Heatmap saved to {filename}")

        def regenerate_heatmap():
            # Regenerate with current samples
            new_image = self.generate_heatmap()
            if new_image:
                new_photo = ImageTk.PhotoImage(new_image)
                canvas.itemconfig(canvas.find_all()[0], image=new_photo)
                canvas.image = new_photo
                tk.messagebox.showinfo("Updated", "Heatmap regenerated with latest data")

        ttk.Button(button_frame, text="Save PNG", command=save_heatmap).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Regenerate", command=regenerate_heatmap).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Close", command=heatmap_window.destroy).pack(side=tk.RIGHT, padx=5)

        # Add statistics label
        stats_text = f"Samples: {len(self.gaze_samples)} | Resolution: {CONFIG['heatmap_resolution']}x{CONFIG['heatmap_resolution']}"
        stats_label = ttk.Label(button_frame, text=stats_text)
        stats_label.pack(side=tk.LEFT, padx=20)

    def get_heatmap_stats(self):
        """
        Get statistics about the gaze heatmap.

        Returns:
            dict: Heatmap statistics
        """
        if not self.gaze_samples:
            return {}

        samples = np.array(self.gaze_samples)

        stats = {
            'total_samples': len(self.gaze_samples),
            'x_range': (float(samples[:, 0].min()), float(samples[:, 0].max())),
            'y_range': (float(samples[:, 1].min()), float(samples[:, 1].max())),
            'x_mean': float(samples[:, 0].mean()),
            'y_mean': float(samples[:, 1].mean()),
            'x_std': float(samples[:, 0].std()),
            'y_std': float(samples[:, 1].std()),
        }

        # Calculate spread metrics
        if self.keyboard_bounds:
            key_positions = list(self.keyboard_bounds['key_positions'].values())
            key_centers = np.array(key_positions)

            # Find closest keys for each gaze sample
            from scipy.spatial.distance import cdist
            distances = cdist(samples, key_centers)
            min_distances = np.min(distances, axis=1)

            stats['mean_distance_to_keys'] = float(min_distances.mean())
            stats['max_distance_to_keys'] = float(min_distances.max())
            stats['accuracy_score'] = float((min_distances < 0.05).mean())  # Within 5% of screen

        return stats

    def clear_samples(self):
        """Clear all gaze samples."""
        self.gaze_samples.clear()
        self.heatmap_image = None

    def export_heatmap_data(self, filename):
        """
        Export heatmap data to a file.

        Args:
            filename: Output filename
        """
        try:
            data = {
                'gaze_samples': self.gaze_samples,
                'keyboard_bounds': self.keyboard_bounds,
                'stats': self.get_heatmap_stats(),
                'config': CONFIG
            }

            import json
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2, default=str)

            print(f"Heatmap data exported to {filename}")

        except Exception as e:
            print(f"Error exporting heatmap data: {e}")

    def analyze_gaze_patterns(self):
        """
        Analyze gaze patterns for insights.

        Returns:
            dict: Analysis results
        """
        if len(self.gaze_samples) < CONFIG['min_samples']:
            return {'error': 'Not enough samples for analysis'}

        samples = np.array(self.gaze_samples)

        analysis = {
            'total_samples': len(self.gaze_samples),
            'time_distribution': self._analyze_time_distribution(),
            'spatial_distribution': self._analyze_spatial_distribution(samples),
            'movement_patterns': self._analyze_movement_patterns(samples),
        }

        return analysis

    def _analyze_time_distribution(self):
        """Analyze how gaze is distributed over time."""
        # This would require timestamped samples
        return {'note': 'Time analysis requires timestamped gaze samples'}

    def _analyze_spatial_distribution(self, samples):
        """Analyze spatial distribution of gaze."""
        x_coords, y_coords = samples[:, 0], samples[:, 1]

        # Calculate quartiles
        x_quartiles = np.percentile(x_coords, [25, 50, 75])
        y_quartiles = np.percentile(y_coords, [25, 50, 75])

        return {
            'x_quartiles': x_quartiles.tolist(),
            'y_quartiles': y_quartiles.tolist(),
            'spread_x': float(x_coords.max() - x_coords.min()),
            'spread_y': float(y_coords.max() - y_coords.min()),
        }

    def _analyze_movement_patterns(self, samples):
        """Analyze gaze movement patterns."""
        if len(samples) < 3:
            return {'error': 'Need more samples for movement analysis'}

        # Calculate distances between consecutive points
        distances = np.sqrt(np.sum(np.diff(samples, axis=0)**2, axis=1))

        return {
            'mean_movement': float(distances.mean()),
            'max_movement': float(distances.max()),
            'total_path_length': float(distances.sum()),
            'movement_variance': float(distances.var()),
        }

# Example usage
if __name__ == "__main__":
    # Test heatmap generation
    heatmap = GazeHeatmap()

    # Add some test gaze samples
    np.random.seed(42)
    test_samples = np.random.rand(100, 2)  # 100 random points
    for sample in test_samples:
        heatmap.add_gaze_sample(sample[0], sample[1])

    # Mock keyboard positions
    mock_keys = {
        'Q': (0.1, 0.1), 'W': (0.2, 0.1), 'E': (0.3, 0.1),
        'A': (0.1, 0.2), 'S': (0.2, 0.2), 'D': (0.3, 0.2),
        'Z': (0.1, 0.3), 'X': (0.2, 0.3), 'C': (0.3, 0.3),
    }
    heatmap.set_keyboard_bounds(mock_keys)

    # Generate and show heatmap
    image = heatmap.generate_heatmap()
    if image:
        print("Heatmap generated successfully")
        print(f"Image size: {image.size}")

        # Show stats
        stats = heatmap.get_heatmap_stats()
        print("Heatmap statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

        # Analyze patterns
        analysis = heatmap.analyze_gaze_patterns()
        print("Gaze pattern analysis:")
        for key, value in analysis.items():
            print(f"  {key}: {value}")
    else:
        print("Failed to generate heatmap")