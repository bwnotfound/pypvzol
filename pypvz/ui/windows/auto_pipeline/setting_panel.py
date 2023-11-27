from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLineEdit,
)
from PyQt6 import QtGui

from ...wrapped import QLabel


class OpenBoxWidget(QWidget):
    
    def __init__(self, pipeline):
        super().__init__()
        self.pipeline = pipeline
        self.init_ui()
        
    def init_ui(self):
        self.main_layout = QVBoxLayout()
        
        self.main_layout.addWidget(QLabel("设置一次开魔神箱的数量"))
        self.inputbox = QLineEdit()
        self.inputbox.setText(str(self.pipeline.amount))
        self.inputbox.setValidator(QtGui.QIntValidator(1, 99999))
        self.inputbox.textChanged.connect(self.inputbox_text_changed)
        self.main_layout.addWidget(self.inputbox)
        
        self.setLayout(self.main_layout)

    def inputbox_text_changed(self):
        text = self.inputbox.text()
        amount = int(text) if text != "" else 0
        self.pipeline.amount = amount
        