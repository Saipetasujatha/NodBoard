# Eye Gaze Typer

A hands-free desktop typing application controlled entirely by eye movements.
Uses your webcam + MediaPipe FaceMesh to track your gaze in real time.

---

## What This Project Does

- Tracks your eyes using a standard webcam (no special hardware needed)
- Maps your gaze to a virtual on-screen keyboard
- You type by staring at a key for a configurable dwell time (default 1.2s)
- Blink to confirm, double-blink to delete, long blink for space
- Word prediction suggests completions as you type
- Text-to-speech reads your typed text aloud
- Fully configurable: themes, dwell time, voices, profiles, and more

---

## Requirements

- Python 3.9 or higher
- A working webcam
- Windows, macOS, or Linux

---

## How to Install

```bash
# 1. Clone or download this project
cd eye_gaze_typer

# 2. (Recommended) Create a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## How to Run

```bash
python main.py
```

---

## How Calibration Works

1. A fullscreen window shows 9 red dots in a 3x3 grid
2. Stare at each dot for 2 seconds while keeping your head still
3. The app collects 30 gaze samples per dot (270 total)
4. A polynomial regression model maps raw iris positions → screen coordinates
5. Calibration accuracy (% error) is shown after completion
6. Data is saved to `calibration_data.json` for future sessions
7. Press **R** at any time to recalibrate

---

## Keyboard Shortcuts

| Key        | Action                        |
|------------|-------------------------------|
| R          | Start recalibration           |
| ESC        | Exit app                      |
| CTRL+S     | Save text to file             |
| CTRL+Z     | Undo                          |
| CTRL+Y     | Redo                          |
| CTRL+C     | Copy text                     |
| F1         | Toggle dark / light mode      |
| F2         | Toggle word prediction        |
| F3         | Show gaze heatmap             |
| SPACE      | Pause / resume gaze tracking  |

---

## File Overview

| File               | Purpose                                      |
|--------------------|----------------------------------------------|
| main.py            | App entry point, main window layout          |
| gaze_engine.py     | Eye tracking + gaze estimation (MediaPipe)   |
| calibration.py     | 9-point calibration screen                   |
| keyboard_ui.py     | Virtual keyboard with dwell selection        |
| word_predictor.py  | N-gram next-word prediction engine           |
| voice_output.py    | Text-to-speech (pyttsx3, offline)            |
| blink_detector.py  | Blink detection (EAR formula)                |
| settings.py        | Settings panel + settings.json persistence  |
| profiles.py        | User profile management                      |
| heatmap.py         | Gaze heatmap visualizer                      |

---

## Tips for Best Results

- Use in a well-lit room with light on your face
- Keep your head relatively still during calibration
- Sit 50–70 cm from the screen
- Recalibrate if you move your chair or change lighting
- Increase dwell time if accidental key presses occur
