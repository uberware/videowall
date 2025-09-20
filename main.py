"""The main entry point."""

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Set the stylesheet
    stylesheet = Path(__file__).parent / "style.qss"
    app.setStyleSheet(stylesheet.read_text())

    # Set a smaller point size
    app_font = app.font()
    app_font.setPointSize(10)
    app.setFont(app_font)

    # videos = [
    #     "/Volumes/Movies-4/Godzilla.vs.Kong.2021.1080p.x264.ac3-nibo.mp4",
    #     "/Volumes/Movies-4/Groundhog.Day.1993.REMASTERED.1080p.BluRay.6CH.ShAaNiG.mp4",
    #     "/Volumes/Movies-4/Jumanji (1995).1080p-x264-ac3.Nibo.mp4",
    #     "/Volumes/Movies-4/Jumanji (2017).1080p-x264-ac3.Nibo.mp4",
    # ]

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
