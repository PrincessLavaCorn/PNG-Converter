"""
Lossless Universal Image to PNG Converter (CloudConvert-Style Interface)
Features:
- CloudConvert-style interactive queue list: file badges, format indicator, individual ✕ delete buttons.
- Direct row-level "Open" action once converted.
- Authentic Windows 11 circular radio buttons (with smooth radial-gradient indicators).
- Windows 11 Fluent Light Theme (clean white cards with crisp blue accents) and Dark Mode toggle.
- Universal Lossless PNG conversion: Apple HEIC/HEIF/AVIF/Live Photos/DNG ProRAW and all standard formats.
- Accurate Color Management: Apple Display P3 ICC profile to standard sRGB conversion.
- Auto-orientation (EXIF transpose) and safe EXIF metadata preservation.
- Collision avoidance: auto-renaming (e.g. photo_1.png) so existing files are never overwritten.
"""

import io
import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from PIL import Image, ImageCms, ImageOps
except ImportError:
    Image = None
    ImageCms = None
    ImageOps = None

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pillow_heif = None

try:
    from PySide6.QtCore import QSize, Qt, QThread, QTimer, Signal
    from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent, QFont, QIcon
    from PySide6.QtWidgets import (
        QApplication,
        QButtonGroup,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QRadioButton,
        QScrollArea,
        QSizePolicy,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    pass

# Supported formats
SUPPORTED_EXTENSIONS = {
    # Apple & modern photo formats
    ".heic", ".heif", ".hif", ".avif", ".dng",
    # Standard photography & web formats
    ".jpg", ".jpeg", ".jpe", ".jfif", ".webp", ".png",
    # Uncompressed & archival
    ".bmp", ".dib", ".tif", ".tiff", ".tga", ".icb", ".vda", ".vst",
    # Miscellaneous formats
    ".gif", ".ico", ".cur", ".pcx", ".ppm", ".pgm", ".pbm", ".pnm",
    ".dds", ".eps", ".ps", ".im", ".msp", ".sgi", ".xbm", ".xpm",
}


def is_supported_image(path: Path) -> bool:
    """Check if the given path is a readable supported image file."""
    if not path.is_file():
        return False
    if path.suffix.lower() in SUPPORTED_EXTENSIONS:
        return True
    try:
        with Image.open(path):
            return True
    except Exception:
        return False


def get_unique_output_path(dest_folder: Path, base_stem: str) -> Path:
    """Return a unique non-colliding PNG file path (appends _1, _2, etc. if needed)."""
    candidate = dest_folder / f"{base_stem}.png"
    if not candidate.exists():
        return candidate
    counter = 1
    while True:
        candidate = dest_folder / f"{base_stem}_{counter}.png"
        if not candidate.exists():
            return candidate
        counter += 1


def convert_single_image(src_path: Path, output_path: Path) -> Tuple[bool, str]:
    """
    Convert any image file to lossless PNG.
    - Accurately converts Apple Display P3 ICC profile to sRGB to prevent washed-out colors.
    - Applies EXIF transpose for orientation and retains safe EXIF tags.
    - Extracts the primary still frame if multi-frame.
    """
    try:
        with Image.open(src_path) as img:
            # Seek to first/primary frame (for bursts, GIFs, multi-frame TIFF/HEIC)
            try:
                img.seek(0)
            except (EOFError, AttributeError):
                pass

            # Auto-rotate based on EXIF orientation
            transposed = ImageOps.exif_transpose(img)
            if transposed is not None:
                img = transposed

            # Preserve EXIF metadata bytes
            exif_bytes = img.info.get("exif")

            # Color profile conversion (Apple Display P3 -> sRGB)
            icc_bytes = img.info.get("icc_profile")
            if icc_bytes and ImageCms:
                try:
                    src_profile = ImageCms.getOpenProfile(io.BytesIO(icc_bytes))
                    dst_profile = ImageCms.createProfile("sRGB")

                    # Normalize color modes suitable for profile transforms
                    if img.mode not in ("RGB", "RGBA"):
                        img = img.convert("RGBA" if "A" in img.mode else "RGB")

                    transform = ImageCms.buildTransform(
                        src_profile,
                        dst_profile,
                        img.mode,
                        img.mode,
                        renderingIntent=ImageCms.Intent.PERCEPTUAL,
                    )
                    ImageCms.applyTransform(img, transform, inPlace=True)
                except Exception:
                    # Graceful fallback: maintain raw RGB data if CMS transform fails
                    pass

            # Ensure compatible color space for lossless PNG
            if img.mode == "CMYK":
                img = img.convert("RGB")
            elif img.mode == "P" and "transparency" in img.info:
                img = img.convert("RGBA")
            elif img.mode not in ("RGB", "RGBA", "L", "LA", "1"):
                img = img.convert("RGBA" if "A" in img.mode else "RGB")

            # Lossless PNG save configuration
            save_options = {
                "format": "PNG",
                "compress_level": 6,  # Lossless standard
            }
            if exif_bytes:
                save_options["exif"] = exif_bytes

            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path, **save_options)
            return True, "Converted"

    except Exception as exc:
        return False, str(exc)


# =====================================================================
# QSS Stylesheets: Windows 11 Fluent Light & Windows 11 Dark Mode
# =====================================================================

WINDOWS_LIGHT_QSS = """
QMainWindow, QWidget#MainContainer {
    background-color: #F8F9FA;
    color: #1A1A1A;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
}

QFrame#HeaderCard, QFrame#ContentCard, QFrame#DropZone {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
}

QFrame#DropZone {
    border: 2px dashed #0067C0;
    background-color: #F4F8FC;
}

QFrame#DropZone:hover {
    background-color: #EBF3FC;
    border-color: #005A9E;
}

QLabel#AppTitle {
    font-size: 20px;
    font-weight: 600;
    color: #0F172A;
}

QLabel#AppSubtitle {
    font-size: 13px;
    color: #64748B;
}

QLabel#DropZoneTitle {
    font-size: 16px;
    font-weight: 600;
    color: #0067C0;
}

QLabel#DropZoneHint {
    font-size: 12px;
    color: #64748B;
}

/* Authentic Circular Radio Buttons (Windows 11 Light) */
QRadioButton {
    font-size: 13px;
    color: #1A1A1A;
    spacing: 9px;
    background: transparent;
}

QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border-radius: 10px;
    border: 2px solid #8A8A8A;
    background-color: #FFFFFF;
}

QRadioButton::indicator:hover {
    border-color: #0067C0;
}

QRadioButton::indicator:checked {
    border: 2px solid #0067C0;
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
        stop:0 #0067C0, stop:0.48 #0067C0, stop:0.52 #FFFFFF, stop:1 #FFFFFF);
}

QPushButton {
    background-color: #FFFFFF;
    color: #1A1A1A;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #F1F5F9;
    border-color: #94A3B8;
}

QPushButton:pressed {
    background-color: #E2E8F0;
}

QPushButton#PrimaryButton {
    background-color: #0067C0;
    color: #FFFFFF;
    border: 1px solid #005A9E;
    font-weight: 600;
}

QPushButton#PrimaryButton:hover {
    background-color: #1075C9;
    border-color: #004B87;
}

QPushButton#PrimaryButton:pressed {
    background-color: #005A9E;
}

QPushButton#PrimaryButton:disabled {
    background-color: #CBD5E1;
    border-color: #94A3B8;
    color: #64748B;
}

QPushButton#ThemeToggle {
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    background-color: #FFFFFF;
    font-size: 12px;
    font-weight: 500;
    padding: 5px 12px;
}

QPushButton#ThemeToggle:hover {
    background-color: #F1F5F9;
}

QLineEdit {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 10px;
    color: #1A1A1A;
}

QLineEdit:focus {
    border: 1px solid #0067C0;
}

QProgressBar {
    background-color: #E2E8F0;
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
    color: transparent;
}

QProgressBar::chunk {
    background-color: #0067C0;
    border-radius: 4px;
}

QScrollArea, QScrollArea QWidget, QScrollArea QWidget#CardsContainer {
    background-color: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
}

/* CloudConvert-Style File Cards (Light Mode) */
QFrame#FileCard {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
}

QFrame#FileCard:hover {
    border: 1px solid #B4C6DC;
    background-color: #FAFCFF;
}

QLabel#FileName {
    font-size: 13px;
    font-weight: 600;
    color: #0F172A;
}

QLabel#FileSize {
    font-size: 12px;
    color: #64748B;
}

QLabel#FormatBadge {
    background-color: #EBF3FC;
    color: #0067C0;
    border: 1px solid #C8E1FA;
    border-radius: 5px;
    padding: 3px 8px;
    font-weight: 700;
    font-size: 11px;
}

QLabel#TargetBadge {
    background-color: #F1F5F9;
    color: #334155;
    border: 1px solid #E2E8F0;
    border-radius: 5px;
    padding: 3px 8px;
    font-weight: 600;
    font-size: 11px;
}

QLabel#StatusBadge_ready {
    background-color: #F1F5F9;
    color: #475569;
    border: 1px solid #E2E8F0;
    border-radius: 5px;
    padding: 3px 9px;
    font-weight: 600;
    font-size: 12px;
}

QLabel#StatusBadge_converting {
    background-color: #EBF3FC;
    color: #0067C0;
    border: 1px solid #BBDDFB;
    border-radius: 5px;
    padding: 3px 9px;
    font-weight: 600;
    font-size: 12px;
}

QLabel#StatusBadge_done {
    background-color: #E6F4EA;
    color: #137333;
    border: 1px solid #CEEAD6;
    border-radius: 5px;
    padding: 3px 9px;
    font-weight: 600;
    font-size: 12px;
}

QLabel#StatusBadge_failed {
    background-color: #FCE8E6;
    color: #C5221F;
    border: 1px solid #FAD2CF;
    border-radius: 5px;
    padding: 3px 9px;
    font-weight: 600;
    font-size: 12px;
}

QPushButton#RowOpenBtn {
    background-color: #EBF3FC;
    color: #0067C0;
    border: 1px solid #BBDDFB;
    border-radius: 6px;
    padding: 4px 12px;
    font-weight: 600;
    font-size: 12px;
}

QPushButton#RowOpenBtn:hover {
    background-color: #0067C0;
    color: #FFFFFF;
}

QPushButton#RemoveBtn {
    background-color: transparent;
    color: #94A3B8;
    border: 1px solid transparent;
    border-radius: 14px;
    font-size: 14px;
    font-weight: 700;
    padding: 0px;
}

QPushButton#RemoveBtn:hover {
    background-color: #FEE2E2;
    color: #DC2626;
    border-color: #FECACA;
}

QLabel#EmptyLabel {
    font-size: 14px;
    color: #64748B;
    padding: 40px;
}

/* Windows 11 InfoBar / Toast Notification Banner (Light Mode) */
QFrame#NotificationBanner {
    border-radius: 8px;
    background-color: #DEF6E5;
    border: 1px solid #73D295;
}

QFrame#NotificationBanner[bannerType="success"] {
    background-color: #DEF6E5;
    border: 1px solid #73D295;
}

QFrame#NotificationBanner[bannerType="warning"] {
    background-color: #FFF4CE;
    border: 1px solid #F0C33C;
}

QFrame#NotificationBanner[bannerType="info"] {
    background-color: #EBF3FC;
    border: 1px solid #94C4F7;
}

QLabel#BannerIcon {
    font-size: 16px;
    font-weight: 700;
}

QFrame#NotificationBanner[bannerType="success"] QLabel#BannerIcon {
    color: #107C41;
}

QFrame#NotificationBanner[bannerType="warning"] QLabel#BannerIcon {
    color: #8A6500;
}

QFrame#NotificationBanner[bannerType="info"] QLabel#BannerIcon {
    color: #0067C0;
}

QLabel#BannerTitle {
    font-size: 13px;
    font-weight: 700;
    color: #0F172A;
}

QLabel#BannerMessage {
    font-size: 12px;
    color: #334155;
}

QPushButton#BannerActionBtn {
    background-color: #107C41;
    color: #FFFFFF;
    border: 1px solid #0B5A2F;
    border-radius: 6px;
    padding: 5px 12px;
    font-weight: 600;
    font-size: 12px;
}

QPushButton#BannerActionBtn:hover {
    background-color: #0E6C38;
}

QFrame#NotificationBanner[bannerType="warning"] QPushButton#BannerActionBtn {
    background-color: #8A6500;
    border: 1px solid #6E5100;
}

QFrame#NotificationBanner[bannerType="warning"] QPushButton#BannerActionBtn:hover {
    background-color: #725300;
}

QFrame#NotificationBanner[bannerType="info"] QPushButton#BannerActionBtn {
    background-color: #0067C0;
    border: 1px solid #005A9E;
}

QFrame#NotificationBanner[bannerType="info"] QPushButton#BannerActionBtn:hover {
    background-color: #005A9E;
}

QPushButton#BannerCloseBtn {
    background-color: transparent;
    color: #64748B;
    border: 1px solid transparent;
    border-radius: 13px;
    font-size: 12px;
    font-weight: 700;
}

QPushButton#BannerCloseBtn:hover {
    background-color: rgba(0, 0, 0, 0.07);
    color: #0F172A;
}
"""

WINDOWS_DARK_QSS = """
QMainWindow, QWidget#MainContainer {
    background-color: #202020;
    color: #EAEAEA;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
}

QFrame#HeaderCard, QFrame#ContentCard, QFrame#DropZone {
    background-color: #2B2B2B;
    border: 1px solid #383838;
    border-radius: 8px;
}

QFrame#DropZone {
    border: 2px dashed #4CC2FF;
    background-color: #242D35;
}

QFrame#DropZone:hover {
    background-color: #283745;
    border-color: #70D1FF;
}

QLabel#AppTitle {
    font-size: 20px;
    font-weight: 600;
    color: #FFFFFF;
}

QLabel#AppSubtitle {
    font-size: 13px;
    color: #A0A0A0;
}

QLabel#DropZoneTitle {
    font-size: 16px;
    font-weight: 600;
    color: #4CC2FF;
}

QLabel#DropZoneHint {
    font-size: 12px;
    color: #A0A0A0;
}

/* Authentic Circular Radio Buttons (Windows 11 Dark) */
QRadioButton {
    font-size: 13px;
    color: #EAEAEA;
    spacing: 9px;
    background: transparent;
}

QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border-radius: 10px;
    border: 2px solid #757575;
    background-color: #242424;
}

QRadioButton::indicator:hover {
    border-color: #4CC2FF;
}

QRadioButton::indicator:checked {
    border: 2px solid #4CC2FF;
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
        stop:0 #4CC2FF, stop:0.48 #4CC2FF, stop:0.52 #242424, stop:1 #242424);
}

QPushButton {
    background-color: #333333;
    color: #FFFFFF;
    border: 1px solid #484848;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #3D3D3D;
    border-color: #606060;
}

QPushButton:pressed {
    background-color: #282828;
}

QPushButton#PrimaryButton {
    background-color: #0078D4;
    color: #FFFFFF;
    border: 1px solid #005A9E;
    font-weight: 600;
}

QPushButton#PrimaryButton:hover {
    background-color: #198CE6;
    border-color: #0078D4;
}

QPushButton#PrimaryButton:pressed {
    background-color: #005A9E;
}

QPushButton#PrimaryButton:disabled {
    background-color: #404040;
    border-color: #505050;
    color: #777777;
}

QPushButton#ThemeToggle {
    border: 1px solid #484848;
    border-radius: 6px;
    background-color: #333333;
    color: #FFFFFF;
    font-size: 12px;
    font-weight: 500;
    padding: 5px 12px;
}

QPushButton#ThemeToggle:hover {
    background-color: #3D3D3D;
}

QLineEdit {
    background-color: #262626;
    border: 1px solid #484848;
    border-radius: 6px;
    padding: 6px 10px;
    color: #FFFFFF;
}

QLineEdit:focus {
    border: 1px solid #4CC2FF;
}

QProgressBar {
    background-color: #383838;
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
    color: transparent;
}

QProgressBar::chunk {
    background-color: #4CC2FF;
    border-radius: 4px;
}

QScrollArea, QScrollArea QWidget, QScrollArea QWidget#CardsContainer {
    background-color: #202020;
    border: 1px solid #383838;
    border-radius: 8px;
}

/* CloudConvert-Style File Cards (Dark Mode) */
QFrame#FileCard {
    background-color: #2B2B2B;
    border: 1px solid #383838;
    border-radius: 8px;
}

QFrame#FileCard:hover {
    border: 1px solid #555555;
    background-color: #313131;
}

QLabel#FileName {
    font-size: 13px;
    font-weight: 600;
    color: #FFFFFF;
}

QLabel#FileSize {
    font-size: 12px;
    color: #A0A0A0;
}

QLabel#FormatBadge {
    background-color: #1F3347;
    color: #4CC2FF;
    border: 1px solid #2B4E6E;
    border-radius: 5px;
    padding: 3px 8px;
    font-weight: 700;
    font-size: 11px;
}

QLabel#TargetBadge {
    background-color: #383838;
    color: #D0D0D0;
    border: 1px solid #484848;
    border-radius: 5px;
    padding: 3px 8px;
    font-weight: 600;
    font-size: 11px;
}

QLabel#StatusBadge_ready {
    background-color: #383838;
    color: #B0B0B0;
    border: 1px solid #484848;
    border-radius: 5px;
    padding: 3px 9px;
    font-weight: 600;
    font-size: 12px;
}

QLabel#StatusBadge_converting {
    background-color: #1F3347;
    color: #4CC2FF;
    border: 1px solid #2B4E6E;
    border-radius: 5px;
    padding: 3px 9px;
    font-weight: 600;
    font-size: 12px;
}

QLabel#StatusBadge_done {
    background-color: #143823;
    color: #5CD68D;
    border: 1px solid #1E5234;
    border-radius: 5px;
    padding: 3px 9px;
    font-weight: 600;
    font-size: 12px;
}

QLabel#StatusBadge_failed {
    background-color: #451D1D;
    color: #FF7B7B;
    border: 1px solid #632B2B;
    border-radius: 5px;
    padding: 3px 9px;
    font-weight: 600;
    font-size: 12px;
}

QPushButton#RowOpenBtn {
    background-color: #1F3347;
    color: #4CC2FF;
    border: 1px solid #2B4E6E;
    border-radius: 6px;
    padding: 4px 12px;
    font-weight: 600;
    font-size: 12px;
}

QPushButton#RowOpenBtn:hover {
    background-color: #4CC2FF;
    color: #1F1F1F;
}

QPushButton#RemoveBtn {
    background-color: transparent;
    color: #707070;
    border: 1px solid transparent;
    border-radius: 14px;
    font-size: 14px;
    font-weight: 700;
    padding: 0px;
}

QPushButton#RemoveBtn:hover {
    background-color: #451D1D;
    color: #FF7B7B;
    border-color: #632B2B;
}

QLabel#EmptyLabel {
    font-size: 14px;
    color: #888888;
    padding: 40px;
}

/* Windows 11 InfoBar / Toast Notification Banner (Dark Mode) */
QFrame#NotificationBanner {
    border-radius: 8px;
    background-color: #133823;
    border: 1px solid #236B3D;
}

QFrame#NotificationBanner[bannerType="success"] {
    background-color: #133823;
    border: 1px solid #236B3D;
}

QFrame#NotificationBanner[bannerType="warning"] {
    background-color: #382A13;
    border: 1px solid #6E5325;
}

QFrame#NotificationBanner[bannerType="info"] {
    background-color: #1F3347;
    border: 1px solid #2B5E8C;
}

QLabel#BannerIcon {
    font-size: 16px;
    font-weight: 700;
}

QFrame#NotificationBanner[bannerType="success"] QLabel#BannerIcon {
    color: #5CD68D;
}

QFrame#NotificationBanner[bannerType="warning"] QLabel#BannerIcon {
    color: #FCE100;
}

QFrame#NotificationBanner[bannerType="info"] QLabel#BannerIcon {
    color: #4CC2FF;
}

QLabel#BannerTitle {
    font-size: 13px;
    font-weight: 700;
    color: #FFFFFF;
}

QLabel#BannerMessage {
    font-size: 12px;
    color: #D4D4D4;
}

QPushButton#BannerActionBtn {
    background-color: #107C41;
    color: #FFFFFF;
    border: 1px solid #1E5234;
    border-radius: 6px;
    padding: 5px 12px;
    font-weight: 600;
    font-size: 12px;
}

QPushButton#BannerActionBtn:hover {
    background-color: #18934E;
}

QFrame#NotificationBanner[bannerType="warning"] QPushButton#BannerActionBtn {
    background-color: #997000;
    border: 1px solid #805E00;
}

QFrame#NotificationBanner[bannerType="warning"] QPushButton#BannerActionBtn:hover {
    background-color: #B38300;
}

QFrame#NotificationBanner[bannerType="info"] QPushButton#BannerActionBtn {
    background-color: #0078D4;
    border: 1px solid #005A9E;
}

QFrame#NotificationBanner[bannerType="info"] QPushButton#BannerActionBtn:hover {
    background-color: #1A8CE6;
}

QPushButton#BannerCloseBtn {
    background-color: transparent;
    color: #A0A0A0;
    border: 1px solid transparent;
    border-radius: 13px;
    font-size: 12px;
    font-weight: 700;
}

QPushButton#BannerCloseBtn:hover {
    background-color: rgba(255, 255, 255, 0.1);
    color: #FFFFFF;
}
"""


class NotificationBanner(QFrame):
    """Modern non-intrusive Windows 11 InfoBar / Toast notification banner."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("NotificationBanner")
        self.setFixedHeight(54)
        self.setVisible(False)
        self.action_callback = None
        self.banner_type = "success"

        self.auto_dismiss_timer = QTimer(self)
        self.auto_dismiss_timer.setSingleShot(True)
        self.auto_dismiss_timer.timeout.connect(self.hide_banner)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(10)

        # Icon
        self.icon_label = QLabel("✓")
        self.icon_label.setObjectName("BannerIcon")
        self.icon_label.setFixedWidth(24)
        self.icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.icon_label)

        # Text VBox (Title + Message)
        text_vbox = QVBoxLayout()
        text_vbox.setSpacing(1)
        text_vbox.setAlignment(Qt.AlignVCenter)

        self.title_label = QLabel("Notification Title")
        self.title_label.setObjectName("BannerTitle")

        self.msg_label = QLabel("Notification message details...")
        self.msg_label.setObjectName("BannerMessage")

        text_vbox.addWidget(self.title_label)
        text_vbox.addWidget(self.msg_label)
        layout.addLayout(text_vbox, 1)

        # Action Button (e.g. Open Folder)
        self.action_btn = QPushButton("Action")
        self.action_btn.setObjectName("BannerActionBtn")
        self.action_btn.setCursor(Qt.PointingHandCursor)
        self.action_btn.clicked.connect(self.on_action_clicked)
        layout.addWidget(self.action_btn)

        # Close Button (✕)
        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("BannerCloseBtn")
        self.close_btn.setFixedSize(26, 26)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setToolTip("Dismiss")
        self.close_btn.clicked.connect(self.hide_banner)
        layout.addWidget(self.close_btn)

    def show_message(
        self,
        title: str,
        message: str,
        banner_type: str = "success",
        action_text: Optional[str] = None,
        action_callback=None,
        auto_dismiss_ms: int = 6000,
    ):
        self.banner_type = banner_type
        self.action_callback = action_callback

        is_dark = False
        main_win = self.window()
        if hasattr(main_win, "is_dark_mode"):
            is_dark = main_win.is_dark_mode

        if banner_type == "success":
            self.icon_label.setText("✔")
            icon_color = "#5CD68D" if is_dark else "#0E6C38"
        elif banner_type == "warning":
            self.icon_label.setText("⚠")
            icon_color = "#FCE100" if is_dark else "#8A6500"
        elif banner_type == "error":
            self.icon_label.setText("✕")
            icon_color = "#FF7B7B" if is_dark else "#C5221F"
        else:
            self.icon_label.setText("ℹ")
            icon_color = "#4CC2FF" if is_dark else "#0067C0"

        self.icon_label.setStyleSheet(f"color: {icon_color}; font-size: 17px; font-weight: 700;")
        close_color = "#D4D4D4" if is_dark else "#475569"
        self.close_btn.setStyleSheet(f"color: {close_color}; font-size: 13px; font-weight: 700; border: none; background: transparent;")

        self.title_label.setText(title)
        self.msg_label.setText(message)

        if action_text and action_callback:
            self.action_btn.setText(action_text)
            self.action_btn.setVisible(True)
        else:
            self.action_btn.setVisible(False)

        self.setProperty("bannerType", banner_type)
        self.style().unpolish(self)
        self.style().polish(self)

        self.setVisible(True)

        if auto_dismiss_ms > 0:
            self.auto_dismiss_timer.start(auto_dismiss_ms)
        else:
            self.auto_dismiss_timer.stop()

    def on_action_clicked(self):
        if self.action_callback:
            self.action_callback()
        self.hide_banner()

    def hide_banner(self):
        self.auto_dismiss_timer.stop()
        self.setVisible(False)


class FileCardWidget(QFrame):
    """CloudConvert-style interactive queue row card."""
    remove_requested = Signal(object)  # emits self

    def __init__(self, file_path: Path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.output_path: Optional[Path] = None
        self.status = "ready"  # ready, converting, done, failed
        self.setObjectName("FileCard")
        self.setFixedHeight(64)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(12)

        # 1. Format Badge (e.g. HEIC, JPG, WEBP)
        ext = file_path.suffix.upper().replace(".", "") or "IMG"
        self.format_badge = QLabel(ext)
        self.format_badge.setObjectName("FormatBadge")
        self.format_badge.setAlignment(Qt.AlignCenter)
        self.format_badge.setFixedWidth(56)
        layout.addWidget(self.format_badge)

        # 2. File Name & Size
        name_vbox = QVBoxLayout()
        name_vbox.setSpacing(2)
        name_vbox.setAlignment(Qt.AlignVCenter)

        self.name_label = QLabel(file_path.name)
        self.name_label.setObjectName("FileName")
        self.name_label.setToolTip(str(file_path))

        try:
            size_kb = file_path.stat().st_size / 1024
            size_str = f"{size_kb / 1024:.2f} MB" if size_kb > 1024 else f"{size_kb:.1f} KB"
        except Exception:
            size_str = "Unknown size"

        self.size_label = QLabel(size_str)
        self.size_label.setObjectName("FileSize")

        name_vbox.addWidget(self.name_label)
        name_vbox.addWidget(self.size_label)
        layout.addLayout(name_vbox, 1)

        # 3. Conversion Direction Tag (to PNG)
        self.target_badge = QLabel("to  PNG")
        self.target_badge.setObjectName("TargetBadge")
        self.target_badge.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.target_badge)

        # 4. Status Badge
        self.status_badge = QLabel("Ready")
        self.status_badge.setObjectName("StatusBadge_ready")
        self.status_badge.setAlignment(Qt.AlignCenter)
        self.status_badge.setMinimumWidth(85)
        layout.addWidget(self.status_badge)

        # 5. Row "Open" Button (shows when finished)
        self.open_btn = QPushButton("Open")
        self.open_btn.setObjectName("RowOpenBtn")
        self.open_btn.setCursor(Qt.PointingHandCursor)
        self.open_btn.setVisible(False)
        self.open_btn.clicked.connect(self.open_result_file)
        layout.addWidget(self.open_btn)

        # 6. Delete / Remove Button (✕)
        self.remove_btn = QPushButton("✕")
        self.remove_btn.setObjectName("RemoveBtn")
        self.remove_btn.setFixedSize(28, 28)
        self.remove_btn.setCursor(Qt.PointingHandCursor)
        self.remove_btn.setToolTip("Remove from queue")
        self.remove_btn.clicked.connect(lambda: self.remove_requested.emit(self))
        layout.addWidget(self.remove_btn)

    def set_status(self, status: str, message: str = "", out_path: Optional[Path] = None):
        self.status = status
        if status == "ready":
            self.status_badge.setText("Ready")
            self.status_badge.setObjectName("StatusBadge_ready")
            self.status_badge.setToolTip("")
            self.open_btn.setVisible(False)
            self.remove_btn.setEnabled(True)
        elif status == "converting":
            self.status_badge.setText("Converting...")
            self.status_badge.setObjectName("StatusBadge_converting")
            self.status_badge.setToolTip("")
            self.open_btn.setVisible(False)
            self.remove_btn.setEnabled(False)
        elif status == "done":
            self.status_badge.setText("✓ Finished")
            self.status_badge.setObjectName("StatusBadge_done")
            self.output_path = out_path
            self.status_badge.setToolTip(f"Saved: {out_path}")
            self.open_btn.setVisible(True)
            self.remove_btn.setEnabled(True)
        elif status == "failed":
            self.status_badge.setText("✕ Failed")
            self.status_badge.setObjectName("StatusBadge_failed")
            self.status_badge.setToolTip(f"Error: {message}")
            self.open_btn.setVisible(False)
            self.remove_btn.setEnabled(True)

        # Force style re-polish for dynamic object names
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)

    def open_result_file(self):
        """Open the converted PNG file directly."""
        if not self.output_path or not self.output_path.exists():
            return
        try:
            if sys.platform == "win32":
                os.startfile(str(self.output_path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(self.output_path)])
            else:
                subprocess.Popen(["xdg-open", str(self.output_path)])
        except Exception as e:
            main_win = self.window()
            if hasattr(main_win, "show_banner"):
                main_win.show_banner("Error Opening File", str(e), banner_type="error")
            else:
                QMessageBox.warning(self, "Error", f"Could not open file: {e}")


class ConversionWorker(QThread):
    """Background worker for non-blocking batch conversion."""
    card_started = Signal(object)
    card_finished = Signal(object, bool, str, str)  # (card, success, out_path_str, error_message)
    overall_progress = Signal(int, int)             # (current, total)
    finished_batch = Signal(int, int, str)          # (success_count, fail_count, last_out_dir)

    def __init__(self, cards: List[FileCardWidget], save_mode: str, custom_dir: Optional[Path]):
        super().__init__()
        self.cards = cards
        self.save_mode = save_mode
        self.custom_dir = custom_dir
        self.is_cancelled = False

    def run(self):
        success_count = 0
        fail_count = 0
        last_out_dir = ""

        total = len(self.cards)
        for i, card in enumerate(self.cards):
            if self.is_cancelled:
                break

            self.card_started.emit(card)
            src_path = card.file_path

            if self.save_mode == "custom" and self.custom_dir:
                dest_dir = self.custom_dir
            else:
                dest_dir = src_path.parent

            last_out_dir = str(dest_dir)
            target_png = get_unique_output_path(dest_dir, src_path.stem)

            success, msg = convert_single_image(src_path, target_png)
            if success:
                success_count += 1
                self.card_finished.emit(card, True, str(target_png), "")
            else:
                fail_count += 1
                self.card_finished.emit(card, False, "", msg)

            self.overall_progress.emit(i + 1, total)

        self.finished_batch.emit(success_count, fail_count, last_out_dir)

    def cancel(self):
        self.is_cancelled = True


class DropZoneFrame(QFrame):
    """Custom Drag & Drop target area."""
    files_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DropZone")
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        file_paths = []
        for url in urls:
            path = Path(url.toLocalFile())
            file_paths.append(path)
        if file_paths:
            self.files_dropped.emit(file_paths)
            event.acceptProposedAction()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.window().on_browse_files()


class PngConverterApp(QMainWindow):
    """Main application window for the Universal PNG Converter."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Universal PNG Converter")
        self.setMinimumSize(940, 720)
        self.resize(1020, 780)

        # State
        self.is_dark_mode = False
        self.file_cards: List[FileCardWidget] = []
        self.worker: Optional[ConversionWorker] = None
        self.last_completed_folder = ""

        self.init_ui()
        self.apply_theme()

    def init_ui(self):
        central_widget = QWidget(self)
        central_widget.setObjectName("MainContainer")
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(14)

        # 1. Header with Title and Dark Mode Toggle
        header_card = QFrame()
        header_card.setObjectName("HeaderCard")
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(18, 14, 18, 14)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)
        title_label = QLabel("Universal PNG Converter")
        title_label.setObjectName("AppTitle")
        subtitle_label = QLabel(
            "Lossless conversion for Apple formats (HEIC, HEIF, Live Photos, DNG) & standard images to PNG"
        )
        subtitle_label.setObjectName("AppSubtitle")
        title_vbox.addWidget(title_label)
        title_vbox.addWidget(subtitle_label)

        header_layout.addLayout(title_vbox)
        header_layout.addStretch()

        self.theme_btn = QPushButton("🌙 Dark Mode")
        self.theme_btn.setObjectName("ThemeToggle")
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.clicked.connect(self.toggle_theme)
        header_layout.addWidget(self.theme_btn)

        main_layout.addWidget(header_card)

        # 2. Drag & Drop Area
        self.drop_zone = DropZoneFrame()
        drop_layout = QVBoxLayout(self.drop_zone)
        drop_layout.setContentsMargins(20, 22, 20, 22)
        drop_layout.setAlignment(Qt.AlignCenter)

        drop_title = QLabel("Drag & Drop Images or Folders Here")
        drop_title.setObjectName("DropZoneTitle")
        drop_title.setAlignment(Qt.AlignCenter)

        drop_hint = QLabel("Supports HEIC, HEIF, AVIF, DNG, WebP, JPG, TIFF, BMP, and more • Click to browse")
        drop_hint.setObjectName("DropZoneHint")
        drop_hint.setAlignment(Qt.AlignCenter)

        drop_layout.addWidget(drop_title)
        drop_layout.addWidget(drop_hint)
        self.drop_zone.files_dropped.connect(self.add_paths)

        main_layout.addWidget(self.drop_zone)

        # 3. Output Destination Settings Card
        settings_card = QFrame()
        settings_card.setObjectName("ContentCard")
        settings_layout = QVBoxLayout(settings_card)
        settings_layout.setContentsMargins(18, 14, 18, 14)
        settings_layout.setSpacing(10)

        dest_row = QHBoxLayout()
        self.radio_same_dir = QRadioButton("Save in same folder as original images (recommended)")
        self.radio_same_dir.setChecked(True)
        self.radio_custom_dir = QRadioButton("Save to custom output folder:")

        self.dest_group = QButtonGroup(self)
        self.dest_group.addButton(self.radio_same_dir)
        self.dest_group.addButton(self.radio_custom_dir)

        dest_row.addWidget(self.radio_same_dir)
        dest_row.addSpacing(20)
        dest_row.addWidget(self.radio_custom_dir)
        dest_row.addStretch()
        settings_layout.addLayout(dest_row)

        custom_folder_row = QHBoxLayout()
        self.custom_dir_input = QLineEdit()
        self.custom_dir_input.setPlaceholderText("Select a destination folder...")
        self.custom_dir_input.setEnabled(False)

        self.browse_folder_btn = QPushButton("Browse Folder...")
        self.browse_folder_btn.setEnabled(False)
        self.browse_folder_btn.clicked.connect(self.on_browse_output_folder)

        self.radio_custom_dir.toggled.connect(self.on_dest_mode_changed)

        custom_folder_row.addWidget(self.custom_dir_input)
        custom_folder_row.addWidget(self.browse_folder_btn)
        settings_layout.addLayout(custom_folder_row)

        main_layout.addWidget(settings_card)

        # 4. CloudConvert-Style Queue Container Card
        queue_card = QFrame()
        queue_card.setObjectName("ContentCard")
        queue_layout = QVBoxLayout(queue_card)
        queue_layout.setContentsMargins(18, 14, 18, 14)
        queue_layout.setSpacing(12)

        # Action Toolbar above the list
        toolbar_row = QHBoxLayout()
        self.stats_label = QLabel("0 images in queue")
        self.stats_label.setStyleSheet("font-weight: 600; font-size: 13px;")

        self.add_files_btn = QPushButton("+ Add Files...")
        self.add_files_btn.clicked.connect(self.on_browse_files)

        self.add_folder_btn = QPushButton("+ Add Folder...")
        self.add_folder_btn.clicked.connect(self.on_browse_input_folder)

        self.clear_queue_btn = QPushButton("Clear All")
        self.clear_queue_btn.clicked.connect(self.clear_queue)

        toolbar_row.addWidget(self.stats_label)
        toolbar_row.addStretch()
        toolbar_row.addWidget(self.add_files_btn)
        toolbar_row.addWidget(self.add_folder_btn)
        toolbar_row.addWidget(self.clear_queue_btn)
        queue_layout.addLayout(toolbar_row)

        # Notification Banner (InfoBar / Toast)
        self.banner = NotificationBanner()
        queue_layout.addWidget(self.banner)

        # Scroll Area holding the list of File Cards
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.cards_container = QWidget()
        self.cards_container.setObjectName("CardsContainer")
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(8, 8, 8, 8)
        self.cards_layout.setSpacing(8)

        # Empty State Placeholder
        self.empty_label = QLabel("No files in queue. Drag & drop images above or click '+ Add Files'.")
        self.empty_label.setObjectName("EmptyLabel")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.cards_layout.addWidget(self.empty_label)

        self.cards_layout.addStretch()
        self.scroll_area.setWidget(self.cards_container)
        queue_layout.addWidget(self.scroll_area, 1)

        # 5. Bottom Conversion Progress and Primary Action
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(12)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(8)

        self.open_folder_btn = QPushButton("Open Output Folder")
        self.open_folder_btn.setEnabled(False)
        self.open_folder_btn.clicked.connect(self.open_output_folder)

        self.convert_btn = QPushButton("Convert to PNG")
        self.convert_btn.setObjectName("PrimaryButton")
        self.convert_btn.setMinimumHeight(38)
        self.convert_btn.setMinimumWidth(160)
        self.convert_btn.setCursor(Qt.PointingHandCursor)
        self.convert_btn.clicked.connect(self.start_conversion)

        bottom_row.addWidget(self.progress_bar, 1)
        bottom_row.addWidget(self.open_folder_btn)
        bottom_row.addWidget(self.convert_btn)
        queue_layout.addLayout(bottom_row)

        main_layout.addWidget(queue_card, 1)

    def apply_theme(self):
        """Switch between Windows 11 Light and Dark styles."""
        if self.is_dark_mode:
            self.setStyleSheet(WINDOWS_DARK_QSS)
            self.theme_btn.setText("☀️ Light Mode")
        else:
            self.setStyleSheet(WINDOWS_LIGHT_QSS)
            self.theme_btn.setText("🌙 Dark Mode")

        if hasattr(self, "banner"):
            self.banner.style().unpolish(self.banner)
            self.banner.style().polish(self.banner)

    def show_banner(
        self,
        title: str,
        message: str,
        banner_type: str = "success",
        action_text: Optional[str] = None,
        action_callback=None,
        auto_dismiss_ms: int = 6000,
    ):
        """Display an inline Windows 11 toast/banner notification."""
        self.banner.show_message(
            title=title,
            message=message,
            banner_type=banner_type,
            action_text=action_text,
            action_callback=action_callback,
            auto_dismiss_ms=auto_dismiss_ms,
        )

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.apply_theme()

    def on_dest_mode_changed(self, is_custom: bool):
        self.custom_dir_input.setEnabled(is_custom)
        self.browse_folder_btn.setEnabled(is_custom)

    def on_browse_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Destination Folder")
        if folder:
            self.custom_dir_input.setText(folder)

    def on_browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Images to Convert",
            "",
            "All Images (*.heic *.heif *.avif *.dng *.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff *.gif);;All Files (*.*)",
        )
        if files:
            self.add_paths([Path(f) for f in files])

    def on_browse_input_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder Containing Images")
        if folder:
            self.add_paths([Path(folder)])

    def add_paths(self, paths: List[Path]):
        """Accepts file or folder paths and dynamically instantiates CloudConvert row cards."""
        new_files: List[Path] = []
        for path in paths:
            if path.is_file():
                if is_supported_image(path):
                    new_files.append(path)
            elif path.is_dir():
                for root, _, files in os.walk(path):
                    for file in files:
                        p = Path(root) / file
                        if is_supported_image(p):
                            new_files.append(p)

        existing_set = {card.file_path for card in self.file_cards}
        added_any = False

        for f in new_files:
            if f not in existing_set:
                card = FileCardWidget(f)
                card.remove_requested.connect(self.remove_file_card)

                # Insert before stretch item at the end of cards_layout
                insert_pos = max(0, self.cards_layout.count() - 1)
                self.cards_layout.insertWidget(insert_pos, card)
                self.file_cards.append(card)
                existing_set.add(f)
                added_any = True

        if added_any:
            self.empty_label.setVisible(False)
            self.update_stats()

    def remove_file_card(self, card: FileCardWidget):
        """Removes an individual file card from the queue."""
        if self.worker and self.worker.isRunning() and card.status == "converting":
            self.show_banner(
                "Cannot Remove Item",
                "This image is currently being converted. Please wait.",
                banner_type="warning",
                auto_dismiss_ms=4000,
            )
            return

        if card in self.file_cards:
            self.file_cards.remove(card)
            self.cards_layout.removeWidget(card)
            card.deleteLater()

        if len(self.file_cards) == 0:
            self.empty_label.setVisible(True)

        self.update_stats()

    def clear_queue(self):
        """Clears all file cards from the queue."""
        if self.worker and self.worker.isRunning():
            self.show_banner(
                "Cannot Clear Queue",
                "Conversion is currently in progress. Please wait until it completes.",
                banner_type="warning",
                auto_dismiss_ms=4000,
            )
            return

        for card in list(self.file_cards):
            self.cards_layout.removeWidget(card)
            card.deleteLater()

        self.file_cards.clear()
        self.empty_label.setVisible(True)
        self.progress_bar.setValue(0)
        self.open_folder_btn.setEnabled(False)
        self.update_stats()

    def update_stats(self):
        count = len(self.file_cards)
        self.stats_label.setText(f"{count} image{'s' if count != 1 else ''} in queue")
        self.convert_btn.setEnabled(count > 0 and (self.worker is None or not self.worker.isRunning()))
        self.clear_queue_btn.setEnabled(count > 0 and (self.worker is None or not self.worker.isRunning()))

    def start_conversion(self):
        # Convert any cards that are ready or failed
        pending_cards = [card for card in self.file_cards if card.status in ("ready", "failed")]
        if not pending_cards:
            if not self.file_cards:
                self.show_banner(
                    "Queue Empty",
                    "Please drag & drop images or click '+ Add Files' to get started.",
                    banner_type="info",
                    auto_dismiss_ms=4000,
                )
            else:
                self.show_banner(
                    "All Converted",
                    "All images in the queue have already been converted.",
                    banner_type="info",
                    action_text="Open Folder",
                    action_callback=self.open_output_folder,
                    auto_dismiss_ms=5000,
                )
            return

        save_mode = "custom" if self.radio_custom_dir.isChecked() else "same"
        custom_dir = None
        if save_mode == "custom":
            folder_text = self.custom_dir_input.text().strip()
            if not folder_text:
                self.show_banner(
                    "Missing Output Folder",
                    "Please select a destination folder using 'Browse Folder...'",
                    banner_type="warning",
                    auto_dismiss_ms=5000,
                )
                return
            custom_dir = Path(folder_text)
            custom_dir.mkdir(parents=True, exist_ok=True)

        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(pending_cards))

        # Lock UI during processing
        self.convert_btn.setEnabled(False)
        self.convert_btn.setText("Converting...")
        self.add_files_btn.setEnabled(False)
        self.add_folder_btn.setEnabled(False)
        self.clear_queue_btn.setEnabled(False)
        self.open_folder_btn.setEnabled(False)

        # Launch background worker
        self.worker = ConversionWorker(pending_cards, save_mode, custom_dir)
        self.worker.card_started.connect(self.on_card_started)
        self.worker.card_finished.connect(self.on_card_finished)
        self.worker.overall_progress.connect(self.on_overall_progress)
        self.worker.finished_batch.connect(self.on_finished_batch)
        self.worker.start()

    def on_card_started(self, card: FileCardWidget):
        card.set_status("converting")

    def on_card_finished(self, card: FileCardWidget, success: bool, out_path_str: str, error_message: str):
        if success:
            card.set_status("done", out_path=Path(out_path_str))
        else:
            card.set_status("failed", message=error_message)

    def on_overall_progress(self, current: int, total: int):
        self.progress_bar.setValue(current)

    def on_finished_batch(self, success_count: int, fail_count: int, last_out_dir: str):
        self.convert_btn.setEnabled(True)
        self.convert_btn.setText("Convert to PNG")
        self.add_files_btn.setEnabled(True)
        self.add_folder_btn.setEnabled(True)
        self.clear_queue_btn.setEnabled(True)

        self.last_completed_folder = last_out_dir
        if last_out_dir and Path(last_out_dir).exists():
            self.open_folder_btn.setEnabled(True)

        # Modern Windows 11 Toast / InfoBar Notification
        if fail_count == 0:
            self.show_banner(
                title="Conversion Complete!",
                message=f"Successfully converted {success_count} image{'s' if success_count != 1 else ''} to lossless PNG.",
                banner_type="success",
                action_text="Open Folder",
                action_callback=self.open_output_folder,
                auto_dismiss_ms=8000,
            )
        else:
            self.show_banner(
                title="Completed with Warnings",
                message=f"{success_count} succeeded, {fail_count} failed. Hover over '✕ Failed' badges for details.",
                banner_type="warning",
                action_text="Open Folder",
                action_callback=self.open_output_folder,
                auto_dismiss_ms=10000,
            )

    def open_output_folder(self):
        """Open the output destination folder in Windows File Explorer."""
        if not self.last_completed_folder or not os.path.exists(self.last_completed_folder):
            self.show_banner(
                "Folder Unavailable",
                "No output directory available yet. Convert images first.",
                banner_type="info",
                auto_dismiss_ms=4000,
            )
            return
        try:
            if sys.platform == "win32":
                os.startfile(self.last_completed_folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", self.last_completed_folder])
            else:
                subprocess.Popen(["xdg-open", self.last_completed_folder])
        except Exception as e:
            self.show_banner(
                "Error",
                f"Could not open directory: {e}",
                banner_type="error",
                auto_dismiss_ms=5000,
            )


def main():
    missing = []
    if Image is None:
        missing.append("Pillow")
    if pillow_heif is None:
        missing.append("pillow-heif (required for Apple HEIC/HEIF)")
    if "PySide6" not in sys.modules:
        missing.append("PySide6")

    if missing:
        print("\n[!] Missing required dependencies to run Universal PNG Converter:")
        for pkg in missing:
            print(f"    - {pkg}")
        print("\nPlease run the following command to install them:")
        print("    pip install Pillow pillow-heif PySide6\n")
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = PngConverterApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
