"""Custom ComboBox with searching."""

from PySide6.QtCore import QSize, QSortFilterProxyModel, Qt
from PySide6.QtWidgets import QComboBox, QCompleter


class SearchableListBox(QComboBox):
    """Custom ComboBox with searching class."""

    def __init__(self, parent=None):
        """Initialize a new MovieListWidget object."""
        super().__init__(parent)
        self.setFocusPolicy(Qt.ClickFocus)
        self.setEditable(True)

        # prevent insertions into combobox
        self.setInsertPolicy(QComboBox.NoInsert)

        # filter model for matching items
        self.filter_model = QSortFilterProxyModel(self)
        self.filter_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.filter_model.setSourceModel(self.model())

        # completer that uses filter model
        self.completer = QCompleter(self.filter_model, self)
        self.completer.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        self.setCompleter(self.completer)

        # connect signals
        self.lineEdit().textEdited[str].connect(self.filter_model.setFilterFixedString)
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
        self.filter_model.setSourceModel(model)
        self.completer.setModel(self.filter_model)

    def setModelColumn(self, column):
        """Set column for both the main and the filter models."""
        self.completer.setCompletionColumn(column)
        self.filter_model.setFilterKeyColumn(column)
        super().setModelColumn(column)

    def minimumSizeHint(self):
        """Override to have no minimum width."""
        return QSize(1, super().minimumSizeHint().height())
