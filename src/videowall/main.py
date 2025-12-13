"""The main entry point."""

import argparse
import logging
import sys

from PySide6.QtWidgets import QApplication

from videowall.options import DEFAULT_QSS
from videowall.window import MainWindow


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-v", "--verbose", action="store_true", help="More logging.")
    group.add_argument("-q", "--quiet", action="store_true", help="Less logging.")
    return parser.parse_args()


def main():
    """Main function to run the GUI."""
    # Get the command line overrides
    parsed_args = parse_args()

    # Set up the logger
    logger = logging.getLogger("videowall")
    if parsed_args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    elif not parsed_args.quiet:
        logging.basicConfig(level=logging.INFO)

    # Get the Qt Application
    app = QApplication(sys.argv)
    # Set the stylesheet
    app.setStyleSheet(DEFAULT_QSS)
    # Set a smaller point size
    app_font = app.font()
    app_font.setPointSize(10)
    app.setFont(app_font)

    # Show the window and run the app loop
    window = MainWindow()
    window.show()
    logger.info("Running main loop")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
