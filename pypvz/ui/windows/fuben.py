from time import sleep
from threading import Event
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QComboBox,
    QCheckBox,
    QApplication,
)
from PyQt6 import QtGui
from PyQt6.QtCore import Qt, pyqtSignal, QThread

from ..wrapped import QLabel
from ..user import UserSettings
from ... import FubenRequest


class FubenSelectWindow(QMainWindow):
    def __init__(self, usersettings: UserSettings, parent=None):
        super().__init__(parent)
        self.usersettings = usersettings
        self.fuben_layer_cache = {}

    def init_ui(self):
        self.setWindowTitle("练级设置")

        # 将窗口居中显示，宽度为显示器宽度的30%，高度为显示器高度的50%
        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.3), int(screen_size.height() * 0.5))
        self.move(int(screen_size.width() * 0.35), int(screen_size.height() * 0.25))

        main_widget = QWidget()
        main_layout = QHBoxLayout()

        cave_type_widget = QWidget()
        cave_type_widget.setFixedWidth(int(self.width() * 0.4))
        cave_type_layout = QVBoxLayout()
        cave_type_layout.addWidget(QLabel("副本层级"))
        self.cave_type_list_widget = QListWidget()
        cave_type_layout.addWidget(self.cave_type_list_widget)
        cave_type_widget.setLayout(cave_type_layout)
        self.cave_type_list_widget.itemClicked.connect(
            self.cave_type_list_widget_clicked
        )
        for i, name in enumerate(["炽热沙漠", "幽静树海", "冰火世界", "死亡峡谷", "荒原驿道"]):
            item = QListWidgetItem("{}".format(name))
            item.setData(Qt.ItemDataRole.UserRole, i + 1)
            self.cave_type_list_widget.addItem(item)
        main_layout.addWidget(cave_type_widget)

        cave_widget = QWidget()
        cave_widget.setFixedWidth(int(self.width() * 0.4))
        cave_layout = QVBoxLayout()
        cave_layout.addWidget(QLabel("洞口"))
        self.cave_list_widget = QListWidget()
        self.cave_list_widget.itemClicked.connect(self.cave_list_widget_clicked)
        cave_layout.addWidget(self.cave_list_widget)
        cave_widget.setLayout(cave_layout)
        main_layout.addWidget(cave_widget)

        # widget3 = QWidget()
        # widget3_layout = QVBoxLayout()
        # self.need_use_sand = QCheckBox("使用时之沙")
        # self.need_use_sand.setChecked(False)
        # widget3_layout.addWidget(self.need_use_sand)
        # widget3_1_layout = QHBoxLayout()
        # widget3_1_layout.addWidget(QLabel("洞口难度:"))
        # self.difficulty_choice = QComboBox()
        # difficulty = ["简单", "普通", "困难"]
        # self.difficulty_choice.addItems(difficulty)
        # self.difficulty_choice.setCurrentIndex(2)
        # widget3_1_layout.addWidget(self.difficulty_choice)
        # widget3_layout.addLayout(widget3_1_layout)
        # if self.usersettings.cfg.server == "私服":
        #     result = self.usersettings.challenge4Level.caveMan.switch_garden_layer(
        #         1, self.usersettings.logger
        #     )
        #     widget3_2_layout = QHBoxLayout()
        #     widget3_2_layout.addWidget(QLabel("选择花园层级:"))
        #     self.usersettings.logger.log(result["result"])
        #     if not result["success"]:
        #         self.close()
        #     self.current_garden_layer_choice = QComboBox()
        #     self.current_garden_layer_choice.addItems(["1", "2", "3", "4"])
        #     self.current_garden_layer_choice.setCurrentIndex(0)
        #     self.current_garden_layer_choice.currentIndexChanged.connect(
        #         self.current_garden_layer_choice_currentIndexChanged
        #     )
        #     widget3_2_layout.addWidget(self.current_garden_layer_choice)
        #     widget3_layout.addLayout(widget3_2_layout)
        # widget3.setLayout(widget3_layout)
        # main_layout.addWidget(widget3)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
    def cave_type_list_widget_clicked(self, item):
        self.cave_list_widget.clear()
        layer = item.data(Qt.ItemDataRole.UserRole)
        if self.fuben_layer_cache.get(layer, None) is None:
            caves = self.usersettings.fuben_man.get_caves(layer)
            self.fuben_layer_cache[layer] = caves
        else:
            caves = self.fuben_layer_cache[layer]
        for cave in caves:
            item = QListWidgetItem(cave.name)
            item.setData(Qt.ItemDataRole.UserRole, cave)
            self.cave_list_widget.addItem(item)
            
    def cave_list_widget_clicked(self, item):
        cave = item.data(Qt.ItemDataRole.UserRole)


