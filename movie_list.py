"""Custom ComboBox with searching."""

from PySide6.QtCore import Qt, QSortFilterProxyModel, QSize
from PySide6.QtWidgets import QComboBox, QCompleter


class MovieListWidget(QComboBox):
    """Custom ComboBox with searching class."""

    def __init__(self, parent=None):
        """Initialize a new MovieListWidget object."""
        super().__init__(parent)
        self.setFocusPolicy(Qt.ClickFocus)
        self.setEditable(True)

        # prevent insertions into combobox
        self.setInsertPolicy(QComboBox.NoInsert)

        # filter model for matching items
        self.pFilterModel = QSortFilterProxyModel(self)
        self.pFilterModel.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.pFilterModel.setSourceModel(self.model())

        # completer that uses filter model
        self.completer = QCompleter(self.pFilterModel, self)
        self.completer.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        self.setCompleter(self.completer)

        # connect signals
        self.lineEdit().textEdited[str].connect(self.pFilterModel.setFilterFixedString)
        self.completer.activated.connect(self.on_completer_activated)

    def on_completer_activated(self, text):
        """Callback for handling auto-complete."""
        if text:
            index = self.findText(text)
            self.setCurrentIndex(index)
            self.activated.emit(index)

    def setModel(self, model):
        """Update the filter model and use that to update the main model."""
        super().setModel(model)
        self.pFilterModel.setSourceModel(model)
        self.completer.setModel(self.pFilterModel)

    def setModelColumn(self, column):
        """Set column for both the main and the filter models."""
        self.completer.setCompletionColumn(column)
        self.pFilterModel.setFilterKeyColumn(column)
        super().setModelColumn(column)

    def minimumSizeHint(self):
        """Override to have no minimum width."""
        return QSize(1, super().minimumSizeHint().height())
