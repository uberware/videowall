"""Browser with auto-complete dropdown list to select with."""

import logging
import typing
from pathlib import Path

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout, QWidget

from videowall import content
from videowall.searchable_list import SearchableListBox

logger = logging.getLogger("videowall")


class Browser(QDialog):
    """A browser dialog box."""

    def __init__(self, parent: QWidget, items):
        """Initialize a new Browser object."""
        super().__init__(parent)
        self.setWindowTitle("Load")
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.addWidget(QLabel("Select a layout to load"))
        self.list_box = SearchableListBox(self)
        self.list_box.addItems(items)
        self.list_box.setMinimumWidth(200)
        layout.addWidget(self.list_box)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


def browse_for_spec(parent: QWidget) -> typing.Optional[Path]:
    """Open the Load dialog box and load a selected layout.

    Returns:
        the selected Path or None if canceled
    """
    browser = Browser(parent, content.get_files("layout"))
    if browser.exec() == QDialog.Accepted:
        selected = content.get_path("layout", browser.list_box.currentText())
        logger.info(f"Browser selected: {selected}")
        return selected
