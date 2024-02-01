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
    QLineEdit,
)
from PyQt6 import QtGui
from PyQt6.QtCore import Qt

from ..wrapped import QLabel
from ..user import UserSettings
from ...utils.common import format_plant_info


class TerritorySettingWindow(QMainWindow):
    def __init__(self, usersettings: UserSettings, parent=None):
        super().__init__(parent=parent)
        self.usersettings = usersettings
        self.init_ui()
        self.refresh_plant_list()
        self.refresh_team_list()

    def init_ui(self):
        self.setWindowTitle("领地挑战设置")

        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.7), int(screen_size.height() * 0.7))
        self.move(int(screen_size.width() * 0.15), int(screen_size.height() * 0.15))

        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_layout.setSpacing(3)

        widget2 = QWidget()
        widget2.setMinimumWidth(int(self.width() * 0.30))
        layout2 = QVBoxLayout()
        layout2.addWidget(QLabel("植物列表"))
        self.plant_list = QListWidget()
        self.plant_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        layout2.addWidget(self.plant_list)
        widget2.setLayout(layout2)

        widget3 = QWidget()
        widget3.setMinimumWidth(int(self.width() * 0.12))
        layout3 = QVBoxLayout()
        self.set_plant_team_btn = QPushButton("添加出战植物")
        self.set_plant_team_btn.clicked.connect(self.set_plant_team_btn_clicked)
        layout3.addWidget(self.set_plant_team_btn)
        widget3.setLayout(layout3)

        widget4 = QWidget()
        widget4.setMinimumWidth(int(self.width() * 0.30))
        layout4 = QVBoxLayout()
        self.team_list_widget = QListWidget()
        self.team_list_widget.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection
        )
        layout4.addWidget(self.team_list_widget)
        widget4.setLayout(layout4)

        widget5 = QWidget()
        widget5.setMinimumWidth(int(self.width() * 0.28))
        layout5 = QVBoxLayout()
        layout5.addStretch(1)

        difficulty_choice_widget = QWidget()
        difficulty_choice_layout = QHBoxLayout()
        difficulty_choice_layout.addWidget(QLabel("难度:"))
        self.difficulty_choice_box = difficulty_choice_box = QComboBox()
        difficulty_choice_box.addItems(["1", "2", "3", "4"])
        difficulty_choice_box.setCurrentIndex(
            self.usersettings.territory_man.difficulty_choice - 1
        )
        difficulty_choice_box.currentIndexChanged.connect(
            self.difficulty_choice_box_currentIndexChanged
        )
        difficulty_choice_layout.addWidget(difficulty_choice_box)
        difficulty_choice_widget.setLayout(difficulty_choice_layout)
        layout5.addWidget(difficulty_choice_widget)

        layout = QHBoxLayout()
        layout.addWidget(QLabel("智能领地四:"))
        self.smart_mode_checkbox = QCheckBox()
        self.smart_mode_checkbox.setChecked(
            self.usersettings.territory_man.smart_enabled
        )
        self.smart_mode_checkbox.stateChanged.connect(
            self.smart_mode_checkbox_state_changed
        )
        layout.addWidget(self.smart_mode_checkbox)
        layout5.addLayout(layout)

        layout5.addWidget(QLabel("智能领地四可容忍最高战力:"))
        layout = QHBoxLayout()
        self.mantissa_fight_line_edit = QLineEdit()
        self.mantissa_fight_line_edit.setValidator(QtGui.QDoubleValidator())
        self.mantissa_fight_line_edit.setText(
            str(self.usersettings.territory_man.max_fight_mantissa)
        )
        self.mantissa_fight_line_edit.textChanged.connect(
            self.mantissa_fight_line_edit_textChanged
        )
        layout.addWidget(self.mantissa_fight_line_edit)
        layout.addWidget(QLabel("x10的"))
        self.exponent_fight_line_edit = QLineEdit()
        self.exponent_fight_line_edit.setValidator(QtGui.QIntValidator())
        self.exponent_fight_line_edit.setText(
            str(self.usersettings.territory_man.max_fight_exponent)
        )
        self.exponent_fight_line_edit.textChanged.connect(
            self.exponent_fight_line_edit_textChanged
        )
        layout.addWidget(self.exponent_fight_line_edit)
        layout.addWidget(QLabel("次方亿"))
        layout5.addLayout(layout)

        layout = QHBoxLayout()
        layout.addWidget(QLabel("并发数:"))
        self.pool_size_combobox = QComboBox()
        self.pool_size_combobox.addItems([str(i) for i in range(1, 21)])
        self.pool_size_combobox.setCurrentText(
            str(self.usersettings.territory_man.pool_size)
        )
        self.pool_size_combobox.currentIndexChanged.connect(
            self.pool_size_combobox_currentIndexChanged
        )
        layout.addWidget(self.pool_size_combobox)
        layout5.addLayout(layout)

        self.territory_mutex_checkbox = QCheckBox("开启领地互斥:")
        self.territory_mutex_checkbox.setChecked(
            self.usersettings.territory_man.territory_mutex_enabled
        )
        self.territory_mutex_checkbox.stateChanged.connect(
            self.territory_mutex_checkbox_state_changed
        )
        layout5.addWidget(self.territory_mutex_checkbox)

        warn_label = QLabel(
            "----注意----\n"
            "每次挑战前会自动上植物\n"
            "打完领地后会自动下植物\n"
            "智能领地只对难度四有效\n"
            "选择智能领地后将无法多并发\n"
            "领地互斥选中就会起效\n"
            "领地互斥是根据竞技场排名决定优先级的\n"
            "排名高的在遇到冲突时会优先开始\n"
            "排名低在运行时若有排名高的想要运行\n"
            "    则会被迫停止，直到排名高的运行完毕\n"
        )
        warn_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout5.addWidget(warn_label)

        layout5.addStretch(1)
        widget5.setLayout(layout5)

        main_layout.addWidget(widget2)
        main_layout.addWidget(widget3)
        main_layout.addWidget(widget4)
        main_layout.addWidget(widget5)
        main_widget.setLayout(main_layout)

        self.setCentralWidget(main_widget)

    def territory_mutex_checkbox_state_changed(self):
        self.usersettings.territory_man.territory_mutex_enabled = (
            self.territory_mutex_checkbox.isChecked()
        )

    def pool_size_combobox_currentIndexChanged(self):
        self.usersettings.territory_man.pool_size = int(
            self.pool_size_combobox.currentText()
        )

    def mantissa_fight_line_edit_textChanged(self):
        self.usersettings.territory_man.max_fight_mantissa = float(
            self.mantissa_fight_line_edit.text()
        )

    def exponent_fight_line_edit_textChanged(self):
        self.usersettings.territory_man.max_fight_exponent = int(
            self.exponent_fight_line_edit.text()
        )

    def smart_mode_checkbox_state_changed(self):
        self.usersettings.territory_man.smart_enabled = (
            self.smart_mode_checkbox.isChecked()
        )

    def difficulty_choice_box_currentIndexChanged(self, index):
        self.usersettings.territory_man.difficulty_choice = index + 1

    def format_plant_info(self, plant):
        return format_plant_info(
            plant,
            self.usersettings.lib,
            spec_skill=True,
            show_normal_attribute=True,
            need_tab=True,
        )

    def refresh_plant_list(self):
        self.plant_list.clear()
        for plant in self.usersettings.repo.plants:
            if plant.id in self.usersettings.territory_man.team:
                continue
            item = QListWidgetItem(self.format_plant_info(plant))
            item.setData(Qt.ItemDataRole.UserRole, plant.id)
            self.plant_list.addItem(item)

    def refresh_team_list(self):
        self.team_list_widget.clear()
        for plant_id in self.usersettings.territory_man.team:
            plant = self.usersettings.repo.get_plant(plant_id)
            if plant is None:
                continue
            item = QListWidgetItem(self.format_plant_info(plant))
            item.setData(Qt.ItemDataRole.UserRole, plant.id)
            self.team_list_widget.addItem(item)

    def set_plant_team_btn_clicked(self):
        team = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self.plant_list.selectedItems()
        ]
        team = list(
            filter(lambda x: x not in self.usersettings.territory_man.team, team)
        )
        if len(team) + len(self.usersettings.territory_man.team) > 5:
            self.usersettings.logger.log("出战植物不能超过5个")
            return
        self.usersettings.territory_man.team.extend(team)
        self.refresh_team_list()
        self.refresh_plant_list()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Backspace or event.key() == Qt.Key.Key_Delete:
            items = [
                item.data(Qt.ItemDataRole.UserRole)
                for item in self.team_list_widget.selectedItems()
            ]
            self.usersettings.territory_man.team = [
                plant_id
                for plant_id in self.usersettings.territory_man.team
                if plant_id not in items
            ]
            self.refresh_team_list()
            self.refresh_plant_list()
