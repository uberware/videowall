"""The VideoWall is a collection of Players in a single row or column."""

import logging
import typing

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter, QVBoxLayout, QWidget

from videowall.player import Player

logger = logging.getLogger("videowall")


class VideoWall(QWidget):
    """A widget class to contain a single row or column of Players."""

    def __init__(self, spec: dict, parent: typing.Optional[QWidget] = None):
        """Initialize a new VideoWall object.

        Args:
            spec: A VideoWall layout spec dictionary
            parent: Optional parent QWidget
        """
        super().__init__(parent)

        # Determine orientation from spec
        orientation_str = spec.get("orientation", "horizontal").lower()
        self.orientation = Qt.Horizontal if orientation_str.startswith("h") else Qt.Vertical
        items = spec.get("items", [])
        if not items:
            items = [None]
        self.item_count = len(items)
        sizes = spec.get("sizes", [])
        logger.debug(f"Initializing VideoWall {self} {items}")
        # Build the cells
        self.splitter = QSplitter(self.orientation, self)
        for item in items:
            self.append_item(item)
        # Resize the cells
        if len(sizes) < len(items):
            sizes = self.arrange_cells()
        self.splitter.setSizes(sizes)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.splitter)

    @property
    def spec(self) -> dict:
        """The current layout spec dictionary for this VideoWall object."""
        result = {
            "type": "VideoWall",
            "orientation": "horizontal" if self.orientation == Qt.Horizontal else "vertical",
            "items": [],
            "sizes": self.splitter.sizes(),
        }
        for widget in each_item_in(self):
            result["items"].append(widget.spec)
        return result

    def append_item(self, item: typing.Union[None, dict, Player]):
        """Append a Player to this row/column.

        Args:
            item: an existing Player object, a Player or Video wall spec dictionary, or None for an empty Player
        """
        logger.debug(f"Append item: {item}")
        if not item:
            item = {"type": "Player"}
        if not isinstance(item, (dict, Player)):
            raise TypeError(f"Invalid Item: {item}")
        if isinstance(item, Player) or item["type"] == "Player":
            # a Player cell
            player = item if isinstance(item, Player) else Player(item)
            player.setParent(self)
            player.split_horizontal = lambda: self.handle_split(player, Qt.Horizontal)
            player.split_vertical = lambda: self.handle_split(player, Qt.Vertical)
            self.splitter.addWidget(player)
        elif item["type"] == "VideoWall":
            # nested VideoWall
            child = VideoWall(item)
            self.splitter.addWidget(child)
        else:
            raise TypeError(f"Unknown spec type: {item['type']}")

    def arrange_cells(self) -> list:
        """Return the list of sizes to distribute the cells evenly."""
        length = self.width() if self.orientation == Qt.Horizontal else self.height()
        cell_size = length // self.item_count
        extra_cells = self.item_count - 1
        sizes = [cell_size] * extra_cells
        sizes.append(length - extra_cells * cell_size)
        logger.debug(f"Arranged: {sizes}")
        return sizes

    def handle_split(self, player, new_orientation):
        """Callback for the split operation to add a new Player or split in a new direction."""
        # Find which index this player occupies in the splitter
        index = self.splitter.indexOf(player)
        if index == -1:
            logger.debug(f"split: {player} not found")
            return  # not found
        if new_orientation == self.orientation:
            # Add a new widget after this one
            logger.debug("split: same direction")
            self.item_count += 1
            self.append_item(None)
            self.splitter.setSizes(self.arrange_cells())
        else:
            logger.debug("split: new direction")
            # Build a new nested splitter with two items:
            # the original player and a new blank Player
            new_spec = {
                "orientation": "horizontal" if new_orientation == Qt.Horizontal else "vertical",
                "items": [player, None],  # second one is a blank player
            }
            # Actually create the nested VideoWall widget
            nested = VideoWall(new_spec, parent=self.splitter)
            # Insert it back in the same place
            self.splitter.insertWidget(index, nested)

    def play(self):
        """Notify all child Player and VideoWall widgets to start playback."""
        for widget in each_item_in(self):
            widget.play()

    def pause(self):
        """Notify all child Player and VideoWall widgets to pause playback."""
        for widget in each_item_in(self):
            widget.pause()

    def mute(self):
        """Notify all child Player and VideoWall widgets to mute."""
        for widget in each_item_in(self):
            widget.mute()

    def unmute(self):
        """Notify all child Player and VideoWall widgets to unmute."""
        for widget in each_item_in(self):
            widget.unmute()

    def closeEvent(self, event):
        """Override the close event to ensure the children close cleanly."""
        super().closeEvent(event)
        logger.debug(f"VideoWall {self} Closing")
        for widget in each_item_in(self, reverse=True):
            widget.close()
        self.deleteLater()


def each_item_in(video_wall: VideoWall, reverse: bool = False) -> typing.Iterator[typing.Union[VideoWall, Player]]:
    """Generator that yields each child item in the splitter."""
    index_list = range(video_wall.splitter.count())
    if reverse:
        index_list = reversed(index_list)
    for i in index_list:
        yield video_wall.splitter.widget(i)
