import sys
from io import BytesIO
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
)
from PyQt6.QtGui import QImage, QPixmap, QFont, QTextCursor
from PyQt6.QtCore import Qt, pyqtSignal
from PIL import Image

from pypvz import WebRequest, Config, User, CaveMan, Repository, Library
from pypvz.ui import IOLogger
from pypvz.ui.user import SingleCave, UserSettings

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


class AddCaveWindow(QMainWindow):
    cave_add_update = pyqtSignal()

    def __init__(self, usersettings: UserSettings, parent=None):
        super().__init__(parent=parent)
        self.usersettings = usersettings
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("练级设置")

        # 将窗口居中显示，宽度为显示器宽度的30%，高度为显示器高度的50%
        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.3), int(screen_size.height() * 0.5))
        self.move(int(screen_size.width() * 0.35), int(screen_size.height() * 0.25))

        main_widget = QWidget()
        main_layout = QHBoxLayout()

        cave_type_widget = QWidget()
        cave_type_layout = QVBoxLayout()
        cave_type_layout.addWidget(QLabel("洞口类型"))
        cave_type_list_widget = QListWidget()
        cave_type_layout.addWidget(cave_type_list_widget)
        cave_type_widget.setLayout(cave_type_layout)
        main_layout.addWidget(cave_type_widget)

        cave_widget = QWidget()
        cave_layout = QVBoxLayout()
        cave_layout.addWidget(QLabel("洞口"))
        cave_list_widget = QListWidget()
        cave_layout.addWidget(cave_list_widget)
        cave_widget.setLayout(cave_layout)
        main_layout.addWidget(cave_widget)

        main_widget.setLayout(main_layout)

        self.setCentralWidget(main_widget)

        self.cave_list_widget = cave_list_widget
        self.cave_type_list_widget = cave_type_list_widget
        for i in range(3):
            item = QListWidgetItem("暗夜狩猎场-{}层".format(i + 1))
            item.setData(Qt.ItemDataRole.UserRole, {"type": 1, "layer": i + 1})
            cave_type_list_widget.addItem(item)
        for i in range(3):
            item = QListWidgetItem("僵尸狩猎场-{}层".format(i + 1))
            item.setData(Qt.ItemDataRole.UserRole, {"type": 2, "layer": i + 1})
            cave_type_list_widget.addItem(item)
        for i in range(3):
            item = QListWidgetItem("个人狩猎场-{}层".format(i + 1))
            item.setData(Qt.ItemDataRole.UserRole, {"type": 3, "layer": i + 1})
            cave_type_list_widget.addItem(item)
        stone_chapter_name = [
            '神秘洞穴',
            '光明圣城',
            '黑暗之塔',
            '僵尸坟场',
            '古老树屋',
            '亡灵沼泽',
            '冰岛',
            '末日火山',
            '天空之岛',
        ]
        for i, name in enumerate(stone_chapter_name):
            item = QListWidgetItem("宝石副本-" + name)
            item.setData(Qt.ItemDataRole.UserRole, {"type": 4, "layer": i + 1})
            cave_type_list_widget.addItem(item)
        cave_type_list_widget.itemClicked.connect(self.cave_type_list_widget_clicked)
        cave_list_widget.itemClicked.connect(self.cave_list_widget_clicked)

    def get_caves(self, cave_type, cave_layer):
        if not hasattr(self, "_caves"):
            self._caves = {}
        format_name = "{}-{}".format(cave_type, cave_layer)
        result = self._caves.get(format_name)
        if result is None:
            if cave_type <= 3:
                caves = self.usersettings.caveMan.get_caves(
                    self.usersettings.user.id, cave_type, cave_layer
                )
            elif cave_type == 4:
                caves = self.usersettings.caveMan.get_caves(cave_layer, cave_type)
            else:
                raise NotImplementedError
            result = self._caves[format_name] = caves
        return result

    def cave_type_list_widget_clicked(self, item: QListWidgetItem):
        cave_type = item.data(Qt.ItemDataRole.UserRole)
        cave_type, cave_layer = cave_type["type"], cave_type["layer"]
        self.cave_list_widget.clear()
        caves = self.get_caves(cave_type, cave_layer)
        if cave_type <= 3:
            for cave in caves:
                if cave.cave_id is None:
                    break
                item = QListWidgetItem(cave.format_name())
                item.setData(Qt.ItemDataRole.UserRole, cave)
                self.cave_list_widget.addItem(item)
        elif cave_type == 4:
            for cave in caves:
                item = QListWidgetItem(cave.format_name())
                item.setData(Qt.ItemDataRole.UserRole, cave)
                self.cave_list_widget.addItem(item)
        else:
            raise NotImplementedError

    def cave_list_widget_clicked(self, item: QListWidgetItem):
        cave = item.data(Qt.ItemDataRole.UserRole)
        self.usersettings.add_cave_challenge4Level(cave)
        self.cave_add_update.emit()


class SetPlantListWindow(QMainWindow):
    def __init__(
        self,
        repo: Repository,
        lib: Library,
        sign,
        origin_plant_id_list=None,
        parent=None,
    ):
        super().__init__(parent=parent)
        self.repo = repo
        self.lib = lib
        self.sign = sign
        self.origin_plant_id_list = origin_plant_id_list
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("植物选择")

        # 将窗口居中显示，宽度为显示器宽度的15%，高度为显示器高度的35%
        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.15), int(screen_size.height() * 0.35))
        self.move(int(screen_size.width() * 0.425), int(screen_size.height() * 0.325))

        main_widget = QWidget()
        main_layout = QVBoxLayout()

        origin_plant_id_set = set(self.origin_plant_id_list)
        self.plant_list = plant_list = QListWidget()
        for plant in self.repo.plants:
            if plant.id in origin_plant_id_set:
                continue
            item = QListWidgetItem(f"{plant.name(self.lib)} ({plant.grade})")
            item.setData(Qt.ItemDataRole.UserRole, plant)
            plant_list.addItem(item)
        # 设置plant_list的selectmode为多选
        plant_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        main_layout.addWidget(plant_list)

        button_widget = QWidget()
        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        ok_button.clicked.connect(self.ok_button_clicked)
        no_button = QPushButton("取消")
        no_button.clicked.connect(self.close)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(no_button)
        button_widget.setLayout(button_layout)
        main_layout.addWidget(button_widget)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def ok_button_clicked(self):
        result = []
        for item in self.plant_list.selectedItems():
            result.append(item.data(Qt.ItemDataRole.UserRole).id)
        self.sign.emit(result)
        self.close()


class Challenge4level_setting_window(QMainWindow):
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

        right_panel.setLayout(right_panel_layout)
        main_layout.addWidget(right_panel)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

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
            plant = self.usersettings.repo.id2plant[plant_id]
            item = QListWidgetItem(
                f"{plant.name(self.usersettings.lib)} ({plant.grade})"
            )
            item.setData(Qt.ItemDataRole.UserRole, plant)
            self.main_plant_list.addItem(item)

    def update_trash_plant_list(self):
        self.trash_plant_list.clear()
        for plant_id in self.usersettings.challenge4Level.trash_plant_list:
            plant = self.usersettings.repo.id2plant[plant_id]
            item = QListWidgetItem(
                f"{plant.name(self.usersettings.lib)} ({plant.grade})"
            )
            item.setData(Qt.ItemDataRole.UserRole, plant)
            self.trash_plant_list.addItem(item)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
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
        challenge4level_checkbox = QCheckBox("练级")
        challenge4level_checkbox.setFont(normal_font)
        challenge4level_checkbox.setChecked(self.usersettings.challenge4Level_enabled)
        challenge4level_checkbox.stateChanged.connect(
            self.challenge4level_checkbox_stateChanged
        )
        challenge4level_layout.addWidget(challenge4level_checkbox)
        challenge4level_layout.addStretch(1)
        challenge4level_setting_btn = QPushButton("设置")
        challenge4level_setting_btn.clicked.connect(
            self.challenge4level_setting_btn_clicked
        )
        challenge4level_layout.addWidget(challenge4level_setting_btn)
        challenge4level_widget.setLayout(challenge4level_layout)
        menu_layout.addWidget(challenge4level_widget, 0, 0)

        menu_widget.setLayout(menu_layout)
        main_layout.addWidget(menu_widget)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def challenge4level_checkbox_stateChanged(self):
        self.usersettings.challenge4Level_enabled = (
            not self.usersettings.challenge4Level_enabled
        )

    def challenge4level_setting_btn_clicked(self):
        self.challenge4level_setting_window = Challenge4level_setting_window(
            self.usersettings, parent=self
        )
        self.challenge4level_setting_window.show()

    def closeEvent(self, a0) -> None:
        self.usersettings.save()
        return super().closeEvent(a0)


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

        self.setup_ui()

        self.logger_signal.connect(self.update_text_box)
        self.logger.set_signal(self.logger_signal)
        self.finish_trigger.connect(self.run_finished)

    def setup_ui(self):
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
        self.process_stop_channel = Queue(maxsize=1)
        if self.process_button.text() == "开始":
            self.process_button.setText("暂停")
            if self.process_stop_channel.qsize() > 0:
                self.process_stop_channel.get()
            self.usersettings.start(self.process_stop_channel, self.finish_trigger, self.logger.new_logger())
        elif self.process_button.text() == "暂停":
            self.process_button.setText("开始")
            self.process_stop_channel.put(True)
        else:
            raise ValueError(f"Unknown button text: {self.process_button.text()}")


if __name__ == "__main__":
    # 设置logging监听等级为INFO
    logging.basicConfig(level=logging.INFO)  # 如果不想让控制台输出那么多信息，可以将这一行注释掉

    abs_file_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(abs_file_dir, "config/config.json")
    # config_path = os.path.join(abs_file_dir, "config/24config.json")
    data_dir = os.path.join(abs_file_dir, "data")
    if not os.path.exists(data_dir):
        os.mkdir(data_dir)
    cache_dir = os.path.join(data_dir, "cache")
    if not os.path.exists(cache_dir):
        os.mkdir(cache_dir)
    log_dir = os.path.join(data_dir, "log")
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)
    setting_dir = os.path.join(data_dir, "usersettings")
    if not os.path.exists(setting_dir):
        os.mkdir(setting_dir)

    max_info_capacity = 10
    # TODO: 从配置文件中读取
    logger = IOLogger(log_dir, max_info_capacity=max_info_capacity)
    cfg = Config(config_path)
    app = QApplication(sys.argv)
    window = CustomMainWindow(cfg, setting_dir, cache_dir, logger)
    window.show()
    try:
        sys.exit(app.exec())
    finally:
        logger.close()
