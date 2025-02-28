import os
import numpy as np
from PySide6.QtGui import (
    QColor,
    QCursor,
    QPixmap,
    QImage,
)
from PySide6.QtCore import QSize
from qtpy import QtGui, QtWidgets, QtCore
import qtawesome as qta
import imageio.v3 as iio  # Use imageio.v3
from qimage2ndarray import array2qimage, rgb_view, alpha_view
from clickpoints.includes.Tools import HTMLColorToRGB, IconFromFile


def qicon_to_numpy(icon: QtGui.QIcon) -> np.ndarray:
    """
    Converts a QIcon to a NumPy array using PySide6.


    Args:
    icon: The QIcon to convert.


    Returns:
    A NumPy array representing the QIcon. Returns None if the icon is invalid
    or if the conversion fails.
    """
    if icon is None or icon.isNull():
        return None

    # Get the pixmap from the icon (you might want to choose a specific size)
    available_sizes = icon.availableSizes()

    pixmap = icon.pixmap(QSize(16, 16))  # Use the first available size

    # Ensure the pixmap is valid
    if pixmap.isNull():
        return None

    # Get the image from the pixmap
    image = pixmap.toImage()

    return np.concat((rgb_view(image), alpha_view(image)[:, :, None]), axis=2)

def setCursor(window, cursor_name, color):
    """Sets the cursor for the image display."""

    if cursor_name is None:
        window.ImageDisplay.unsetCursor()
        return

    try:
        # 1. Create the base icon (either from FontAwesome or a file)
        if cursor_name.startswith("fa5s."):
            icon = qta.icon(
                cursor_name, color=QColor(*HTMLColorToRGB(color))
            )
        else:
            icon = IconFromFile(
                cursor_name, color=QColor(*HTMLColorToRGB(color))
            )

        icon_array = qicon_to_numpy(icon)

        # 4. Load the base cursor image
        cursor_path = os.path.join(os.environ["CLICKPOINTS_ICON"], "Cursor.png")
        cursor_base = iio.imread(cursor_path)  # Use imageio.v3

        # 5. Compose the images
        cursor_final = np.zeros(
            (cursor_base.shape[0] + icon_array.shape[0], cursor_base.shape[1] + icon_array.shape[1], 4),
            dtype=cursor_base.dtype,
        )
        cursor_final[: cursor_base.shape[0], : cursor_base.shape[1], :] = cursor_base
        y, x = (cursor_base.shape[0] - 6, cursor_base.shape[1] - 4)
        cursor_final[
            y : y + icon_array.shape[0], x : x + icon_array.shape[1], :
        ] = icon_array

        # 6. Create the final QCursor
        final_image = array2qimage(cursor_final)
        final_pixmap = QPixmap.fromImage(final_image)
        cursor = QCursor(final_pixmap, 0, 0)

        # 7. Set the cursor
        window.ImageDisplay.setCursor(cursor)

    except Exception as e:
        print(f"Error setting cursor: {e}")  # Handle exceptions gracefully
        window.ImageDisplay.unsetCursor()  # Revert to default cursor
