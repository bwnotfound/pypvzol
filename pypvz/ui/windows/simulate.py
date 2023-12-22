from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTabWidget,
    QComboBox,
    QPlainTextEdit,
)
from PyQt6 import QtGui
from PyQt6.QtCore import Qt

from ..wrapped import QLabel
from ...utils.calc import simulate_imprisonment


class SimulateWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("模拟面板")

        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.6), int(screen_size.height() * 0.7))
        self.move(int(screen_size.width() * 0.2), int(screen_size.height() * 0.15))

        main_tab_widget = QTabWidget()
        self.setCentralWidget(main_tab_widget)

        self.simulate_imprisonment_widget = QWidget()
        self.simulate_imprisonment_widget.setFixedWidth(int(self.width() * 0.3))
        self.simulate_imprisonment_widget.setFixedHeight(int(self.height() * 0.3))
        self.simulate_imprisonment_layout = QVBoxLayout()
        self.simulate_imprisonment_widget.setLayout(self.simulate_imprisonment_layout)
        main_tab_widget.addTab(self.simulate_imprisonment_widget, "禁锢模拟")
        layout = QHBoxLayout()
        layout.addWidget(QLabel("满级禁锢数量:"))
        self.simulate_imprisonment_book_choice = QComboBox()
        self.simulate_imprisonment_book_choice.addItems([str(i) for i in range(0, 11)])
        self.simulate_imprisonment_book_choice.setCurrentIndex(0)
        layout.addWidget(self.simulate_imprisonment_book_choice)
        layout.addWidget(QLabel("炮灰日光等级:"))
        self.simulate_imprisonment_riguang_choice = QComboBox()
        self.simulate_imprisonment_riguang_choice.addItems(
            [str(i) for i in range(0, 11)]
        )
        self.simulate_imprisonment_riguang_choice.setCurrentIndex(0)
        layout.addWidget(self.simulate_imprisonment_riguang_choice)
        self.simulate_imprisonment_layout.addLayout(layout)
        start_simulate_btn = QPushButton("开始模拟")
        start_simulate_btn.clicked.connect(self.start_simulate_imprisonment)
        self.simulate_imprisonment_layout.addWidget(start_simulate_btn)
        self.simulate_imprisonment_layout.addWidget(QLabel("模拟结果"))
        self.simulate_imprisonment_result_textbox = QPlainTextEdit()
        self.simulate_imprisonment_result_textbox.setReadOnly(True)
        # 设置为可以选中文字
        self.simulate_imprisonment_result_textbox.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.simulate_imprisonment_layout.addWidget(
            self.simulate_imprisonment_result_textbox
        )

    def start_simulate_imprisonment(self):
        n = int(self.simulate_imprisonment_book_choice.currentText())
        riguang_level = int(self.simulate_imprisonment_riguang_choice.currentText())
        result = simulate_imprisonment(n, riguang_level)
        self.simulate_imprisonment_result_textbox.clear()
        self.simulate_imprisonment_result_textbox.appendPlainText(
            f"平均回合数: {int(result)}"
        )
