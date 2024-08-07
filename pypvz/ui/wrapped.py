import threading

from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt

normal_font = QFont("Microsoft YaHei", pointSize=10)


class QLabel(QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFont(normal_font)

    def setFont(self, a0) -> None:
        super().setFont(a0)
        return self

    def setText(self, a0) -> None:
        super().setText(a0)
        return self

    def setPixmap(self, a0: QPixmap) -> None:
        super().setPixmap(a0)
        return self

    def setAlignment(self, a0: Qt.AlignmentFlag) -> None:
        super().setAlignment(a0)
        return self
