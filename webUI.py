import sys
import json
from io import BytesIO
import os
import logging
import concurrent.futures
from queue import Queue

from PyQt6 import QtGui
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTabWidget,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QGridLayout,
    QCheckBox,
    QPlainTextEdit,
    QSpinBox,
    QComboBox,
    QLineEdit,
)
from PyQt6.QtGui import QImage, QPixmap, QTextCursor
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PIL import Image

from pypvz import WebRequest, Config, User, CaveMan, Repository, Library
from pypvz.ui.message import IOLogger
from pypvz.ui.wrapped import QLabel, normal_font
from pypvz.ui.windows.common import (
    AutoUseItemSettingWindow,
    AddCaveWindow,
    ShopAutoBuySetting,
    HeritageWindow,
    PlantRelativeWindow,
    SetPlantListWindow,
)
from pypvz.ui.user import SingleCave, UserSettings
from pypvz.ui.windows import (
    EvolutionPanelWindow,
    UpgradeQualityWindow,
    AutoSynthesisWindow,
)


class Challenge4levelSettingWindow(QMainWindow):
    selectd_cave_update = pyqtSignal()

    set_plant_list_over = pyqtSignal(list)

    def __init__(self, usersettings: UserSettings, parent=None):
        super().__init__(parent=parent)
        self.usersettings = usersettings
        self.selectd_cave: SingleCave = None
        self.set_plant_list_result = []
        self.delete_last_selected_list = None
        self.init_ui()
        self.selectd_cave_update.connect(self.update_selectd_cave)
        self.update_cave_list()
        self.update_main_plant_list()
        self.update_trash_plant_list()

    def init_ui(self):
        self.setWindowTitle("练级设置")

        # 将窗口居中显示，宽度为显示器宽度的40%，高度为显示器高度的60%
        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.4), int(screen_size.height() * 0.8))
        self.move(int(screen_size.width() * 0.3), int(screen_size.height() * 0.1))

        main_widget = QWidget()
        main_layout = QHBoxLayout()

        left_panel = QWidget()
        left_panel_layout = QGridLayout()
        caves_widget = QWidget()
        caves_layout = QVBoxLayout()
        top_layout = QHBoxLayout()
        text = QLabel("洞口:")
        btn = QPushButton("选择洞口")
        btn.clicked.connect(self.add_cave_btn_clicked)
        top_layout.addWidget(text)
        top_layout.addStretch(1)
        top_layout.addWidget(btn)
        self.cave_list = cave_list = QListWidget()
        cave_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        cave_list.itemClicked.connect(self.cave_list_item_clicked)
        caves_layout.addLayout(top_layout)
        caves_layout.addWidget(cave_list)
        caves_widget.setLayout(caves_layout)
        left_panel_layout.addWidget(caves_widget, 0, 0)

        friend_list_panel = QWidget()
        friend_list_panel_layout = QVBoxLayout()
        top_layout = QHBoxLayout()
        text = QLabel("要打的好友列表")
        top_layout.addWidget(text)
        top_layout.addStretch(1)
        self.friend_list = friend_list = QListWidget()
        friend_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        friend_list.itemClicked.connect(self.friend_list_item_clicked)
        friend_list_panel_layout.addLayout(top_layout)
        friend_list_panel_layout.addWidget(friend_list)
        friend_list_panel.setLayout(friend_list_panel_layout)
        left_panel_layout.addWidget(friend_list_panel, 0, 1)

        main_plant_list_panel = QWidget()
        main_plant_list_panel_layout = QVBoxLayout()
        top_layout = QHBoxLayout()
        text = QLabel("主力植物")
        top_layout.addWidget(text)
        top_layout.addStretch(1)
        self.main_plant_setting_btn = btn = QPushButton("设置")
        btn.clicked.connect(self.set_main_plant_btn_clicked)

        top_layout.addWidget(btn)
        self.main_plant_list = main_plant_list = QListWidget()
        main_plant_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        main_plant_list.itemClicked.connect(self.main_plant_list_item_clicked)
        main_plant_list.itemSelectionChanged.connect(
            self.main_plant_list_item_selection_changed
        )
        main_plant_list_panel_layout.addLayout(top_layout)
        main_plant_list_panel_layout.addWidget(main_plant_list)
        main_plant_list_panel.setLayout(main_plant_list_panel_layout)
        left_panel_layout.addWidget(main_plant_list_panel, 1, 0)

        trash_plant_list_panel = QWidget()
        trash_plant_list_panel_layout = QVBoxLayout()
        top_layout = QHBoxLayout()
        text = QLabel("练级植物")
        top_layout.addWidget(text)
        top_layout.addStretch(1)
        self.trash_plant_setting_btn = btn = QPushButton("设置")
        btn.clicked.connect(self.set_trash_plant_btn_clicked)

        top_layout.addWidget(btn)
        self.trash_plant_list = trash_plant_list = QListWidget()
        trash_plant_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        trash_plant_list.itemClicked.connect(self.trash_plant_list_item_clicked)
        trash_plant_list.itemSelectionChanged.connect(
            self.trash_plant_list_item_selection_changed
        )
        trash_plant_list_panel_layout.addLayout(top_layout)
        trash_plant_list_panel_layout.addWidget(trash_plant_list)
        trash_plant_list_panel.setLayout(trash_plant_list_panel_layout)
        left_panel_layout.addWidget(trash_plant_list_panel, 1, 1)

        left_panel.setLayout(left_panel_layout)
        main_layout.addWidget(left_panel)

        right_panel = QWidget()
        right_panel_layout = QVBoxLayout()
        right_panel_layout.addWidget(QLabel("当前洞口的配置:"))

        self.enable_cave_checkbox = QCheckBox("启用当前洞口")
        self.enable_cave_checkbox.setChecked(False)
        self.enable_cave_checkbox.stateChanged.connect(
            self.enable_cave_checkbox_stateChanged
        )
        right_panel_layout.addWidget(self.enable_cave_checkbox)

        self.current_cave_use_sand = QCheckBox("使用时之沙")
        self.current_cave_use_sand.setChecked(False)
        self.current_cave_use_sand.stateChanged.connect(
            self.current_cave_use_sand_stateChanged
        )
        right_panel_layout.addWidget(self.current_cave_use_sand)

        self.current_cave_difficulty = QComboBox()
        self.current_cave_difficulty.addItems(["简单", "普通", "困难"])
        self.current_cave_difficulty.setCurrentIndex(3)
        self.current_cave_difficulty.currentIndexChanged.connect(
            self.current_cave_difficulty_currentIndexChanged
        )
        right_panel_layout.addWidget(self.current_cave_difficulty)

        right_panel_layout.addStretch(1)
        right_panel_layout.addWidget(QLabel("全局挑战设置:"))

        cave_enabled_switch_layout = QHBoxLayout()
        enable_all_cave_btn = QPushButton("启用所有洞口")
        enable_all_cave_btn.clicked.connect(self.enable_all_cave_btn_clicked)
        cave_enabled_switch_layout.addWidget(enable_all_cave_btn)
        disable_all_cave_btn = QPushButton("禁用所有洞口")
        disable_all_cave_btn.clicked.connect(self.disable_all_cave_btn_clicked)
        cave_enabled_switch_layout.addWidget(disable_all_cave_btn)
        right_panel_layout.addLayout(cave_enabled_switch_layout)

        free_max_input_widget = QWidget()
        free_max_input_layout = QHBoxLayout()
        free_max_input_box = QSpinBox()
        free_max_input_box.setMinimum(0)
        free_max_input_box.setMaximum(16)
        free_max_input_box.setValue(self.usersettings.challenge4Level.free_max)

        def free_max_input_box_value_changed(value):
            self.usersettings.challenge4Level.free_max = value

        free_max_input_box.valueChanged.connect(free_max_input_box_value_changed)
        free_max_input_layout.addWidget(QLabel("出战植物最大空位数:"))
        free_max_input_layout.addWidget(free_max_input_box)
        free_max_input_widget.setLayout(free_max_input_layout)
        right_panel_layout.addWidget(free_max_input_widget)

        hp_choice_widget = QWidget()
        hp_choice_layout = QHBoxLayout()
        hp_choice_layout.addWidget(QLabel("血瓶选择:"))
        hp_choice_box = QComboBox()
        self.hp_choice_list = ["低级血瓶", "中级血瓶", "高级血瓶"]
        hp_choice_box.addItems(self.hp_choice_list)
        hp_choice_box.setCurrentIndex(
            self.hp_choice_list.index(self.usersettings.challenge4Level.hp_choice)
        )
        hp_choice_box.currentIndexChanged.connect(
            self.hp_choice_box_currentIndexChanged
        )
        hp_choice_layout.addWidget(hp_choice_box)
        hp_choice_widget.setLayout(hp_choice_layout)
        right_panel_layout.addWidget(hp_choice_widget)

        widget1 = QWidget()
        widget1_layout = QHBoxLayout()
        widget1_layout.addWidget(QLabel("100级后弹出:"))
        self.pop_checkbox = QCheckBox()
        self.pop_checkbox.setChecked(self.usersettings.challenge4Level.pop_after_100)
        self.pop_checkbox.stateChanged.connect(self.pop_checkbox_stateChanged)
        widget1_layout.addWidget(self.pop_checkbox)
        widget1.setLayout(widget1_layout)
        right_panel_layout.addWidget(widget1)

        widget2 = QWidget()
        widget2_layout = QHBoxLayout()
        widget2_layout.addWidget(QLabel("自动使用挑战书(优先高挑):"))
        self.auto_use_challenge_book_checkbox = QCheckBox()
        self.auto_use_challenge_book_checkbox.setChecked(
            self.usersettings.challenge4Level.auto_use_challenge_book
        )
        self.auto_use_challenge_book_checkbox.stateChanged.connect(
            self.auto_use_challenge_book_checkbox_stateChanged
        )
        widget2_layout.addWidget(self.auto_use_challenge_book_checkbox)
        widget2.setLayout(widget2_layout)
        right_panel_layout.addWidget(widget2)

        widget3 = QWidget()
        widget3_layout = QHBoxLayout()
        widget3_layout.addWidget(QLabel("一次使用多少高挑:"))
        self.use_advanced_challenge_book_count_box = QSpinBox()
        self.use_advanced_challenge_book_count_box.setMinimum(1)
        self.use_advanced_challenge_book_count_box.setMaximum(
            5 if self.usersettings.cfg.server == "官服" else 2250 // 5
        )
        self.use_advanced_challenge_book_count_box.setValue(
            self.usersettings.challenge4Level.advanced_challenge_book_amount
        )
        self.use_advanced_challenge_book_count_box.valueChanged.connect(
            self.use_advanced_challenge_book_count_box_currentIndexChanged
        )
        widget3_layout.addWidget(self.use_advanced_challenge_book_count_box)
        widget3.setLayout(widget3_layout)
        right_panel_layout.addWidget(widget3)

        widget4 = QWidget()
        widget4_layout = QHBoxLayout()
        widget4_layout.addWidget(QLabel("一次使用多少挑战书:"))
        self.use_normal_challenge_book_count_box = QSpinBox()
        self.use_normal_challenge_book_count_box.setMinimum(1)
        self.use_normal_challenge_book_count_box.setMaximum(
            25 if self.usersettings.cfg.server == "官服" else 2250
        )
        self.use_normal_challenge_book_count_box.setValue(
            self.usersettings.challenge4Level.normal_challenge_book_amount
        )
        self.use_normal_challenge_book_count_box.valueChanged.connect(
            self.use_normal_challenge_book_count_box_currentIndexChanged
        )
        widget4_layout.addWidget(self.use_normal_challenge_book_count_box)
        widget4.setLayout(widget4_layout)
        right_panel_layout.addWidget(widget4)

        self.enable_sand = QCheckBox("允许使用时之沙")
        self.enable_sand.setChecked(self.usersettings.challenge4Level.enable_sand)
        self.enable_sand.stateChanged.connect(self.enable_sand_stateChanged)
        right_panel_layout.addWidget(self.enable_sand)

        self.show_lottery = QCheckBox("是否显示获胜战利品(会变慢)")
        self.show_lottery.setChecked(self.usersettings.challenge4Level.show_lottery)
        self.show_lottery.stateChanged.connect(self.show_lottery_stateChanged)
        right_panel_layout.addWidget(self.show_lottery)

        self.enable_stone = QCheckBox("允许挑战宝石副本")
        self.enable_stone.setChecked(self.usersettings.challenge4Level.enable_stone)
        self.enable_stone.stateChanged.connect(self.enable_stone_stateChanged)
        right_panel_layout.addWidget(self.enable_stone)

        if self.usersettings.cfg.server == "私服":
            self.enable_large_plant_team = QCheckBox("V4使用16格带级")
            self.enable_large_plant_team.setChecked(
                self.usersettings.challenge4Level.enable_large_plant_team
            )
            self.enable_large_plant_team.stateChanged.connect(
                self.enable_large_plant_team_stateChanged
            )
            right_panel_layout.addWidget(self.enable_large_plant_team)

        right_panel_layout.addWidget(QLabel("--以下功能需认真选取--\n--(因为不恰当使用会有bug)--"))

        self.need_recover_checkbox = QCheckBox("需要恢复植物血量")
        self.need_recover_checkbox.setChecked(
            self.usersettings.challenge4Level.need_recover
        )
        self.need_recover_checkbox.stateChanged.connect(
            self.need_recover_checkbox_stateChanged
        )
        right_panel_layout.addWidget(self.need_recover_checkbox)

        self.disable_cave_info_fetch_checkbox = QCheckBox("刷洞加速")
        self.disable_cave_info_fetch_checkbox.setChecked(
            self.usersettings.challenge4Level.disable_cave_info_fetch
        )
        self.disable_cave_info_fetch_checkbox.stateChanged.connect(
            self.disable_cave_info_fetch_checkbox_stateChanged
        )
        right_panel_layout.addWidget(self.disable_cave_info_fetch_checkbox)

        self.challenge_sand_cave_only_in_disable_mode_checkbox = QCheckBox(
            "加速时只刷用时之沙的洞"
        )
        self.challenge_sand_cave_only_in_disable_mode_checkbox.setChecked(
            self.usersettings.challenge4Level.challenge_sand_cave_only_in_disable_mode
        )
        self.challenge_sand_cave_only_in_disable_mode_checkbox.stateChanged.connect(
            self.challenge_sand_cave_only_in_disable_mode_checkbox_stateChanged
        )
        right_panel_layout.addWidget(
            self.challenge_sand_cave_only_in_disable_mode_checkbox
        )

        self.accelerate_repository_in_challenge_cave_checkbox = QCheckBox("跳过仓库来加速")
        self.accelerate_repository_in_challenge_cave_checkbox.setChecked(
            self.usersettings.challenge4Level.accelerate_repository_in_challenge_cave
        )
        self.accelerate_repository_in_challenge_cave_checkbox.stateChanged.connect(
            self.accelerate_repository_in_challenge_cave_checkbox_stateChanged
        )
        right_panel_layout.addWidget(
            self.accelerate_repository_in_challenge_cave_checkbox
        )

        warning_textbox = QPlainTextEdit()
        warning_textbox.setReadOnly(True)
        warning_textbox.setPlainText(
            "警告：使用上述功能需详细查看此警告\n"
            "注意，加速原理是直接挑战对应洞口\n"
            "因此如果加速不选\"只刷时之沙的洞\"会导致每次循环都会尝试那些没冷却的洞\n"
            "比如你选了10个洞口，只有一个要用时之沙，那么每次都会尝试挑战那9个不用时之沙的洞口\n"
            "会造成很大的性能浪费\n"
            "对于加速跳过仓库，这个选项开启后，原理是不会去获取仓库信息，会预测你的炮灰等级变化，从而加速\n"
            "但是因为跳过了仓库信息获取，因此无法保证植物存在和植物血量\n"
            "选择此选项也会跳过植物回血，请保证以下情况不会发生的时候使用仓库加速:\n"
            "1. 你的植物不会死亡，包括主力和炮灰\n"
            "2. 你的植物不会消失，包括主力和炮灰\n"
        )
        right_panel_layout.addWidget(warning_textbox)

        right_panel.setLayout(right_panel_layout)
        main_layout.addWidget(right_panel)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def enable_all_cave_btn_clicked(self):
        for sc in self.usersettings.challenge4Level.caves:
            sc.enabled = True
        self.selectd_cave_update.emit()

    def disable_all_cave_btn_clicked(self):
        for sc in self.usersettings.challenge4Level.caves:
            sc.enabled = False
        self.selectd_cave_update.emit()

    def enable_cave_checkbox_stateChanged(self):
        self.selectd_cave.enabled = self.enable_cave_checkbox.isChecked()

    def accelerate_repository_in_challenge_cave_checkbox_stateChanged(self):
        self.usersettings.challenge4Level.accelerate_repository_in_challenge_cave = (
            self.accelerate_repository_in_challenge_cave_checkbox.isChecked()
        )

    def challenge_sand_cave_only_in_disable_mode_checkbox_stateChanged(self):
        self.usersettings.challenge4Level.challenge_sand_cave_only_in_disable_mode = (
            self.challenge_sand_cave_only_in_disable_mode_checkbox.isChecked()
        )

    def need_recover_checkbox_stateChanged(self):
        self.usersettings.challenge4Level.need_recover = (
            self.need_recover_checkbox.isChecked()
        )

    def disable_cave_info_fetch_checkbox_stateChanged(self):
        self.usersettings.challenge4Level.disable_cave_info_fetch = (
            self.disable_cave_info_fetch_checkbox.isChecked()
        )

    def enable_large_plant_team_stateChanged(self):
        self.usersettings.challenge4Level.enable_large_plant_team = (
            self.enable_large_plant_team.isChecked()
        )

    def enable_stone_stateChanged(self):
        self.usersettings.challenge4Level.enable_stone = self.enable_stone.isChecked()

    def current_cave_use_sand_stateChanged(self):
        self.selectd_cave.use_sand = self.current_cave_use_sand.isChecked()

    def current_cave_difficulty_currentIndexChanged(self, index):
        self.selectd_cave.difficulty = index + 1

    def show_lottery_stateChanged(self):
        self.usersettings.challenge4Level.show_lottery = self.show_lottery.isChecked()

    def enable_sand_stateChanged(self):
        self.usersettings.challenge4Level.enable_sand = self.enable_sand.isChecked()

    def hp_choice_box_currentIndexChanged(self, index):
        self.usersettings.challenge4Level.hp_choice = self.hp_choice_list[index]

    def pop_checkbox_stateChanged(self):
        self.usersettings.challenge4Level.pop_after_100 = self.pop_checkbox.isChecked()

    def use_normal_challenge_book_count_box_currentIndexChanged(self):
        self.usersettings.challenge4Level.normal_challenge_book_amount = (
            self.use_normal_challenge_book_count_box.value()
        )

    def use_advanced_challenge_book_count_box_currentIndexChanged(self):
        self.usersettings.challenge4Level.advanced_challenge_book_amount = (
            self.use_advanced_challenge_book_count_box.value()
        )

    def auto_use_challenge_book_checkbox_stateChanged(self):
        self.usersettings.challenge4Level.auto_use_challenge_book = (
            self.auto_use_challenge_book_checkbox.isChecked()
        )

    def update_selectd_cave(self):
        self.update_friend_list()
        if self.selectd_cave is None:
            self.enable_cave_checkbox.setDisabled(True)
            self.current_cave_use_sand.setDisabled(True)
            self.current_cave_difficulty.setDisabled(True)
            return
        self.enable_cave_checkbox.setChecked(self.selectd_cave.enabled)
        self.current_cave_use_sand.setChecked(self.selectd_cave.use_sand)
        self.current_cave_difficulty.setCurrentIndex(self.selectd_cave.difficulty - 1)
        self.enable_cave_checkbox.setEnabled(True)
        self.current_cave_use_sand.setEnabled(True)
        self.current_cave_difficulty.setEnabled(True)

    def cave_list_item_clicked(self, item):
        self.selectd_cave = item.data(Qt.ItemDataRole.UserRole)
        self.selectd_cave_update.emit()
        self.delete_last_selected_list = self.cave_list

    def friend_list_item_clicked(self, item):
        self.delete_last_selected_list = self.friend_list

    def main_plant_list_item_clicked(self, item):
        self.delete_last_selected_list = self.main_plant_list

    def main_plant_list_item_selection_changed(self):
        self.delete_last_selected_list = self.main_plant_list

    def trash_plant_list_item_selection_changed(self):
        self.delete_last_selected_list = self.trash_plant_list

    def trash_plant_list_item_clicked(self, item):
        self.delete_last_selected_list = self.trash_plant_list

    def update_cave_list(self):
        self.cave_list.clear()
        self.cave_list.setCurrentItem(None)
        self.selectd_cave = None
        self.selectd_cave_update.emit()
        caves = self.usersettings.challenge4Level.caves
        for sc in caves:
            item = QListWidgetItem(sc.cave.format_name())
            item.setData(Qt.ItemDataRole.UserRole, sc)
            self.cave_list.addItem(item)

    def update_friend_list(self):
        self.friend_list.clear()
        if self.selectd_cave is None:
            return
        for friend_id in self.selectd_cave.friend_id_list:
            friend = self.usersettings.friendman.id2friend[friend_id]
            item = QListWidgetItem(f"{friend.name} ({friend.grade})")
            item.setData(Qt.ItemDataRole.UserRole, friend)
            self.friend_list.addItem(item)

    def update_main_plant_list(self):
        self.main_plant_list.clear()
        for plant_id in self.usersettings.challenge4Level.main_plant_list:
            plant = self.usersettings.repo.get_plant(plant_id)
            if plant is None:
                self.usersettings.challenge4Level.main_plant_list.remove(plant_id)
                continue
            item = QListWidgetItem(
                f"{plant.name(self.usersettings.lib)} ({plant.grade})"
            )
            item.setData(Qt.ItemDataRole.UserRole, plant)
            self.main_plant_list.addItem(item)

    def update_trash_plant_list(self):
        self.trash_plant_list.clear()
        for plant_id in self.usersettings.challenge4Level.trash_plant_list:
            plant = self.usersettings.repo.get_plant(plant_id)
            if plant is None:
                self.usersettings.challenge4Level.trash_plant_list.remove(plant_id)
                continue
            item = QListWidgetItem(
                f"{plant.name(self.usersettings.lib)} ({plant.grade})"
            )
            item.setData(Qt.ItemDataRole.UserRole, plant)
            self.trash_plant_list.addItem(item)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            if self.delete_last_selected_list is not None:
                select_items = self.delete_last_selected_list.selectedItems()
                if self.delete_last_selected_list is self.cave_list:
                    for item in select_items:
                        sc = item.data(Qt.ItemDataRole.UserRole)
                        self.usersettings.challenge4Level.remove_cave(
                            sc.cave, sc.garden_layer
                        )
                    self.update_cave_list()
                elif self.delete_last_selected_list is self.main_plant_list:
                    for item in select_items:
                        plant = item.data(Qt.ItemDataRole.UserRole)
                        self.usersettings.challenge4Level.main_plant_list.remove(
                            plant.id
                        )
                    self.update_main_plant_list()
                elif self.delete_last_selected_list is self.trash_plant_list:
                    for item in select_items:
                        plant = item.data(Qt.ItemDataRole.UserRole)
                        self.usersettings.challenge4Level.trash_plant_list.remove(
                            plant.id
                        )
                    self.update_trash_plant_list()
                elif self.delete_last_selected_list is self.friend_list:
                    friend_ids = [
                        item.data(Qt.ItemDataRole.UserRole).id for item in select_items
                    ]
                    self.usersettings.challenge4Level.remove_cave_friend(
                        self.selectd_cave,
                        friend_ids,
                        self.selectd_cave.garden_layer,
                    )
                    self.update_friend_list()
                else:
                    raise NotImplementedError
        # elif event.key() == Qt.Key.Key_Up or event.key() == Qt.Key.Key_A:
        #     self.close()

    def add_cave_btn_clicked(self):
        self.add_cave_window = AddCaveWindow(self.usersettings, parent=self)
        self.add_cave_window.cave_add_update.connect(self.update_cave_list)
        self.add_cave_window.show()

    def add_main_plant(self, result):
        self.usersettings.challenge4Level.main_plant_list = (
            self.usersettings.challenge4Level.main_plant_list + result
        )
        self.update_main_plant_list()

    def set_main_plant_btn_clicked(self):
        # 当set_plant_list_over有链接的槽函数时，将之前的槽函数disconnect
        try:
            self.set_plant_list_over.disconnect()
        except TypeError:
            pass
        self.set_plant_list_over.connect(self.add_main_plant)
        self.set_plant_list_window = SetPlantListWindow(
            self.usersettings.repo,
            self.usersettings.lib,
            self.set_plant_list_over,
            origin_plant_id_list=self.usersettings.challenge4Level.main_plant_list
            + self.usersettings.challenge4Level.trash_plant_list,
            parent=self,
        )
        self.set_plant_list_window.show()

    def add_trash_plant(self, result):
        self.usersettings.challenge4Level.trash_plant_list = (
            self.usersettings.challenge4Level.trash_plant_list + result
        )
        self.update_trash_plant_list()

    def set_trash_plant_btn_clicked(self):
        try:
            self.set_plant_list_over.disconnect()
        except TypeError:
            pass
        self.set_plant_list_over.connect(self.add_trash_plant)
        self.set_plant_list_window = SetPlantListWindow(
            self.usersettings.repo,
            self.usersettings.lib,
            self.set_plant_list_over,
            origin_plant_id_list=self.usersettings.challenge4Level.main_plant_list
            + self.usersettings.challenge4Level.trash_plant_list,
            parent=self,
        )
        self.set_plant_list_window.show()


class SettingWindow(QMainWindow):
    def __init__(self, usersettings: UserSettings, parent=None):
        super().__init__(parent=parent)
        self.usersettings = usersettings
        self.init_ui()

    def init_ui(self):
        # 将窗口居中显示，宽度为显示器宽度的50%，高度为显示器高度的70%
        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.5), int(screen_size.height() * 0.7))
        self.move(int(screen_size.width() * 0.25), int(screen_size.height() * 0.15))
        self.setWindowTitle("设置")

        main_widget = QWidget()
        main_layout = QHBoxLayout()

        left_panel = QWidget()
        left_panel.setFixedWidth(int(self.width() * 0.2))
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("植物列表"))
        self.plant_list = QListWidget()
        self.plant_list.addItems(
            [
                f"{plant.name(self.usersettings.lib)}({plant.grade})"
                for plant in self.usersettings.repo.plants
            ]
        )
        left_layout.addWidget(self.plant_list)
        left_panel.setLayout(left_layout)

        main_layout.addWidget(left_panel)

        menu_widget = QWidget()
        menu_layout = QGridLayout()
        challenge4level_widget = QWidget()
        challenge4level_layout = QHBoxLayout()
        self.challenge4level_checkbox = challenge4level_checkbox = QCheckBox("刷洞")
        challenge4level_checkbox.setFont(normal_font)
        challenge4level_checkbox.setChecked(self.usersettings.challenge4Level_enabled)
        challenge4level_checkbox.stateChanged.connect(
            self.challenge4level_checkbox_stateChanged
        )
        challenge4level_layout.addWidget(challenge4level_checkbox)
        challenge4level_setting_btn = QPushButton("设置")
        challenge4level_setting_btn.clicked.connect(
            self.challenge4level_setting_btn_clicked
        )
        challenge4level_layout.addWidget(challenge4level_setting_btn)
        challenge4level_layout.addStretch(1)
        challenge4level_widget.setLayout(challenge4level_layout)
        menu_layout.addWidget(challenge4level_widget, 0, 0)

        shop_enable_widget = QWidget()
        shop_enable_layout = QHBoxLayout()
        self.shop_enable_checkbox = shop_enable_checkbox = QCheckBox("商店购买")
        shop_enable_checkbox.setFont(normal_font)
        shop_enable_checkbox.setChecked(self.usersettings.shop_enabled)
        shop_enable_checkbox.stateChanged.connect(
            self.shop_enable_checkbox_stateChanged
        )
        shop_enable_layout.addWidget(shop_enable_checkbox)
        shop_auto_buy_setting_btn = QPushButton("设置")
        shop_auto_buy_setting_btn.clicked.connect(
            self.shop_auto_buy_setting_btn_clicked
        )
        shop_enable_layout.addWidget(shop_auto_buy_setting_btn)
        shop_enable_layout.addStretch(1)
        shop_enable_widget.setLayout(shop_enable_layout)
        menu_layout.addWidget(shop_enable_widget, 1, 0)

        task_panel = QWidget()
        task_panel_layout = QVBoxLayout()
        self.task_setting_checkbox = task_setting_checkbox = QCheckBox("自动领取任务")
        task_setting_checkbox.setFont(normal_font)
        task_setting_checkbox.setChecked(self.usersettings.task_enabled)
        task_setting_checkbox.stateChanged.connect(
            self.task_setting_checkbox_stateChanged
        )
        task_panel_layout.addWidget(task_setting_checkbox)
        task_widget = QWidget()
        task_layout = QHBoxLayout()

        main_task_widget = QWidget()
        main_task_layout = QHBoxLayout()
        self.main_task_checkbox = main_task_checkbox = QCheckBox("主线")
        main_task_checkbox.setFont(normal_font)
        main_task_checkbox.setChecked(self.usersettings.enable_list[0])
        main_task_checkbox.stateChanged.connect(self.main_task_checkbox_stateChanged)
        main_task_layout.addWidget(main_task_checkbox)
        main_task_widget.setLayout(main_task_layout)
        task_layout.addWidget(main_task_widget)

        side_task_widget = QWidget()
        side_task_layout = QHBoxLayout()
        self.side_task_checkbox = side_task_checkbox = QCheckBox("支线")
        side_task_checkbox.setFont(normal_font)
        side_task_checkbox.setChecked(self.usersettings.enable_list[1])
        side_task_checkbox.stateChanged.connect(self.side_task_checkbox_stateChanged)
        side_task_layout.addWidget(side_task_checkbox)
        side_task_widget.setLayout(side_task_layout)
        task_layout.addWidget(side_task_widget)

        daily_task_widget = QWidget()
        daily_task_layout = QHBoxLayout()
        self.daily_task_checkbox = daily_task_checkbox = QCheckBox("日常")
        daily_task_checkbox.setFont(normal_font)
        daily_task_checkbox.setChecked(self.usersettings.enable_list[2])
        daily_task_checkbox.stateChanged.connect(self.daily_task_checkbox_stateChanged)
        daily_task_layout.addWidget(daily_task_checkbox)
        daily_task_widget.setLayout(daily_task_layout)
        task_layout.addWidget(daily_task_widget)

        active_task_widget = QWidget()
        active_task_layout = QHBoxLayout()
        self.active_task_checkbox = active_task_checkbox = QCheckBox("活动")
        active_task_checkbox.setFont(normal_font)
        active_task_checkbox.setChecked(self.usersettings.enable_list[3])
        active_task_checkbox.stateChanged.connect(
            self.active_task_checkbox_stateChanged
        )
        active_task_layout.addWidget(active_task_checkbox)
        active_task_widget.setLayout(active_task_layout)
        task_layout.addWidget(active_task_widget)
        task_layout.addStretch(1)
        task_widget.setLayout(task_layout)

        task_panel_layout.addWidget(task_widget)
        task_panel.setLayout(task_panel_layout)

        menu_layout.addWidget(task_panel, 2, 0)

        auto_use_item_widget = QWidget()
        auto_use_item_layout = QHBoxLayout()
        self.auto_use_item_checkbox = auto_use_item_checkbox = QCheckBox("自动使用道具")
        auto_use_item_checkbox.setFont(normal_font)
        auto_use_item_checkbox.setChecked(self.usersettings.auto_use_item_enabled)
        auto_use_item_checkbox.stateChanged.connect(
            self.auto_use_item_checkbox_stateChanged
        )
        auto_use_item_layout.addWidget(auto_use_item_checkbox)

        self.auto_use_item_setting_btn = auto_use_item_setting_btn = QPushButton("道具面板")
        auto_use_item_setting_btn.clicked.connect(
            self.auto_use_item_setting_btn_clicked
        )
        auto_use_item_layout.addWidget(auto_use_item_setting_btn)
        auto_use_item_layout.addStretch(1)
        auto_use_item_widget.setLayout(auto_use_item_layout)
        menu_layout.addWidget(auto_use_item_widget, 3, 0)

        arena_widget = QWidget()
        arena_layout = QHBoxLayout()
        self.arena_checkbox = arena_checkbox = QCheckBox("竞技场")
        arena_checkbox.setFont(normal_font)
        arena_checkbox.setChecked(self.usersettings.arena_enabled)
        arena_checkbox.stateChanged.connect(self.arena_checkbox_stateChanged)
        arena_layout.addWidget(arena_checkbox)
        arena_widget.setLayout(arena_layout)
        menu_layout.addWidget(arena_widget, 4, 0)

        serverbattle_widget = QWidget()
        serverbattle_layout = QHBoxLayout()
        self.serverbattle_checkbox = serverbattle_checkbox = QCheckBox("跨服战")
        serverbattle_checkbox.setFont(normal_font)
        serverbattle_checkbox.setChecked(self.usersettings.serverbattle_enabled)
        serverbattle_checkbox.stateChanged.connect(
            self.serverbattle_checkbox_stateChanged
        )
        serverbattle_layout.addWidget(serverbattle_checkbox)
        serverbattle_widget.setLayout(serverbattle_layout)
        menu_layout.addWidget(serverbattle_widget, 5, 0)

        rest_time_input_widget = QWidget()
        rest_time_input_layout = QHBoxLayout()
        rest_time_input_layout.addWidget(QLabel("休息时间(秒):"))
        rest_time_input_box = QSpinBox()
        rest_time_input_box.setMinimum(0)
        rest_time_input_box.setMaximum(60 * 60)
        rest_time_input_box.setValue(self.usersettings.rest_time)
        rest_time_input_box.valueChanged.connect(self.rest_time_input_box_valueChanged)
        rest_time_input_layout.addWidget(rest_time_input_box)
        rest_time_input_widget.setLayout(rest_time_input_layout)
        menu_layout.addWidget(rest_time_input_widget, 6, 0)

        max_timeout_widget = QWidget()
        max_timeout_layout = QHBoxLayout()
        max_timeout_layout.addWidget(QLabel("请求最大超时时间(秒):"))
        self.max_timeout_input_box = max_timeout_input_box = QSpinBox()
        max_timeout_input_box.setMinimum(1)
        max_timeout_input_box.setMaximum(60)
        max_timeout_input_box.setValue(self.usersettings.cfg.timeout)
        max_timeout_input_box.valueChanged.connect(
            self.max_timeout_input_box_valueChanged
        )
        max_timeout_layout.addWidget(max_timeout_input_box)
        max_timeout_widget.setLayout(max_timeout_layout)
        menu_layout.addWidget(max_timeout_widget, 7, 0)

        millsecond_delay_widget = QWidget()
        millsecond_delay_layout = QHBoxLayout()
        millsecond_delay_layout.addWidget(QLabel("请求间隔(毫秒):"))
        self.millsecond_delay_input_box = millsecond_delay_input_box = QSpinBox()
        millsecond_delay_input_box.setMinimum(0)
        millsecond_delay_input_box.setMaximum(60 * 1000)
        millsecond_delay_input_box.setValue(self.usersettings.cfg.millsecond_delay)
        millsecond_delay_input_box.valueChanged.connect(
            self.millsecond_delay_input_box_valueChanged
        )
        millsecond_delay_layout.addWidget(millsecond_delay_input_box)
        millsecond_delay_widget.setLayout(millsecond_delay_layout)
        menu_layout.addWidget(millsecond_delay_widget, 8, 0)

        menu_widget.setLayout(menu_layout)
        main_layout.addWidget(menu_widget)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def serverbattle_checkbox_stateChanged(self):
        self.usersettings.serverbattle_enabled = self.serverbattle_checkbox.isChecked()

    def millsecond_delay_input_box_valueChanged(self):
        self.usersettings.cfg.millsecond_delay = self.millsecond_delay_input_box.value()

    def max_timeout_input_box_valueChanged(self):
        self.usersettings.cfg.timeout = self.max_timeout_input_box.value()

    def task_setting_checkbox_stateChanged(self):
        self.usersettings.task_enabled = self.task_setting_checkbox.isChecked()

    def arena_checkbox_stateChanged(self):
        self.usersettings.arena_enabled = self.arena_checkbox.isChecked()

    def rest_time_input_box_valueChanged(self, value):
        self.usersettings.rest_time = value

    def shop_auto_buy_setting_btn_clicked(self):
        self.shop_auto_buy_setting_window = ShopAutoBuySetting(
            self.usersettings, parent=self
        )
        self.shop_auto_buy_setting_window.show()

    def shop_enable_checkbox_stateChanged(self):
        self.usersettings.shop_enabled = self.shop_enable_checkbox.isChecked()

    def main_task_checkbox_stateChanged(self):
        self.usersettings.enable_list[0] = self.main_task_checkbox.isChecked()

    def side_task_checkbox_stateChanged(self):
        self.usersettings.enable_list[1] = self.side_task_checkbox.isChecked()

    def daily_task_checkbox_stateChanged(self):
        self.usersettings.enable_list[2] = self.daily_task_checkbox.isChecked()

    def active_task_checkbox_stateChanged(self):
        self.usersettings.enable_list[3] = self.active_task_checkbox.isChecked()

    def auto_use_item_checkbox_stateChanged(self):
        self.usersettings.auto_use_item_enabled = (
            self.auto_use_item_checkbox.isChecked()
        )

    def challenge4level_checkbox_stateChanged(self):
        self.usersettings.challenge4Level_enabled = (
            self.challenge4level_checkbox.isChecked()
        )

    def challenge4level_setting_btn_clicked(self):
        self.challenge4level_setting_window = Challenge4levelSettingWindow(
            self.usersettings, parent=self
        )
        self.challenge4level_setting_window.show()

    def auto_use_item_setting_btn_clicked(self):
        self.auto_use_item_setting_window = AutoUseItemSettingWindow(
            self.usersettings, parent=self
        )
        self.auto_use_item_setting_window.show()

    def closeEvent(self, a0) -> None:
        self.usersettings.save()
        return super().closeEvent(a0)


class FunctionPanelWindow(QMainWindow):
    def __init__(self, usersettings: UserSettings, parent=None):
        super().__init__(parent=parent)
        self.usersettings = usersettings
        self.init_ui()

    def init_ui(self):
        # 将窗口居中显示，宽度为显示器宽度的50%，高度为显示器高度的70%
        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.5), int(screen_size.height() * 0.7))
        self.move(int(screen_size.width() * 0.25), int(screen_size.height() * 0.15))
        self.setWindowTitle("功能面板")

        main_widget = QWidget()
        main_layout = QHBoxLayout()

        left_panel = QWidget()
        left_panel.setFixedWidth(int(self.width() * 0.2))
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("植物列表"))
        self.plant_list = QListWidget()
        self.plant_list.addItems(
            [
                f"{plant.name(self.usersettings.lib)}({plant.grade})"
                for plant in self.usersettings.repo.plants
            ]
        )
        left_layout.addWidget(self.plant_list)
        left_panel.setLayout(left_layout)
        main_layout.addWidget(left_panel)

        menu_widget = QWidget()
        menu_layout = QGridLayout()

        evolution_panel_btn = QPushButton("进化路线面板")
        evolution_panel_btn.clicked.connect(self.evolution_panel_btn_clicked)
        menu_layout.addWidget(evolution_panel_btn, 0, 0)

        upgrade_quality_btn = QPushButton("升品面板")
        upgrade_quality_btn.clicked.connect(self.upgrade_quality_btn_clicked)
        menu_layout.addWidget(upgrade_quality_btn, 1, 0)

        auto_synthesis_btn = QPushButton("自动合成面板")
        auto_synthesis_btn.clicked.connect(self.auto_synthesis_btn_clicked)
        menu_layout.addWidget(auto_synthesis_btn, 2, 0)

        heritage_btn = QPushButton("传承面板")
        heritage_btn.clicked.connect(self.heritage_btn_clicked)
        menu_layout.addWidget(heritage_btn, 3, 0)

        plant_relative_btn = QPushButton("植物相关面板")
        plant_relative_btn.clicked.connect(self.plant_relative_btn_clicked)
        menu_layout.addWidget(plant_relative_btn, 4, 0)

        menu_widget.setLayout(menu_layout)
        main_layout.addWidget(menu_widget)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def plant_relative_btn_clicked(self):
        self.plant_relative_window = PlantRelativeWindow(self.usersettings, parent=self)
        self.plant_relative_window.show()

    def heritage_btn_clicked(self):
        self.heritage_window = HeritageWindow(self.usersettings, parent=self)
        self.heritage_window.show()

    def upgrade_quality_btn_clicked(self):
        self.upgrade_quality_window = UpgradeQualityWindow(
            self.usersettings, parent=self
        )
        self.upgrade_quality_window.show()

    def evolution_panel_btn_clicked(self):
        self.evolution_panel_window = EvolutionPanelWindow(
            self.usersettings, parent=self
        )
        self.evolution_panel_window.show()

    def auto_synthesis_btn_clicked(self):
        self.auto_synthesis_window = AutoSynthesisWindow(self.usersettings, parent=self)
        self.auto_synthesis_window.show()

    def closeEvent(self, event):
        self.usersettings.save()
        return super().closeEvent(event)


class CustomMainWindow(QMainWindow):
    logger_signal = pyqtSignal()
    finish_trigger = pyqtSignal()

    def __init__(self, usersettings: UserSettings, cache_dir):
        super().__init__()
        self.usersettings = usersettings

        if not os.path.exists(cache_dir):
            os.mkdir(cache_dir)
        self.wr_cache = WebRequest(self.usersettings.cfg, cache_dir=cache_dir)

        self.init_ui()

        self.logger_signal.connect(self.update_text_box)
        self.usersettings.io_logger.set_signal(self.logger_signal)
        self.finish_trigger.connect(self.run_finished)

    def init_ui(self):
        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.7), int(screen_size.height() * 0.7))
        self.move(int(screen_size.width() * 0.15), int(screen_size.height() * 0.15))

        self.page_widget = QTabWidget()

        main_widget = QWidget()
        main_layout = QVBoxLayout()
        top_widget = QWidget()
        top_layout = QHBoxLayout()

        user_show_layout = QHBoxLayout()

        img = Image.open(
            BytesIO(
                self.wr_cache.get(
                    self.usersettings.user.face_url,
                    init_header="pvzol" in self.usersettings.cfg.host,
                    url_format=False,
                )
            )
        )
        img = img.resize((64, 64))
        user_face_img = QImage(
            img.tobytes(), img.width, img.height, QImage.Format.Format_RGB888
        )
        user_show_layout.addWidget(QLabel().setPixmap(QPixmap.fromImage(user_face_img)))

        user_info_layout = QVBoxLayout()
        user_info_layout.addWidget(QLabel(f"等级: {self.usersettings.user.grade}"))
        user_info_layout.addWidget(
            QLabel(
                f"经验值: {self.usersettings.user.exp_now}/{self.usersettings.user.exp_max}"
            )
        )
        user_info_layout.addWidget(QLabel(self.usersettings.user.name))
        user_show_layout.addLayout(user_info_layout)

        top_layout.addLayout(user_show_layout)
        top_layout.addStretch(1)

        # 设置top_layout的高度为main_layout的0.2倍
        top_widget.setFixedHeight(int(screen_size.height() * 0.1))
        top_widget.setLayout(top_layout)
        main_layout.addWidget(top_widget)

        # Middle Section
        middle_splitter = QSplitter(Qt.Orientation.Horizontal)
        middle_splitter.setFixedHeight(int(self.height() * 0.7))
        middle_splitter.setHandleWidth(10)
        middle_splitter.setStyleSheet(
            "QSplitter::handle{background: rgb(245, 245, 245);}"
        )

        # Left Panel
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_text_layout = QVBoxLayout()
        left_text_layout.setSpacing(5)
        left_text_layout.addWidget(QLabel(f"金币: {self.usersettings.user.money}"))
        left_text_layout.addWidget(
            QLabel(
                f"今日经验: {self.usersettings.user.today_exp} / {self.usersettings.user.today_exp_max}"
            )
        )
        left_text_layout.addWidget(
            QLabel(
                f"挑战次数: {self.usersettings.user.cave_amount} / {self.usersettings.user.cave_amount_max}"
            )
        )
        left_text_layout.addWidget(
            QLabel(
                f"领地次数: {self.usersettings.user.territory_amount} / {self.usersettings.user.territory_amount_max}"
            )
        )

        left_layout.addLayout(left_text_layout)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        self.process_button = process_button = QPushButton("开始")
        process_button.clicked.connect(self.process_button_clicked)
        clear_button = QPushButton("设置")
        clear_button.clicked.connect(self.open_setting_panel)
        button_layout.addWidget(process_button)
        button_layout.addWidget(clear_button)
        left_layout.addLayout(button_layout)

        # function button
        function_panel_open_layout = QHBoxLayout()
        function_panel_open_layout.setSpacing(10)
        self.function_panel_open_button = function_panel_open_button = QPushButton(
            "功能面板"
        )
        function_panel_open_button.clicked.connect(
            self.function_panel_open_button_clicked
        )
        function_panel_open_layout.addWidget(function_panel_open_button)
        left_layout.addLayout(function_panel_open_layout)

        refresh_repository_btn = QPushButton("刷新仓库")
        refresh_repository_btn.clicked.connect(self.refresh_repository_btn)
        left_layout.addWidget(refresh_repository_btn)

        left_layout.addStretch(1)

        left_layout.setSpacing(10)
        left_panel.setLayout(left_layout)

        # Right Panel
        right_panel = QWidget()
        right_layout = QVBoxLayout()

        # Large Text Box
        self.text_box = text_box = QPlainTextEdit()
        text_box.setReadOnly(True)

        right_layout.addWidget(text_box)
        right_panel.setLayout(right_layout)

        left_panel.setFixedWidth(int(screen_size.width() * 0.13))
        middle_splitter.addWidget(left_panel)
        middle_splitter.addWidget(right_panel)
        # 设置left_panel的宽度为screen的0.1倍
        main_layout.addWidget(middle_splitter)

        main_widget.setLayout(main_layout)
        self.page_widget.addTab(main_widget, "Main")
        # 设置主窗口常驻屏幕
        # self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)

        self.setCentralWidget(self.page_widget)
        self.setWindowTitle("Custom Window")

    def update_text_box(self):
        result = self.usersettings.io_logger.get_new_infos()
        document = self.text_box.document()
        # 冻结text_box显示，直到document更新完毕后更新
        self.text_box.viewport().setUpdatesEnabled(False)
        for info in reversed(result):
            cursor = QTextCursor(document)
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.insertText(info + "\n")
            # self.text_box.insertPlainText(info + "\n")
        self.text_box.viewport().setUpdatesEnabled(True)
        self.text_box.viewport().update()

    def open_setting_panel(self):
        self.settingWindow = SettingWindow(self.usersettings, parent=self)
        self.settingWindow.show()

    def run_finished(self):
        self.usersettings.logger.log("暂停运行")
        self.process_button.setText("开始")

    def refresh_repository_btn(self):
        self.usersettings.repo.refresh_repository()
        self.usersettings.logger.log("仓库刷新完成")

    def process_button_clicked(self):
        if self.process_button.text() == "开始":
            self.process_stop_channel = Queue(maxsize=1)
            self.process_button.setText("暂停")
            if self.process_stop_channel.qsize() > 0:
                self.process_stop_channel.get()
            self.usersettings.logger.log("开始运行")
            self.usersettings.start(self.process_stop_channel, self.finish_trigger)
        elif self.process_button.text() == "暂停":
            self.process_button.setText("开始")
            self.process_stop_channel.put(True)
        else:
            raise ValueError(f"Unknown button text: {self.process_button.text()}")

    def function_panel_open_button_clicked(self):
        self.function_panel_window = FunctionPanelWindow(self.usersettings, parent=self)
        self.function_panel_window.show()


class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.configs = []
        self.cfg_path = os.path.join(root_dir, "config/config.json")
        if os.path.exists(self.cfg_path):
            with open(self.cfg_path, "r", encoding="utf-8") as f:
                self.configs = json.load(f)
        self.init_ui()
        self.main_window_thread = []

    def init_ui(self):
        self.resize(500, 400)
        self.setWindowTitle("登录")

        main_widget = QWidget()
        main_layout = QVBoxLayout()

        login_user_widget = QWidget()
        login_user_layout = QVBoxLayout()
        login_user_layout.addWidget(QLabel("已登录的用户(双击登录，选中按delete或backspace删除)"))
        self.login_user_list = login_user_list = QListWidget()
        login_user_list.itemDoubleClicked.connect(self.login_list_item_double_clicked)
        login_user_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.refresh_login_user_list()
        login_user_layout.addWidget(login_user_list)
        login_user_widget.setLayout(login_user_layout)
        main_layout.addWidget(login_user_widget)

        username_widget = QWidget()
        username_layout = QHBoxLayout()
        username_layout.addWidget(QLabel("用户名(这个随便填):"))
        self.username_input = username_input = QLineEdit()
        username_layout.addWidget(username_input)
        username_widget.setLayout(username_layout)
        main_layout.addWidget(username_widget)

        region_widget = QWidget()
        region_layout = QHBoxLayout()
        region_layout.addWidget(QLabel("区服:"))
        self.region_input = region_input = QComboBox()
        region_input.addItems([f"官服{i}区" for i in range(12, 46 + 1)])
        region_input.addItems([f"私服{i}区" for i in range(1, 10)])
        region_layout.addWidget(region_input)
        region_widget.setLayout(region_layout)
        main_layout.addWidget(region_widget)

        cookie_widget = QWidget()
        cookie_layout = QHBoxLayout()
        cookie_layout.addWidget(QLabel("Cookie:"))
        self.cookie_input = cookie_input = QLineEdit()
        cookie_layout.addWidget(cookie_input)
        cookie_widget.setLayout(cookie_layout)
        main_layout.addWidget(cookie_widget)

        login_btn = QPushButton("登录")
        login_btn.clicked.connect(self.login_btn_clicked)
        main_layout.addWidget(login_btn)

        main_layout.addStretch(1)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def login_btn_clicked(self):
        # 取出当前选中的用户
        username = self.username_input.text()
        region_text = self.region_input.currentText()
        region = int(region_text[2:-1])
        if region_text.startswith("官服"):
            host = f"s{region}.youkia.pvz.youkia.com"
            server = "官服"
        elif region_text.startswith("私服"):
            host = "pvzol.org"
            server = "私服"
        else:
            raise ValueError(f"Unknown region text: {region_text}")
        cookie = self.cookie_input.text()
        if (cookie[0] == '"' and cookie[-1] == '"') or (
            cookie[0] == "'" and cookie[-1] == "'"
        ):
            cookie = cookie[1:-1]
        cfg = {
            "username": username,
            "host": host,
            "region": region,
            "cookie": cookie,
            "server": server,
        }
        for i, saved_cfg in enumerate(self.configs):
            if (
                saved_cfg["username"] == cfg["username"]
                and saved_cfg["host"] == cfg["host"]
                and saved_cfg["region"] == cfg["region"]
                and saved_cfg["server"] == cfg["server"]
            ):
                self.configs[i]["cookie"] = cfg["cookie"]
                break
        else:
            self.configs.append(cfg)
        self.save_config()
        self.refresh_login_user_list()
        # 强制重新渲染login窗口元素
        QApplication.processEvents()
        self.create_main_window(Config(cfg))

    def login_list_item_double_clicked(self, item):
        cfg_index = item.data(Qt.ItemDataRole.UserRole)
        self.create_main_window(Config(self.configs[cfg_index]))

    def create_main_window(self, cfg: Config):
        thread = GetUsersettings(cfg, root_dir)
        thread.finish_trigger.connect(self.get_usersettings_finished)
        self.main_window_thread.append(thread)
        thread.start()

    def get_usersettings_finished(self, args):
        main_window = CustomMainWindow(*args)
        main_window_list.append(main_window)
        main_window.show()

    def refresh_login_user_list(self):
        self.login_user_list.clear()
        for i, cfg in enumerate(self.configs):
            item = QListWidgetItem(
                "{}_{}_{}".format(cfg["username"], cfg["region"], cfg["host"])
            )
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.login_user_list.addItem(item)

    def save_config(self):
        with open(self.cfg_path, "w", encoding="utf-8") as f:
            json.dump(self.configs, f, indent=4, ensure_ascii=False)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Backspace or event.key() == Qt.Key.Key_Delete:
            if len(self.login_user_list.selectedItems()) == 0:
                return
            assert len(self.login_user_list.selectedItems()) == 1
            cfg_index = self.login_user_list.selectedItems()[0].data(
                Qt.ItemDataRole.UserRole
            )
            self.configs.pop(cfg_index)
            self.save_config()
            self.refresh_login_user_list()


class GetUsersettings(QThread):
    finish_trigger = pyqtSignal(tuple)

    def __init__(self, cfg: Config, root_dir):
        super().__init__()
        self.cfg = cfg
        self.root_dir = root_dir

    def run(self):
        data_dir = os.path.join(
            self.root_dir, f"data/{self.cfg.username}/{self.cfg.region}/{self.cfg.host}"
        )
        os.makedirs(data_dir, exist_ok=True)
        cache_dir = os.path.join(data_dir, "cache")
        os.makedirs(cache_dir, exist_ok=True)
        log_dir = os.path.join(data_dir, "log")
        os.makedirs(log_dir, exist_ok=True)
        setting_dir = os.path.join(data_dir, "usersettings")
        os.makedirs(setting_dir, exist_ok=True)

        max_info_capacity = 10
        # TODO: 从配置文件中读取
        logger = IOLogger(log_dir, max_info_capacity=max_info_capacity)
        logger_list.append(logger)
        usersettings = get_usersettings(self.cfg, logger, setting_dir)
        self.finish_trigger.emit((usersettings, cache_dir))


def get_usersettings(cfg, logger: IOLogger, setting_dir):
    # results = []
    # with concurrent.futures.ThreadPoolExecutor() as executor:
    #     futures = []
    #     futures.append(executor.submit(User, cfg))
    #     futures.append(executor.submit(Library, cfg))
    #     futures.append(executor.submit(Repository, cfg))

    #     for future in futures:
    #         results.append(future.result())

    user: User = User(cfg)
    lib: Library = Library(cfg)
    repo: Repository = Repository(cfg)

    caveMan: CaveMan = CaveMan(cfg, lib)

    usersettings = UserSettings(
        cfg,
        repo,
        lib,
        user,
        caveMan,
        logger,
        setting_dir,
    )
    if not os.path.exists(setting_dir):
        os.mkdir(setting_dir)
        usersettings.save()
    else:
        usersettings.load()

    return usersettings


if __name__ == "__main__":
    # 设置logging监听等级为INFO
    logging.basicConfig(level=logging.INFO)  # 如果不想让控制台输出那么多信息，可以将这一行注释掉
    # 取root_dir为可执行文件的目录
    root_dir = os.getcwd()
    os.makedirs(os.path.join(root_dir, "config"), exist_ok=True)

    try:
        app = QApplication(sys.argv)
        logger_list = []
        main_window_list = []
        login_window = LoginWindow()
        login_window.show()
        app_return = app.exec()
    except Exception as e:
        print(str(e))
    for log in logger_list:
        log.close()
    for main_window in main_window_list:
        main_window.usersettings.save()
    os.system("pause")
    sys.exit(app_return)
