from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTabWidget,
    QComboBox,
    QPlainTextEdit,
    QListWidget,
    QListWidgetItem,
)
from PyQt6 import QtGui
from PyQt6.QtCore import Qt

from ..user.usersettings import UserSettings
from ..wrapped import QLabel


class CommandSettingWindow(QMainWindow):
    def __init__(self, usersettings: UserSettings, parent=None):
        super().__init__(parent=parent)
        self.usersettings = usersettings
        self.init_ui()
        self.refresh_command_list()

    def init_ui(self):
        self.setWindowTitle("指令设置面板")

        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.4), int(screen_size.height() * 0.6))
        self.move(int(screen_size.width() * 0.3), int(screen_size.height() * 0.2))

        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        self.command_list = QListWidget()
        self.command_list.setFixedWidth(int(self.width() * 0.5))
        self.command_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        main_layout.addWidget(self.command_list)

        command_tab_widget = QTabWidget()
        main_layout.addWidget(command_tab_widget)

        crystal_widget = QWidget()
        crystal_layout = QVBoxLayout()
        crystal_widget.setLayout(crystal_layout)
        command_tab_widget.addTab(crystal_widget, "宝石指令")
        layout = QHBoxLayout()
        layout.addWidget(QLabel("宝石种类:"))
        self.crystal_type_combobox = QComboBox()
        self.crystal_type_combobox.addItems(
            [
                "红宝石",
                "蓝宝石",
                "烟晶石",
                "白宝石",
                "绿宝石",
                "日光石",
                "黑曜石",
                "紫晶石",
                "天河石",
            ]
        )
        self.crystal_type_combobox.setCurrentIndex(5)
        layout.addWidget(self.crystal_type_combobox)
        crystal_layout.addLayout(layout)
        layout = QHBoxLayout()
        layout.addWidget(QLabel("关卡序号:"))
        self.crystal_level_combobox = QComboBox()
        self.crystal_level_combobox.addItems([str(i) for i in range(1, 12 * 5 + 1)])
        self.crystal_level_combobox.setCurrentIndex(0)
        layout.addWidget(self.crystal_level_combobox)
        crystal_layout.addLayout(layout)
        self.crystal_amount = QComboBox()
        self.crystal_amount.addItems(["100", "1000", "10000"])
        self.crystal_amount.setCurrentIndex(0)
        crystal_layout.addWidget(self.crystal_amount)
        crystal_set_btn = QPushButton("设置指令")
        crystal_set_btn.clicked.connect(self.crystal_set_btn_clicked)
        crystal_layout.addWidget(crystal_set_btn)

        dungeon_widget = QWidget()
        dungeon_layout = QVBoxLayout()
        dungeon_widget.setLayout(dungeon_layout)
        command_tab_widget.addTab(dungeon_widget, "打洞指令")
        layout = QHBoxLayout()
        layout.addWidget(QLabel("洞口种类:"))
        self.dungeon_type_combobox = QComboBox()
        self.dungeon_type_combobox.addItems(["暗洞", "公洞", "个洞"])
        self.dungeon_type_combobox.setCurrentIndex(1)
        layout.addWidget(self.dungeon_type_combobox)
        dungeon_layout.addLayout(layout)
        layout = QHBoxLayout()
        layout.addWidget(QLabel("关卡序号:"))
        self.dungeon_level_combobox = QComboBox()
        self.dungeon_level_combobox.addItems([str(i) for i in range(1, 5 * 4 * 12 + 1)])
        self.dungeon_level_combobox.setCurrentIndex(0)
        layout.addWidget(self.dungeon_level_combobox)
        dungeon_layout.addLayout(layout)
        self.dungeon_amount = QComboBox()
        self.dungeon_amount.addItems(["100", "1000", "10000"])
        self.dungeon_amount.setCurrentIndex(0)
        dungeon_layout.addWidget(self.dungeon_amount)
        dungeon_set_btn = QPushButton("设置指令")
        dungeon_set_btn.clicked.connect(self.dungeon_set_btn_clicked)
        dungeon_layout.addWidget(dungeon_set_btn)

    def refresh_command_list(self):
        self.command_list.clear()
        for command in self.usersettings.command_man.command_list:
            item = QListWidgetItem()
            item.setText(command)
            item.setData(Qt.ItemDataRole.UserRole, command)
            self.command_list.addItem(item)

    def crystal_set_btn_clicked(self):
        crystal_type = self.crystal_type_combobox.currentIndex() + 1
        level = self.crystal_level_combobox.currentText()
        if len(level) == 1:
            level = "0" + level
        amount = int(self.crystal_amount.currentText())
        self.usersettings.command_man.command_list.append(
            "/crystal {}{} {}".format(
                crystal_type,
                level,
                amount,
            )
        )
        self.refresh_command_list()

    def dungeon_set_btn_clicked(self):
        if self.dungeon_type_combobox.currentIndex() == 0:
            dungeon_type = 100
        elif self.dungeon_type_combobox.currentIndex() == 1:
            dungeon_type = 600
        elif self.dungeon_type_combobox.currentIndex() == 2:
            dungeon_type = 300
        else:
            raise ValueError(
                "未知的洞口类型{}".format(self.dungeon_type_combobox.currentIndex())
            )
        level = int(self.dungeon_level_combobox.currentText())
        amount = int(self.dungeon_amount.currentText())
        self.usersettings.command_man.command_list.append(
            "/dungeon {} {}".format(
                dungeon_type + level,
                amount,
            )
        )
        self.refresh_command_list()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            selected_command_items = self.command_list.selectedItems()
            if len(selected_command_items) == 0:
                return
            for item in selected_command_items:
                command_str = item.data(Qt.ItemDataRole.UserRole)
                try:
                    self.usersettings.command_man.command_list.remove(command_str)
                except ValueError:
                    pass
            self.refresh_command_list()
