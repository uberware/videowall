"""The main entry point."""

import logging
import sys

from PySide6.QtWidgets import QApplication

from videowall.options import DEFAULT_QSS
from videowall.window import MainWindow


def main():
    """Main function to run the GUI."""
    app = QApplication(sys.argv)

    # Set the stylesheet
    app.setStyleSheet(DEFAULT_QSS)

    # Set a smaller point size
    app_font = app.font()
    app_font.setPointSize(10)
    app.setFont(app_font)

    window = MainWindow()
    window.show()
    logger.info("Running main loop")
    return app.exec()


if __name__ == "__main__":
    logger = logging.getLogger("videowall")
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
