"""The main entry point."""

import logging
import sys

from PySide6.QtWidgets import QApplication

from .options import DEFAULT_QSS
from .window import MainWindow


def main():
    """Main function to run the GUI."""
    app = QApplication(sys.argv)

    # Set the stylesheet
    app.setStyleSheet(DEFAULT_QSS)

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
    logger.info("Running main loop")
    return app.exec()


if __name__ == "__main__":
    logger = logging.getLogger("videowall")
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
