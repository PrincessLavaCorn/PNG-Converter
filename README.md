# Universal Lossless PNG Converter

A modern desktop GUI application built in Python & PySide6 (Qt) to convert any image format—including Apple HEIC/HEIF, Live Photos, DNG ProRAW, and standard image formats—into high-quality lossless PNGs.

## Key Features

- **Apple Formats Supported**: HEIC, HEIF, HIF, AVIF, Apple DNG (ProRAW), and Live Photo still frames.
- **Accurate Color Preservation**: Automatically converts Apple Display P3 wide gamut to standard sRGB, ensuring photos never appear washed out or dull on Windows, Android, or web browsers.
- **Auto-Orientation & EXIF**: Performs EXIF transpose so portrait photos are right-side up, and preserves camera metadata.
- **Lossless Quality**: Strict lossless PNG compression without visual degradation.
- **Windows 11 Native Aesthetic**: Clean white background with crisp Windows blue accent outlines and buttons.
- **Dark Mode Toggle**: Includes a one-click toggle to switch to Windows 11 Dark Mode (`#202020`).
- **Drag & Drop**: Drop individual files, multiple selections, or entire folders (with automatic recursive scanning).
- **Collision Avoidance**: Automatically appends `_1`, `_2` if target filename already exists so your original files are never overwritten.
- **Multi-threaded Background Worker**: Keeps the GUI 100% responsive during large batch conversions with real-time progress bars.

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   python png_converter.py
   ```
   *(Or double-click `run.bat` on Windows)*
