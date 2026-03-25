"""Provide a lightweight mp.solutions.face_mesh shim for MediaPipe 0.10.x.

This module is imported automatically via a .pth file placed into the
user site-packages directory. It installs an import hook that patches the
real `mediapipe` module (when it is imported) to include a `mp.solutions` API
compatible with legacy code.

The shim uses the new MediaPipe Tasks FaceLandmarker under the hood.
"""

import importlib
import importlib.abc
import importlib.util
import os
import sys
import types

_MODEL_NAME = "face_landmarker.task"
_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-tasks/face_landmarker/"
    "face_landmarker.task"
)

# Keep a reference so we don't download repeatedly.
_model_downloaded = False


def _download_model(target_path: str) -> None:
    """Download the face landmarker task model if it's missing."""
    global _model_downloaded

    if _model_downloaded or os.path.exists(target_path):
        return

    try:
        import urllib.request

        urllib.request.urlretrieve(_MODEL_URL, target_path)
        _model_downloaded = True
    except Exception:
        # If the download fails, the underlying FaceLandmarker will raise a clear error.
        pass


def _create_face_mesh_class(model_path: str):
    """Return a FaceMesh class that wraps MediaPipe Tasks FaceLandmarker."""

    # Imports are deferred until the class is created so that importing this
    # shim does not force MediaPipe or matplotlib to be imported.
    from mediapipe.tasks.python.vision import face_landmarker
    from mediapipe.tasks.python.core import base_options
    from mediapipe.tasks.python.vision.core import vision_task_running_mode, image as mp_image
    import cv2

    class FaceMesh:
        """A minimal shim compatible with `mp.solutions.face_mesh.FaceMesh`."""

        def __init__(
            self,
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        ):
            options = face_landmarker.FaceLandmarkerOptions(
                base_options=base_options.BaseOptions(model_asset_path=model_path),
                running_mode=vision_task_running_mode.VisionTaskRunningMode.IMAGE,
                num_faces=max_num_faces,
                min_face_detection_confidence=min_detection_confidence,
                min_tracking_confidence=min_tracking_confidence,
            )
            self._landmarker = face_landmarker.FaceLandmarker.create_from_options(options)

        def process(self, image):
            # Accept OpenCV images (BGR numpy arrays) or MediaPipe Image
            if hasattr(image, "shape") and image.ndim == 3 and image.shape[2] == 3:
                rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                image = mp_image.Image(mp_image.ImageFormat.SRGB, rgb)

            result = self._landmarker.detect(image)

            class Result:
                pass

            class LandmarkList:
                def __init__(self, landmarks):
                    self.landmark = landmarks

            res = Result()
            res.multi_face_landmarks = [LandmarkList(lm) for lm in result.face_landmarks]
            return res

        def close(self):
            try:
                self._landmarker.close()
            except Exception:
                pass

    return FaceMesh


def _patch_mediapipe_module(mp_module):
    """Patch an imported mediapipe module with a mp.solutions.face_mesh shim."""
    if hasattr(mp_module, "solutions"):
        return

    project_root = os.path.dirname(__file__)
    model_path = os.path.join(project_root, _MODEL_NAME)
    _download_model(model_path)

    FaceMesh = _create_face_mesh_class(model_path)
    mp_module.solutions = types.SimpleNamespace(face_mesh=types.SimpleNamespace(FaceMesh=FaceMesh))


class _MediapipeFinder(importlib.abc.MetaPathFinder):
    """Meta path finder that patches mediapipe when it is imported."""

    def find_spec(self, fullname, path, target=None):
        if fullname != "mediapipe":
            return None

        # Use PathFinder to avoid recursing through meta_path (including ourselves).
        from importlib.machinery import PathFinder

        spec = PathFinder.find_spec(fullname, path)
        if spec is None:
            return None

        # Wrap the loader so we can patch after the module is executed.
        original_loader = spec.loader

        class _Loader(importlib.abc.Loader):
            def create_module(self, spec):
                if hasattr(original_loader, "create_module"):
                    return original_loader.create_module(spec)
                return None

            def exec_module(self, module):
                if hasattr(original_loader, "exec_module"):
                    original_loader.exec_module(module)
                else:
                    # Fallback: use default machinery
                    import importlib._bootstrap as _bootstrap
                    _bootstrap._load(spec.name, _bootstrap._find_and_load(spec.name, None))
                _patch_mediapipe_module(module)

        spec.loader = _Loader()
        return spec


# If mediapipe is already imported, patch it immediately.
if "mediapipe" in sys.modules:
    try:
        _patch_mediapipe_module(sys.modules["mediapipe"])  # type: ignore
    except Exception:
        pass

# Install the import hook so that future imports of mediapipe are patched.
if not any(isinstance(f, _MediapipeFinder) for f in sys.meta_path):
    sys.meta_path.insert(0, _MediapipeFinder())
