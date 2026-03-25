<<<<<<< HEAD
# NodBoard

A hands-free typing system controlled entirely by eye movements. This desktop application uses computer vision to track your eye gaze and allows you to type by looking at virtual keyboard keys.

## Features

- **Real-time Eye Tracking**: Uses MediaPipe FaceMesh for accurate gaze estimation
- **Calibration System**: 9-point calibration for personalized accuracy
- **Virtual Keyboard**: Full QWERTY layout with dwell-to-type functionality
- **Word Prediction**: Smart next-word suggestions based on typing history
- **Blink Detection**: Use blinks to click, delete, or insert spaces
- **Text-to-Speech**: Hear your typed text spoken aloud
- **User Profiles**: Save and switch between different user configurations
- **Gaze Heatmap**: Visualize where you look most during typing sessions
- **Settings Panel**: Customize dwell time, themes, and more
- **Cross-Platform**: Works on Windows, macOS, and Linux

## Installation

1. **Clone or download** this repository to your local machine.

2. **Install Python** (version 3.8 or higher) if you haven't already. Download from [python.org](https://www.python.org/).

3. **Install dependencies**:
   ```
   pip install -r requirements.txt
   ```

4. **Run the application**:
   ```
   python main.py
   ```

## How to Use

### First Time Setup

1. **Launch the app**: Run `python main.py`
2. **Select or create a profile**: Choose an existing profile or create a new one
3. **Calibrate**: Follow the on-screen instructions to calibrate your eye gaze
4. **Start typing**: Look at keys on the virtual keyboard to type

### Calibration Process

- A 9-point grid will appear on screen
- Stare at each red dot for 2 seconds
- The system collects gaze samples and creates a mapping
- Calibration accuracy will be displayed after completion
- Press 'R' anytime to recalibrate

### Typing

- **Dwell-to-Type**: Stare at a key for the configured dwell time (default 1.2s) to type it
- **Blink to Click**: Single blink confirms the current key selection
- **Double Blink**: Deletes the last character
- **Long Blink**: Inserts a space
- **Word Suggestions**: Look at word suggestions above the keyboard to insert full words

### Keyboard Shortcuts

- `R` → Start recalibration
- `ESC` → Exit app
- `CTRL+S` → Save text to file
- `CTRL+Z` → Undo
- `CTRL+Y` → Redo
- `CTRL+C` → Copy text
- `F1` → Toggle dark/light mode
- `F2` → Toggle word prediction
- `F3` → Show gaze heatmap
- `SPACE` → Pause/resume gaze tracking

## Troubleshooting

### Camera Issues
- Ensure your webcam is connected and not being used by other applications
- Try different camera sources in settings (0, 1, 2, etc.)
- Good lighting is important for accurate tracking

### Calibration Problems
- Clean your camera lens
- Ensure you're in a well-lit environment
- Remove glasses if they cause reflections
- Take breaks if your eyes feel strained

### Performance Issues
- Close other applications using the camera
- Lower camera resolution in settings if needed
- Ensure your computer meets minimum requirements

## System Requirements

- **OS**: Windows 10+, macOS 10.15+, Ubuntu 18.04+
- **Python**: 3.8 or higher
- **Camera**: Webcam with at least 640x480 resolution
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 500MB free space

## Architecture

The application is structured as follows:

- `main.py`: Main application entry point and UI coordination
- `gaze_engine.py`: Core eye tracking and gaze estimation
- `calibration.py`: Calibration system and screen mapping
- `keyboard_ui.py`: Virtual keyboard rendering and interaction
- `word_predictor.py`: Word prediction and suggestion engine
- `voice_output.py`: Text-to-speech functionality
- `blink_detector.py`: Blink detection and classification
- `settings.py`: User settings management
- `profiles.py`: User profile management
- `heatmap.py`: Gaze heatmap visualization

## Contributing

This is an open-source project. Feel free to contribute improvements, bug fixes, or new features.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This application is for research and accessibility purposes. Always consult with medical professionals for assistive technology needs. Prolonged screen time may cause eye strain.
=======
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
>>>>>>> 52c3d7ea5ed405484f229b508704a40d14764e6c
