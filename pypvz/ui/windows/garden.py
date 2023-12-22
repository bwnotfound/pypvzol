from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
)
from PyQt6 import QtGui
from PyQt6.QtCore import Qt

from ..wrapped import QLabel
from ..user import UserSettings


class GardenChallengeSettingWindow(QMainWindow):
    def __init__(self, usersettings: UserSettings, parent=None):
        super().__init__(parent=parent)
        self.usersettings = usersettings
        self.init_ui()
        self.refresh_plant_list()
        self.refresh_team_list()

    def init_ui(self):
        self.setWindowTitle("花园boss挑战设置")

        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.5), int(screen_size.height() * 0.5))
        self.move(int(screen_size.width() * 0.25), int(screen_size.height() * 0.25))

        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_layout.setSpacing(3)

        widget2 = QWidget()
        widget2.setMinimumWidth(int(self.width() * 0.42))
        layout2 = QVBoxLayout()
        layout2.addWidget(QLabel("植物列表"))
        self.plant_list = QListWidget()
        self.plant_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        layout2.addWidget(self.plant_list)
        widget2.setLayout(layout2)

        widget3 = QWidget()
        widget3.setMinimumWidth(int(self.width() * 0.16))
        layout3 = QVBoxLayout()
        self.set_plant_team_btn = QPushButton("添加出战植物")
        self.set_plant_team_btn.clicked.connect(self.set_plant_team_btn_clicked)
        layout3.addWidget(self.set_plant_team_btn)
        widget3.setLayout(layout3)

        widget4 = QWidget()
        widget4.setMinimumWidth(int(self.width() * 0.42))
        layout4 = QVBoxLayout()
        self.team_list_widget = QListWidget()
        self.team_list_widget.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection
        )
        layout4.addWidget(self.team_list_widget)
        widget4.setLayout(layout4)

        main_layout.addWidget(widget2)
        main_layout.addWidget(widget3)
        main_layout.addWidget(widget4)
        main_widget.setLayout(main_layout)

        self.setCentralWidget(main_widget)

    def format_plant_info(self, plant):
        if isinstance(plant, str):
            plant = int(plant)
        if isinstance(plant, int):
            plant = self.usersettings.repo.get_plant(plant)
        msg = "{}({})[{}]".format(
            plant.name(self.usersettings.lib),
            plant.grade,
            plant.quality_str,
            self.usersettings.lib.get_spec_skill(plant.special_skill_id),
        )
        if plant.special_skill_id is not None:
            spec_skill = self.usersettings.lib.get_spec_skill(plant.special_skill_id)
            msg += " 专属:{}({}级)".format(spec_skill["name"], spec_skill['grade'])
        return msg

    def refresh_plant_list(self):
        self.plant_list.clear()
        for plant in self.usersettings.repo.plants:
            if plant.id in self.usersettings.garden_man.team:
                continue
            item = QListWidgetItem(self.format_plant_info(plant))
            item.setData(Qt.ItemDataRole.UserRole, plant.id)
            self.plant_list.addItem(item)

    def refresh_team_list(self):
        self.team_list_widget.clear()
        for plant_id in self.usersettings.garden_man.team:
            plant = self.usersettings.repo.get_plant(plant_id)
            if plant is None:
                continue
            item = QListWidgetItem(self.format_plant_info(plant))
            item.setData(Qt.ItemDataRole.UserRole, plant.id)
            self.team_list_widget.addItem(item)

    def set_plant_team_btn_clicked(self):
        self.usersettings.garden_man.team.extend(
            [
                item.data(Qt.ItemDataRole.UserRole)
                for item in self.plant_list.selectedItems()
            ]
        )
        self.refresh_team_list()
        self.refresh_plant_list()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Backspace or event.key() == Qt.Key.Key_Delete:
            items = [
                item.data(Qt.ItemDataRole.UserRole)
                for item in self.team_list_widget.selectedItems()
            ]
            self.usersettings.garden_man.team = [
                plant_id
                for plant_id in self.usersettings.garden_man.team
                if plant_id not in items
            ]
            self.refresh_team_list()
            self.refresh_plant_list()
