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