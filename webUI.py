import sys
import json
from io import BytesIO
import typing
from PyQt6 import QtGui
import os
import logging
import concurrent.futures
from queue import Queue

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
from PyQt6.QtGui import QImage, QPixmap, QFont, QTextCursor
from PyQt6.QtCore import Qt, pyqtSignal
from PIL import Image

from pypvz import WebRequest, Config, User, CaveMan, Repository, Library
from pypvz.ui.message import IOLogger
from pypvz.ui.wrapped import QLabel, normal_font
from pypvz.ui.windows import EvolutionPanelWindow, SetPlantListWindow, AddCaveWindow, AutoUseItemSettingWindow
from pypvz.ui.user import SingleCave, UserSettings


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
        self.resize(int(screen_size.width() * 0.4), int(screen_size.height() * 0.6))
        self.move(int(screen_size.width() * 0.3), int(screen_size.height() * 0.2))

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
        cave_list = QListWidget()
        self.cave_list = cave_list
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
        friend_list = QListWidget()
        self.friend_list = friend_list
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

        free_max_input_widget = QWidget()
        free_max_input_layout = QHBoxLayout()
        free_max_input_box = QSpinBox()
        free_max_input_box.setMinimum(0)
        free_max_input_box.setMaximum(10)
        free_max_input_box.setValue(self.usersettings.challenge4Level.free_max)

        def free_max_input_box_value_changed(value):
            self.usersettings.challenge4Level.free_max = value

        free_max_input_box.valueChanged.connect(free_max_input_box_value_changed)
        free_max_input_layout.addWidget(QLabel("出战植物最大空位数:"))
        free_max_input_layout.addWidget(free_max_input_box)
        free_max_input_widget.setLayout(free_max_input_layout)
        right_panel_layout.addWidget(free_max_input_widget)

        stone_cave_challenge_max_attempts_widget = QWidget()
        stone_cave_challenge_max_attempts_layout = QHBoxLayout()
        stone_cave_challenge_max_attempts_box = QSpinBox()
        stone_cave_challenge_max_attempts_box.setMinimum(0)
        stone_cave_challenge_max_attempts_box.setMaximum(999)
        stone_cave_challenge_max_attempts_box.setValue(
            self.usersettings.challenge4Level.stone_cave_challenge_max_attempts
        )

        def stone_cave_challenge_max_attempts_box_value_changed(value):
            self.usersettings.challenge4Level.stone_cave_challenge_max_attempts = value

        stone_cave_challenge_max_attempts_box.valueChanged.connect(
            stone_cave_challenge_max_attempts_box_value_changed
        )
        stone_cave_challenge_max_attempts_layout.addWidget(QLabel("宝石副本最大挑战次数:"))
        stone_cave_challenge_max_attempts_layout.addWidget(
            stone_cave_challenge_max_attempts_box
        )
        stone_cave_challenge_max_attempts_widget.setLayout(
            stone_cave_challenge_max_attempts_layout
        )
        right_panel_layout.addWidget(stone_cave_challenge_max_attempts_widget)

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
        right_panel.setLayout(right_panel_layout)
        main_layout.addWidget(right_panel)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def hp_choice_box_currentIndexChanged(self, index):
        self.usersettings.challenge4Level.hp_choice = self.hp_choice_list[index]

    def update_selectd_cave(self):
        self.update_friend_list()

    def cave_list_item_clicked(self, item):
        self.selectd_cave = item.data(Qt.ItemDataRole.UserRole)
        self.selectd_cave_update.emit()
        self.delete_last_selected_list = self.cave_list

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
                        self.usersettings.remove_cave_challenge4Level(sc.cave)
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
        self.challenge4level_checkbox = challenge4level_checkbox = QCheckBox("练级")
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
        shop_enable_layout.addStretch(1)
        shop_enable_widget.setLayout(shop_enable_layout)
        menu_layout.addWidget(shop_enable_widget, 1, 0)
        
        daily_task_widget = QWidget()
        daily_task_layout = QHBoxLayout()
        self.daily_task_checkbox = daily_task_checkbox = QCheckBox("日常任务领取")
        daily_task_checkbox.setFont(normal_font)
        daily_task_checkbox.setChecked(self.usersettings.daily_task_enabled)
        daily_task_checkbox.stateChanged.connect(
            self.daily_task_checkbox_stateChanged
        )
        daily_task_layout.addWidget(daily_task_checkbox)
        daily_task_layout.addStretch(1)
        daily_task_widget.setLayout(daily_task_layout)
        menu_layout.addWidget(daily_task_widget, 2, 0)
        
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
        auto_use_item_setting_btn.clicked.connect(self.auto_use_item_setting_btn_clicked)
        auto_use_item_layout.addWidget(auto_use_item_setting_btn)
        auto_use_item_layout.addStretch(1)
        auto_use_item_widget.setLayout(auto_use_item_layout)
        menu_layout.addWidget(auto_use_item_widget, 3, 0)

        menu_widget.setLayout(menu_layout)
        main_layout.addWidget(menu_widget)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def shop_enable_checkbox_stateChanged(self):
        self.usersettings.shop_enabled = self.shop_enable_checkbox.isChecked()
        
    def daily_task_checkbox_stateChanged(self):
        self.usersettings.daily_task_enabled = self.daily_task_checkbox.isChecked()
        
    def auto_use_item_checkbox_stateChanged(self):
        self.usersettings.auto_use_item_enabled = self.auto_use_item_checkbox.isChecked()

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

        menu_widget.setLayout(menu_layout)
        main_layout.addWidget(menu_widget)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def evolution_panel_btn_clicked(self):
        self.evolution_panel_window = EvolutionPanelWindow(
            self.usersettings, parent=self
        )
        self.evolution_panel_window.show()

    def closeEvent(self, event):
        self.usersettings.save()
        return super().closeEvent(event)


class CustomMainWindow(QMainWindow):
    logger_signal = pyqtSignal()
    finish_trigger = pyqtSignal()

    def __init__(self, cfg: Config, setting_dir, cache_dir, logger: IOLogger):
        super().__init__()
        self.cfg = cfg
        self.logger = logger

        results = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []
            futures.append(executor.submit(User, cfg))
            futures.append(executor.submit(Library, cfg))
            futures.append(executor.submit(Repository, cfg))

            for future in futures:
                results.append(future.result())

        self.user: User = results[0]
        self.lib: Library = results[1]
        self.repo: Repository = results[2]

        self.caveMan: CaveMan = CaveMan(cfg, self.lib)

        self.usersettings = UserSettings(
            cfg,
            self.repo,
            self.lib,
            self.user,
            self.caveMan,
            logger,
            setting_dir,
        )
        if not os.path.exists(setting_dir):
            os.mkdir(setting_dir)
            self.usersettings.save()
        else:
            self.usersettings.load()

        if not os.path.exists(cache_dir):
            os.mkdir(cache_dir)
        self.wr_cache = WebRequest(cfg, cache_dir=cache_dir)

        self.init_ui()

        self.logger_signal.connect(self.update_text_box)
        self.logger.set_signal(self.logger_signal)
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
                    self.user.face_url,
                    need_region=False,
                    use_cache=True,
                    init_header=False,
                )
            )
        )
        user_face_img = QImage(
            img.tobytes(), img.width, img.height, QImage.Format.Format_RGB888
        )
        user_show_layout.addWidget(QLabel().setPixmap(QPixmap.fromImage(user_face_img)))

        user_info_layout = QVBoxLayout()
        user_info_layout.addWidget(QLabel(f"等级: {self.user.grade}"))
        user_info_layout.addWidget(
            QLabel(f"经验值: {self.user.exp_now}/{self.user.exp_max}")
        )
        user_info_layout.addWidget(QLabel(self.user.name))
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
        left_text_layout.addWidget(QLabel(f"金币: {self.user.money}"))
        left_text_layout.addWidget(
            QLabel(f"今日经验: {self.user.today_exp} / {self.user.today_exp_max}")
        )
        left_text_layout.addWidget(
            QLabel(f"挑战次数: {self.user.cave_amount} / {self.user.cave_amount_max}")
        )
        left_text_layout.addWidget(
            QLabel(
                f"领地次数: {self.user.territory_amount} / {self.user.territory_amount_max}"
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

        # # List Widget
        # list_widget = QListWidget()
        # list_widget.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        # left_layout.addWidget(list_widget)
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
        result = self.logger.get_new_infos()
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
        self.process_button.setText("开始")

    def process_button_clicked(self):
        if self.process_button.text() == "开始":
            self.process_stop_channel = Queue(maxsize=1)
            self.usersettings.repo.refresh_repository()
            self.process_button.setText("暂停")
            if self.process_stop_channel.qsize() > 0:
                self.process_stop_channel.get()
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
        username_layout.addWidget(QLabel("用户名:"))
        self.username_input = username_input = QLineEdit()
        username_layout.addWidget(username_input)
        username_widget.setLayout(username_layout)
        main_layout.addWidget(username_widget)

        region_widget = QWidget()
        region_layout = QHBoxLayout()
        region_layout.addWidget(QLabel("区服:"))
        self.region_input = region_input = QComboBox()
        region_input.addItems([str(i) for i in range(12, 46 + 1)])
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
        region = int(self.region_input.currentText())
        cookie = self.cookie_input.text()
        if (cookie[0] == '"' and cookie[-1] == '"') or (
            cookie[0] == "'" and cookie[-1] == "'"
        ):
            cookie = cookie[1:-1]
        cfg = {
            "username": username,
            "region": region,
            "cookie": cookie,
        }
        self.configs.append(cfg)
        self.save_config()
        self.refresh_login_user_list()
        # 强制重新渲染login窗口元素
        QApplication.processEvents()
        show_main_window(Config(cfg))

    def login_list_item_double_clicked(self, item):
        cfg_index = item.data(Qt.ItemDataRole.UserRole)
        show_main_window(Config(self.configs[cfg_index]))

    def refresh_login_user_list(self):
        self.login_user_list.clear()
        for i, cfg in enumerate(self.configs):
            item = QListWidgetItem("{}_{}".format(cfg["username"], cfg["region"]))
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


def show_main_window(cfg: Config):
    data_dir = os.path.join(root_dir, f"data/{cfg.username}/{cfg.region}")
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
    window = CustomMainWindow(cfg, setting_dir, cache_dir, logger)
    main_window_list.append(window)
    window.show()


if __name__ == "__main__":
    # 设置logging监听等级为INFO
    logging.basicConfig(level=logging.INFO)  # 如果不想让控制台输出那么多信息，可以将这一行注释掉
    # 取root_dir为可执行文件的目录
    root_dir = os.getcwd()
    os.makedirs(os.path.join(root_dir, "config"), exist_ok=True)

    app = QApplication(sys.argv)
    logger_list = []
    main_window_list = []
    login_window = LoginWindow()
    login_window.show()
    app_return = app.exec()
    for log in logger_list:
        log.close()
    os.system("pause")
    sys.exit(app_return)
