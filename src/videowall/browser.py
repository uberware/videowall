"""Browser with auto-complete dropdown list to select with."""

import typing
from pathlib import Path

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout, QWidget

from .options import OPTIONS
from .searchable_list import SearchableListBox


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
    items = {it.stem: it for it in OPTIONS.spec_folder.glob("*.json") if not it.name.startswith(".")}
    browser = Browser(parent, list(items.keys()))
    if browser.exec() == QDialog.Accepted:
        return items[browser.list_box.currentText()]
