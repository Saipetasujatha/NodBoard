"""Startup hooks for this project.

This file runs automatically when Python starts (if it's on sys.path).
It patches the installed MediaPipe library to provide a lightweight
`mp.solutions.face_mesh.FaceMesh` shim using the new Tasks API.

This allows existing code that expects `mp.solutions.face_mesh` to work
with MediaPipe 0.10.x (which no longer exports `mp.solutions`).
"""


import os
import sys
import types

# Only patch if mediapipe is available
try:
    import mediapipe as mp  # type: ignore
except Exception:
    mp = None

if mp is not None and not hasattr(mp, "solutions"):
    # Create a simple namespace to mimic the old mp.solutions API.
    solutions = types.SimpleNamespace()

    try:
        from mediapipe.tasks.python.vision import face_landmarker
        from mediapipe.tasks.python.core import base_options
        from mediapipe.tasks.python.vision.core import vision_task_running_mode, image as mp_image
        import cv2
    except Exception:
        # If any of these imports fail, we silently skip patching.
        mp.solutions = solutions
    else:
        # Ensure a face_landmarker model is available next to this file.
        _THIS_DIR = os.path.dirname(__file__)
        _MODEL_NAME = "face_landmarker.task"
        _MODEL_PATH = os.path.join(_THIS_DIR, _MODEL_NAME)

        if not os.path.exists(_MODEL_PATH):
            try:
                import urllib.request

                _MODEL_URL = (
                    "https://storage.googleapis.com/mediapipe-tasks/face_landmarker/"
                    "face_landmarker.task"
                )
                urllib.request.urlretrieve(_MODEL_URL, _MODEL_PATH)
            except Exception:
                # If download fails, leave _MODEL_PATH as-is; the underlying
                # FaceLandmarker will raise a clear error later.
                pass

        class FaceMesh:
            """A small shim compatible with `mp.solutions.face_mesh.FaceMesh`.

            This wraps the MediaPipe Tasks FaceLandmarker API and exposes a
            `process()` interface that returns an object with
            `multi_face_landmarks`, matching the old Solutions API shape.
            """

            def __init__(
                self,
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=False,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            ):
                options = face_landmarker.FaceLandmarkerOptions(
                    base_options=base_options.BaseOptions(model_asset_path=_MODEL_PATH),
                    running_mode=vision_task_running_mode.VisionTaskRunningMode.IMAGE,
                    num_faces=max_num_faces,
                    min_face_detection_confidence=min_detection_confidence,
                    min_tracking_confidence=min_tracking_confidence,
                )
                self._landmarker = face_landmarker.FaceLandmarker.create_from_options(options)

            def process(self, image):
                """Process a BGR OpenCV frame or MediaPipe Image and return landmarks."""
                if hasattr(image, "shape") and image.ndim == 3 and image.shape[2] == 3:
                    # OpenCV BGR image
                    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    mp_image_obj = mp_image.Image(mp_image.ImageFormat.SRGB, rgb)
                else:
                    # Assume already a MediaPipe Image
                    mp_image_obj = image

                result = self._landmarker.detect(mp_image_obj)

                # Wrap into an object compatible with mp.solutions.face_mesh output
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

        solutions.face_mesh = types.SimpleNamespace(FaceMesh=FaceMesh)
        mp.solutions = solutions
