import logging
import threading
from queue import Queue
from copy import deepcopy
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QTabWidget,
    QPlainTextEdit,
    QComboBox,
    QCheckBox,
    QApplication,
    QSpinBox,
)
from PyQt6.QtGui import QPixmap
from PyQt6 import QtGui
from PyQt6.QtCore import Qt, pyqtSignal

from ...repository import Repository
from ...library import Library
from ..wrapped import QLabel
from ..user import UserSettings
from ...upgrade import SkillStoneMan
from ...utils.common import format_number
from ...repository import Plant


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


class AddCaveWindow(QMainWindow):
    cave_add_update: pyqtSignal = pyqtSignal()

    def __init__(self, usersettings: UserSettings, parent=None):
        super().__init__(parent=parent)
        self.usersettings = usersettings
        self.init_ui()
        self.refresh_cave_list()

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
        cave_type_layout.addWidget(QLabel("洞口类型"))
        self.cave_type_list_widget = QListWidget()
        cave_type_layout.addWidget(self.cave_type_list_widget)
        cave_type_widget.setLayout(cave_type_layout)
        main_layout.addWidget(cave_type_widget)

        cave_widget = QWidget()
        cave_widget.setFixedWidth(int(self.width() * 0.4))
        cave_layout = QVBoxLayout()
        cave_layout.addWidget(QLabel("洞口"))
        self.cave_list_widget = QListWidget()
        cave_layout.addWidget(self.cave_list_widget)
        cave_widget.setLayout(cave_layout)
        main_layout.addWidget(cave_widget)

        widget3 = QWidget()
        widget3_layout = QVBoxLayout()
        self.need_use_sand = QCheckBox("使用时之沙")
        self.need_use_sand.setChecked(False)
        widget3_layout.addWidget(self.need_use_sand)
        widget3_1_layout = QHBoxLayout()
        widget3_1_layout.addWidget(QLabel("洞口难度:"))
        self.difficulty_choice = QComboBox()
        difficulty = ["简单", "普通", "困难"]
        self.difficulty_choice.addItems(difficulty)
        self.difficulty_choice.setCurrentIndex(2)
        widget3_1_layout.addWidget(self.difficulty_choice)
        widget3_layout.addLayout(widget3_1_layout)
        if self.usersettings.cfg.server == "私服":
            result = self.usersettings.challenge4Level.caveMan.switch_garden_layer(
                1, self.usersettings.logger
            )
            widget3_2_layout = QHBoxLayout()
            widget3_2_layout.addWidget(QLabel("选择花园层级:"))
            self.usersettings.logger.log(result["result"])
            if not result["success"]:
                self.close()
            self.current_garden_layer_choice = QComboBox()
            self.current_garden_layer_choice.addItems(["1", "2", "3", "4"])
            self.current_garden_layer_choice.setCurrentIndex(0)
            self.current_garden_layer_choice.currentIndexChanged.connect(
                self.current_garden_layer_choice_currentIndexChanged
            )
            widget3_2_layout.addWidget(self.current_garden_layer_choice)
            widget3_layout.addLayout(widget3_2_layout)
        widget3.setLayout(widget3_layout)
        main_layout.addWidget(widget3)

        main_widget.setLayout(main_layout)

        self.setCentralWidget(main_widget)

        for i in range(3):
            item = QListWidgetItem("暗夜狩猎场-{}层".format(i + 1))
            item.setData(Qt.ItemDataRole.UserRole, {"type": 1, "layer": i + 1})
            self.cave_type_list_widget.addItem(item)
        for i in range(4):
            item = QListWidgetItem("僵尸狩猎场-{}层".format(i + 1))
            item.setData(Qt.ItemDataRole.UserRole, {"type": 2, "layer": i + 1})
            self.cave_type_list_widget.addItem(item)
        for i in range(4):
            item = QListWidgetItem("个人狩猎场-{}层".format(i + 1))
            item.setData(Qt.ItemDataRole.UserRole, {"type": 3, "layer": i + 1})
            self.cave_type_list_widget.addItem(item)
        stone_chapter_name = [
            "神秘洞穴",
            "光明圣城",
            "黑暗之塔",
            "僵尸坟场",
            "古老树屋",
            "亡灵沼泽",
            "冰岛",
            "末日火山",
            "天空之岛",
        ]
        for i, name in enumerate(stone_chapter_name):
            item = QListWidgetItem("宝石副本-" + name)
            item.setData(Qt.ItemDataRole.UserRole, {"type": 4, "layer": i + 1})
            self.cave_type_list_widget.addItem(item)
        self.cave_type_list_widget.itemClicked.connect(
            self.cave_type_list_widget_clicked
        )
        self.cave_list_widget.itemClicked.connect(self.cave_list_widget_clicked)

    def refresh_cave_list(self):
        if not hasattr(self, "current_cave_type"):
            return
        cave_type, cave_layer = (
            self.current_cave_type["type"],
            self.current_cave_type["layer"],
        )
        self.cave_list_widget.clear()
        caves = self.get_caves(cave_type, cave_layer)
        if cave_type <= 3:
            for cave in caves:
                if cave.cave_id is None:
                    self.usersettings.logger.log("洞口{}异常".format(cave.format_name()))
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

    def current_garden_layer_choice_currentIndexChanged(self, index):
        self.usersettings.challenge4Level.caveMan.switch_garden_layer(
            index + 1, self.usersettings.logger
        )
        self.refresh_cave_list()

    def get_caves(self, cave_type, cave_layer):
        if not hasattr(self, "_caves"):
            self._caves = {}
        format_name = "{}-{}".format(cave_type, cave_layer)
        if self.usersettings.cfg.server == "私服" and cave_type <= 3:
            format_name += "-{}".format(self.current_garden_layer_choice.currentIndex())
        result = self._caves.get(format_name)
        if result is None:
            if cave_type <= 3:
                caves = self.usersettings.caveMan.get_caves(
                    self.usersettings.user.id,
                    cave_type,
                    cave_layer,
                    logger=self.usersettings.logger,
                )
            elif cave_type == 4:
                caves = self.usersettings.caveMan.get_caves(
                    cave_layer, cave_type, logger=self.usersettings.logger
                )
            else:
                raise NotImplementedError
            result = self._caves[format_name] = caves
        return result

    def cave_type_list_widget_clicked(self, item: QListWidgetItem):
        self.current_cave_type = item.data(Qt.ItemDataRole.UserRole)
        self.refresh_cave_list()

    def cave_list_widget_clicked(self, item: QListWidgetItem):
        cave = item.data(Qt.ItemDataRole.UserRole)
        if self.usersettings.cfg.server == "私服":
            self.usersettings.challenge4Level.add_cave(
                cave,
                difficulty=self.difficulty_choice.currentIndex() + 1,
                garden_layer=self.current_garden_layer_choice.currentIndex() + 1,
            )
        else:
            self.usersettings.challenge4Level.add_cave(
                cave, difficulty=self.difficulty_choice.currentIndex() + 1
            )
        self.cave_add_update.emit()


class AutoUseItemSettingWindow(QMainWindow):
    def __init__(self, usersettings: UserSettings, parent=None):
        super().__init__(parent=parent)
        self.usersettings = usersettings
        self.init_ui()
        self.refresh_item_list()
        self.refresh_auto_use_item_list()
        self.refresh_plant_list()

    def init_ui(self):
        self.setWindowTitle("自动使用道具设置")

        # 将窗口居中显示，宽度为显示器宽度的30%，高度为显示器高度的50%
        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.5), int(screen_size.height() * 0.5))
        self.move(int(screen_size.width() * 0.25), int(screen_size.height() * 0.25))

        main_widget = QWidget()
        main_layout = QHBoxLayout()

        item_list_widget = QWidget()
        item_list_widget.setFixedWidth(int(self.width() * 0.35))
        item_list_layout = QVBoxLayout()
        item_list_layout.addWidget(QLabel("道具列表"))

        self.item_list_tab = item_list_tab = QTabWidget()
        self.item_list = QListWidget()
        self.item_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        item_list_tab.addTab(self.item_list, "道具")
        self.box_list = QListWidget()
        self.box_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        item_list_tab.addTab(self.box_list, "宝箱")
        self.plant_list = QListWidget()
        self.plant_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        item_list_tab.addTab(self.plant_list, "植物")
        item_list_layout.addWidget(item_list_tab)

        item_list_widget.setLayout(item_list_layout)
        main_layout.addWidget(item_list_widget)

        use_item_panel_widget = QWidget()
        use_item_panel_layout = QVBoxLayout()
        use_item_panel_layout.addStretch(1)

        self.use_item_all_btn = use_item_all_btn = QPushButton("全部使用")
        use_item_all_btn.clicked.connect(self.use_item_all_btn_clicked)
        use_item_panel_layout.addWidget(use_item_all_btn)

        self.auto_use_item_btn = auto_use_item_btn = QPushButton("设为自动使用")
        auto_use_item_btn.clicked.connect(self.auto_use_item_btn_clicked)
        use_item_panel_layout.addWidget(auto_use_item_btn)

        part_use_widget = QWidget()
        part_use_layout = QHBoxLayout()
        self.part_use_amount = part_use_amount = QSpinBox()
        part_use_amount.setMinimum(1)
        part_use_amount.setMaximum(99999)
        part_use_amount.setValue(1)
        part_use_layout.addWidget(part_use_amount)
        self.part_use_item_btn = part_use_item_btn = QPushButton("部分使用")
        part_use_item_btn.clicked.connect(self.part_use_item_btn_clicked)
        part_use_layout.addWidget(part_use_item_btn)
        part_use_widget.setLayout(part_use_layout)
        use_item_panel_layout.addWidget(part_use_widget)

        self.sell_item_all_btn = sell_item_all_btn = QPushButton("全部出售")
        sell_item_all_btn.clicked.connect(self.sell_item_all_btn_clicked)
        use_item_panel_layout.addWidget(sell_item_all_btn)

        use_item_panel_layout.addStretch(1)
        use_item_panel_widget.setLayout(use_item_panel_layout)
        main_layout.addWidget(use_item_panel_widget)

        auto_use_item_list_widget = QWidget()
        auto_use_item_list_widget.setFixedWidth(int(self.width() * 0.35))
        auto_use_item_list_layout = QVBoxLayout()
        auto_use_item_list_layout.addWidget(QLabel("自动使用道具列表"))
        self.auto_use_item_list = QListWidget()
        self.auto_use_item_list.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection
        )
        auto_use_item_list_layout.addWidget(self.auto_use_item_list)
        auto_use_item_list_widget.setLayout(auto_use_item_list_layout)
        main_layout.addWidget(auto_use_item_list_widget)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def refresh_item_list(self):
        self.item_list.clear()
        self.box_list.clear()
        for tool in self.usersettings.repo.tools:
            lib_tool = self.usersettings.lib.get_tool_by_id(tool['id'])
            item = QListWidgetItem(f"{lib_tool.name}({tool['amount']})")
            item.setData(Qt.ItemDataRole.UserRole, tool['id'])
            if lib_tool.type != 3:
                self.item_list.addItem(item)
            if lib_tool.type == 3:
                self.box_list.addItem(item)

    def refresh_auto_use_item_list(self):
        self.auto_use_item_list.clear()
        for tool_id in self.usersettings.auto_use_item_list:
            lib_tool = self.usersettings.lib.get_tool_by_id(tool_id)
            item = QListWidgetItem(f"{lib_tool.name}")
            item.setData(Qt.ItemDataRole.UserRole, tool_id)
            self.auto_use_item_list.addItem(item)

    def refresh_plant_list(self):
        self.plant_list.clear()
        for plant in self.usersettings.repo.plants:
            item = QListWidgetItem(
                f"{plant.name(self.usersettings.lib)} ({plant.grade})[{plant.quality_str}]"
            )
            item.setData(Qt.ItemDataRole.UserRole, plant.id)
            self.plant_list.addItem(item)
        pass

    def part_use_item_btn_clicked(self):
        self.part_use_item_btn.setDisabled(True)
        QApplication.processEvents()
        try:
            cur_index = self.item_list_tab.currentIndex()
            if cur_index == 0:
                selected_items = self.item_list.selectedItems()
            elif cur_index == 1:
                selected_items = self.box_list.selectedItems()
            else:
                self.usersettings.logger.log("请选择道具或宝箱")
                return
            if len(selected_items) == 0:
                self.usersettings.logger.log("请先选中物品")
                return
            amount = self.part_use_amount.value()
            for item in selected_items:
                tool_id = item.data(Qt.ItemDataRole.UserRole)
                repo_tool = self.usersettings.repo.get_tool(tool_id)
                if repo_tool is None:
                    continue
                tool_type = self.usersettings.lib.get_tool_by_id(tool_id).type
                if tool_type == 3:
                    result = self.usersettings.repo.open_box(
                        tool_id, amount, self.usersettings.lib
                    )
                else:
                    result = self.usersettings.repo.use_item(
                        tool_id, amount, self.usersettings.lib
                    )
                self.usersettings.logger.log(result['result'])
                if not result['success']:
                    continue
            self.usersettings.repo.refresh_repository()
            self.refresh_item_list()
        except Exception as e:
            self.usersettings.logger.log(
                "部分使用道具出错，已暂停。原因类型：{}".format(type(e).__name__)
            )
        finally:
            self.part_use_item_btn.setEnabled(True)

    def use_item_all_btn_clicked(self):
        self.use_item_all_btn.setDisabled(True)
        QApplication.processEvents()
        try:
            cur_index = self.item_list_tab.currentIndex()
            if cur_index == 0:
                selected_items = self.item_list.selectedItems()
            elif cur_index == 1:
                selected_items = self.box_list.selectedItems()
            else:
                self.usersettings.logger.log("请选择道具或宝箱")
                return
            if len(selected_items) == 0:
                self.usersettings.logger.log("请先选中物品")
                return
            for item in selected_items:
                tool_id = item.data(Qt.ItemDataRole.UserRole)
                repo_tool = self.usersettings.repo.get_tool(tool_id)
                if repo_tool is None:
                    continue
                tool_type = self.usersettings.lib.get_tool_by_id(tool_id).type
                amount = repo_tool['amount']
                if tool_type == 3:
                    while amount > 0:
                        result = self.usersettings.repo.open_box(
                            tool_id, 99999, self.usersettings.lib
                        )
                        self.usersettings.logger.log(result['result'])
                        if not result['success']:
                            break
                        amount -= result['open_amount']
                else:
                    result = self.usersettings.repo.use_item(
                        tool_id, amount, self.usersettings.lib
                    )
                    self.usersettings.logger.log(result['result'])
            self.usersettings.repo.refresh_repository()
            self.refresh_item_list()
        except Exception as e:
            self.usersettings.logger.log(
                "全部使用道具出错，已暂停。原因类型：{}".format(type(e).__name__)
            )
        finally:
            self.use_item_all_btn.setEnabled(True)

    def auto_use_item_btn_clicked(self):
        cur_index = self.item_list_tab.currentIndex()
        if cur_index == 0:
            selected_items = self.item_list.selectedItems()
        elif cur_index == 1:
            selected_items = self.box_list.selectedItems()
        else:
            self.usersettings.logger.log("请选择道具或宝箱")
            return
        for item in selected_items:
            self.usersettings.auto_use_item_list.append(
                item.data(Qt.ItemDataRole.UserRole)
            )
        self.refresh_auto_use_item_list()

    def sell_item_all_btn_clicked(self):
        cur_index = self.item_list_tab.currentIndex()
        if cur_index == 0:
            selected_items = self.item_list.selectedItems()
        elif cur_index == 1:
            self.usersettings.logger.log("现在还暂时不开放宝箱售卖功能")
            return
        elif cur_index == 2:
            selected_items = self.plant_list.selectedItems()
        else:
            self.usersettings.logger.log("请选择道具或植物")
            return
        selected_data = [item.data(Qt.ItemDataRole.UserRole) for item in selected_items]
        if cur_index == 0:
            for tool_id in selected_data:
                repo_tool = self.usersettings.repo.get_tool(tool_id)
                if repo_tool is None:
                    continue
                tool_type = self.usersettings.lib.get_tool_by_id(tool_id).type
                amount = repo_tool['amount']
                if tool_type == 3:
                    logging.error("宝箱数据混入道具列表了")
                    continue
                result = self.usersettings.repo.sell_item(
                    tool_id, amount, self.usersettings.lib
                )
                self.usersettings.logger.log(result['result'])
        else:
            for plant_id in selected_data:
                repo_plant = self.usersettings.repo.get_plant(plant_id)
                if repo_plant is None:
                    continue
                result = self.usersettings.repo.sell_plant(
                    plant_id, repo_plant.info(lib=self.usersettings.lib)
                )
                self.usersettings.logger.log(result['result'])
        self.usersettings.repo.refresh_repository()
        if cur_index == 0:
            self.refresh_item_list()
        elif cur_index == 2:
            self.refresh_plant_list()
        else:
            raise RuntimeError

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            selected_item = self.auto_use_item_list.selectedItems()
            tool_id_list = [
                item.data(Qt.ItemDataRole.UserRole) for item in selected_item
            ]
            self.usersettings.auto_use_item_list = [
                tool_id
                for tool_id in self.usersettings.auto_use_item_list
                if tool_id not in tool_id_list
            ]
            self.refresh_auto_use_item_list()


class ChallengeGardenCaveSetting(QMainWindow):
    def __init__(self, usersettings: UserSettings, parent=None):
        super().__init__(parent=parent)
        self.usersettings = usersettings

    def init_ui(self):
        self.setWindowTitle("挑战花园设置")

        # 将窗口居中显示，宽度为显示器宽度的30%，高度为显示器高度的50%
        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.5), int(screen_size.height() * 0.5))
        self.move(int(screen_size.width() * 0.25), int(screen_size.height() * 0.25))

        main_widget = QWidget()
        main_layout = QHBoxLayout()

        friend_list_widget = QWidget()
        friend_list_widget.setFixedWidth(int(self.width() * 0.35))
        friend_list_layout = QVBoxLayout()
        friend_list_layout.addWidget(QLabel("好友列表"))
        self.friend_list = QListWidget()
        self.friend_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.friend_list.itemClicked.connect(self.friend_list_selection_changed)
        friend_list_layout.addWidget(self.friend_list)
        friend_list_widget.setLayout(friend_list_layout)
        self.text_box = QPlainTextEdit()
        self.text_box.setReadOnly(True)
        self.text_box.setFixedWidth(int(self.width() * 0.35))
        friend_list_layout.addWidget(self.text_box)
        main_layout.addWidget(friend_list_widget)
        self.refresh_friend_list()

        challenge_setting_btn = QPushButton("自动挑战")
        challenge_setting_btn.clicked.connect(self.challenge_setting_btn_clicked)
        main_layout.addWidget(challenge_setting_btn)

        challenge_list_widget = QWidget()
        challenge_list_widget.setFixedWidth(int(self.width() * 0.35))
        challenge_list_layout = QVBoxLayout()
        challenge_list_layout.addWidget(QLabel("挑战列表"))
        self.challenge_list = QListWidget()
        self.challenge_list.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection
        )
        challenge_list_layout.addWidget(self.challenge_list)
        challenge_list_widget.setLayout(challenge_list_layout)
        main_layout.addWidget(challenge_list_widget)
        self.refresh_challenge_list()

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def refresh_friend_list(self):
        self.friend_list.clear()
        for friend in self.usersettings.user.friendMan.friends:
            item = QListWidgetItem(f"{friend.name}({friend.grade})")
            item.setData(Qt.ItemDataRole.UserRole, friend.id)
            self.friend_list.addItem(item)

    def friend_list_selection_changed(self, item: QListWidgetItem):
        friend_id = item.data(Qt.ItemDataRole.UserRole)
        if not hasattr(self.usersettings.user.friendMan, "id2garden_cave"):
            setattr(self.usersettings.user.friendMan, "id2garden_cave", {})
        if friend_id not in self.usersettings.user.friendMan.id2garden_cave:
            self.usersettings.user.friendMan.id2garden_cave[
                friend_id
            ] = self.usersettings.caveMan.get_garden_cave(friend_id)
        garden_cave = self.usersettings.user.friendMan.id2garden_cave[friend_id]
        friend = self.usersettings.user.friendMan.id2friend[friend_id]
        if garden_cave is None:
            text = "该好友花园里暂时没有花园怪"
        else:
            text = "{}({})的花园:\n花园怪:{}\n奖励:{}".format(
                friend.name,
                friend.grade,
                garden_cave.name,
                ",".join([r.name for r in garden_cave.reward]),
            )
        self.text_box.setPlainText(text)

    def challenge_setting_btn_clicked(self):
        selected_friend = self.friend_list.selectedItems()
        selected_friend_id = [
            fid
            for fid in map(lambda x: x.data(Qt.ItemDataRole.UserRole), selected_friend)
            if (
                self.usersettings.user.friendMan.id2garden_cave.get(fid, None)
                is not None
            )
        ]
        if len(selected_friend_id) == 0:
            return
        garden_caves = []


class ShopAutoBuySetting(QMainWindow):
    def __init__(self, usersettings: UserSettings, parent=None):
        super().__init__(parent=parent)
        self.usersettings = usersettings
        self.usersettings.shop.refresh_shop()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("商店自动购买设置")

        # 将窗口居中显示，宽度为显示器宽度的30%，高度为显示器高度的50%
        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.5), int(screen_size.height() * 0.5))
        self.move(int(screen_size.width() * 0.25), int(screen_size.height() * 0.25))

        main_widget = QWidget()
        main_layout = QHBoxLayout()

        shop_list_widget = QWidget()
        shop_list_widget.setFixedWidth(int(self.width() * 0.35))
        shop_list_layout = QVBoxLayout()
        shop_list_layout.addWidget(QLabel("商店列表"))
        self.shop_list_tab = shop_list_tab = QTabWidget()
        shop_list_layout.addWidget(shop_list_tab)
        self.normal_shop_list = QListWidget()
        self.normal_shop_list.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection
        )
        self.shop_list_tab.addTab(self.normal_shop_list, "普通商店")
        shop_list_widget.setLayout(shop_list_layout)
        main_layout.addWidget(shop_list_widget)
        self.refresh_shop_list()

        btn_panel_widget = QWidget()
        btn_panel_layout = QVBoxLayout()
        buy_item_btn = QPushButton("全部购买")
        buy_item_btn.clicked.connect(self.buy_item_btn_clicked)
        btn_panel_layout.addWidget(buy_item_btn)
        set_auto_buy_btn = QPushButton("设为自动购买")
        set_auto_buy_btn.clicked.connect(self.set_auto_buy_btn_clicked)
        btn_panel_layout.addWidget(set_auto_buy_btn)

        btn_panel_widget.setLayout(btn_panel_layout)
        main_layout.addWidget(btn_panel_widget)

        auto_buy_list_widget = QWidget()
        auto_buy_list_widget.setFixedWidth(int(self.width() * 0.35))
        auto_buy_list_layout = QVBoxLayout()
        auto_buy_list_layout.addWidget(QLabel("自动购买列表"))
        self.auto_buy_list = QListWidget()
        self.auto_buy_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        auto_buy_list_layout.addWidget(self.auto_buy_list)
        auto_buy_list_widget.setLayout(auto_buy_list_layout)
        main_layout.addWidget(auto_buy_list_widget)
        self.refresh_auto_buy_list()

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def refresh_shop_list(self):
        self.normal_shop_list.clear()
        for shop_item in self.usersettings.shop.normal_shop_goods.values():
            if shop_item.type == "tool":
                tool = self.usersettings.lib.get_tool_by_id(shop_item.p_id)
                item = QListWidgetItem(f"{tool.name}({shop_item.num})")
                item.setData(Qt.ItemDataRole.UserRole, shop_item.id)
                self.normal_shop_list.addItem(item)
            elif shop_item.type == "organisms":
                plant = self.usersettings.lib.get_plant_by_id(shop_item.p_id)
                item = QListWidgetItem(f"{plant.name}({shop_item.num})")
                item.setData(Qt.ItemDataRole.UserRole, shop_item.id)
                self.normal_shop_list.addItem(item)
            else:
                self.usersettings.logger.log(f"未知的商店商品类型:{shop_item.type}")
                logging.info(f"未知的商店商品类型:{shop_item.type}")
                raise NotImplementedError(f"未知的商店商品类型:{shop_item.type}")

    def buy_item_btn_clicked(self):
        selected_items = self.normal_shop_list.selectedItems()
        selected_items_id = [
            item.data(Qt.ItemDataRole.UserRole) for item in selected_items
        ]
        if len(selected_items_id) == 0:
            logging.info("请先选择一个商品")
            self.usersettings.logger.log("请先选择一个商品")
            return
        result = self.usersettings.shop.buy_list(selected_items_id, 1)
        for good_p_id, amount in result:
            self.usersettings.logger.log(
                "购买了{}个{}".format(
                    amount, self.usersettings.lib.get_tool_by_id(good_p_id).name
                ),
                True,
            )
        self.usersettings.logger.log("购买完成", True)
        self.usersettings.shop.refresh_shop()
        self.refresh_shop_list()

    def set_auto_buy_btn_clicked(self):
        selected_items = self.normal_shop_list.selectedItems()
        selected_items_id = [
            item.data(Qt.ItemDataRole.UserRole) for item in selected_items
        ]
        if len(selected_items_id) == 0:
            self.usersettings.logger.log("请先选择一个商品", True)
            return
        for good_id in selected_items_id:
            self.usersettings.shop_auto_buy_list.add(good_id)
        self.refresh_auto_buy_list()

    def refresh_auto_buy_list(self):
        self.auto_buy_list.clear()
        for good_id in self.usersettings.shop_auto_buy_list:
            good = self.usersettings.shop.normal_shop_goods.get(good_id, None)
            if good is None:
                continue
            if good.type == "tool":
                tool = self.usersettings.lib.get_tool_by_id(good.p_id)
                item = QListWidgetItem(f"{tool.name}")
                item.setData(Qt.ItemDataRole.UserRole, good.id)
                self.auto_buy_list.addItem(item)
            elif good.type == "organisms":
                plant = self.usersettings.lib.get_plant_by_id(good.p_id)
                item = QListWidgetItem(f"{plant.name}")
                item.setData(Qt.ItemDataRole.UserRole, good.id)
                self.auto_buy_list.addItem(item)
            else:
                self.usersettings.logger.log(f"未知的商店商品类型:{good.type}")
                logging.info(f"未知的商店商品类型:{good.type}")
                raise NotImplementedError(f"未知的商店商品类型:{good.type}")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            selected_items = self.auto_buy_list.selectedItems()
            selected_items_id = [
                item.data(Qt.ItemDataRole.UserRole) for item in selected_items
            ]
            if len(selected_items_id) == 0:
                self.usersettings.logger.log("请先选择一个商品", True)
                return
            for good_id in selected_items_id:
                self.usersettings.shop_auto_buy_list.remove(good_id)
            self.refresh_auto_buy_list()


class HeritageWindow(QMainWindow):
    def __init__(self, usersettings: UserSettings, parent=None):
        super().__init__(parent=parent)
        self.usersettings = usersettings
        self.heritage_man = self.usersettings.heritage_man
        self.id1, self.id2 = None, None
        self.init_ui()
        self.refresh_plant_list()
        self.restore_data()
        self.refresh_plant_information()

    def init_ui(self):
        self.setWindowTitle("传承面板")

        # 将窗口居中显示，宽度为显示器宽度的60%，高度为显示器高度的50%
        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.7), int(screen_size.height() * 0.5))
        self.move(int(screen_size.width() * 0.15), int(screen_size.height() * 0.25))

        main_widget = QWidget()
        main_layout = QHBoxLayout()

        widget1 = QWidget()
        widget1.setMinimumWidth(int(self.width() * 0.25))
        widget1_layout = QVBoxLayout()
        widget1_layout.addWidget(QLabel("植物一(传出属性的植物)"))
        self.heritage_from_plant_list = QListWidget()
        self.heritage_from_plant_list.setSelectionMode(
            QListWidget.SelectionMode.SingleSelection
        )
        self.heritage_from_plant_list.itemClicked.connect(
            self.heritage_from_plant_list_item_clicked
        )
        widget1_layout.addWidget(self.heritage_from_plant_list)
        widget1.setLayout(widget1_layout)
        main_layout.addWidget(widget1)

        widget2 = QWidget()
        widget2.setMinimumWidth(int(self.width() * 0.25))
        widget2_layout = QVBoxLayout()
        widget2_layout.addWidget(QLabel("植物二(接受属性的植物)"))
        self.heritage_to_plant_list = QListWidget()
        self.heritage_to_plant_list.setSelectionMode(
            QListWidget.SelectionMode.SingleSelection
        )
        self.heritage_to_plant_list.itemClicked.connect(
            self.heritage_to_plant_list_item_clicked
        )
        widget2_layout.addWidget(self.heritage_to_plant_list)
        widget2.setLayout(widget2_layout)
        main_layout.addWidget(widget2)

        widget3 = QWidget()
        widget3.setMinimumWidth(int(self.width() * 0.15))
        widget3_layout = QVBoxLayout()
        widget3_layout.addWidget(QLabel("植物一属性"))
        self.heritage_from_plant_attribute_list = QPlainTextEdit()
        self.heritage_from_plant_attribute_list.setReadOnly(True)
        widget3_layout.addWidget(self.heritage_from_plant_attribute_list)
        widget3.setLayout(widget3_layout)
        main_layout.addWidget(widget3)

        widget4 = QWidget()
        widget4.setMinimumWidth(int(self.width() * 0.15))
        widget4_layout = QVBoxLayout()
        widget4_layout.addWidget(QLabel("植物二属性"))
        self.heritage_to_plant_attribute_list = QPlainTextEdit()
        self.heritage_to_plant_attribute_list.setReadOnly(True)
        widget4_layout.addWidget(self.heritage_to_plant_attribute_list)
        widget4.setLayout(widget4_layout)
        main_layout.addWidget(widget4)

        widget5 = QWidget()
        widget5.setMinimumWidth(int(self.width() * 0.2))
        widget5_layout = QVBoxLayout()
        widget5_layout.addStretch(1)
        self.book_choice = QComboBox()
        self.book_choice.addItems(self.heritage_man.heritage_book_dict.keys())
        self.book_choice.addItem("全属性")
        self.book_choice.setCurrentIndex(0)
        self.book_choice.currentIndexChanged.connect(self.book_choice_changed)
        widget5_layout.addWidget(self.book_choice)
        self.reinforce_number_box = QComboBox()
        self.reinforce_number_box.addItems([str(i) for i in range(1, 11)])
        self.reinforce_number_box.setCurrentIndex(0)
        self.reinforce_number_box.currentIndexChanged.connect(
            self.reinforce_number_box_changed
        )
        widget5_layout.addWidget(self.reinforce_number_box)
        self.heritage_btn = heritage_btn = QPushButton("进行传承")
        heritage_btn.clicked.connect(self.heritage_btn_clicked)
        widget5_layout.addWidget(heritage_btn)
        space_widget = QWidget()
        space_widget.setFixedHeight(10)
        widget5_layout.addWidget(space_widget)
        widget5_layout.addWidget(QLabel("提示，选择全属性\n不用管传承增强的选择"))
        widget5_layout.addStretch(1)
        widget5.setLayout(widget5_layout)
        main_layout.addWidget(widget5)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def format_plant_info(self, plant: Plant):
        return "{}({})[{}]".format(
            plant.name(self.usersettings.lib),
            plant.grade,
            plant.quality_str,
        )

    def refresh_plant_information(self):
        if self.id1 is None:
            self.heritage_from_plant_attribute_list.setPlainText("")
        else:
            plant = self.usersettings.repo.get_plant(self.id1)
            if plant is None:
                self.heritage_from_plant_attribute_list.setPlainText("")
                self.id1 = None
                self.usersettings.logger.log("仓库里没有id为{}的植物，可能已被删除".format(self.id1))
            else:
                message = self.format_plant_info(plant) + "\n"
                for k, v in self.heritage_man.heritage_attribute_dict.items():
                    message += "{}:{}\n".format(k, format_number(getattr(plant, v)))
                self.heritage_from_plant_attribute_list.setPlainText(message)
        if self.id2 is None:
            self.heritage_to_plant_attribute_list.setPlainText("")
        else:
            plant = self.usersettings.repo.get_plant(self.id2)
            if plant is None:
                self.heritage_to_plant_attribute_list.setPlainText("")
                self.id2 = None
                self.usersettings.logger.log("仓库里没有id为{}的植物，可能已被删除".format(self.id2))
            else:
                message = self.format_plant_info(plant) + "\n"
                for k, v in self.heritage_man.heritage_attribute_dict.items():
                    message += "{}:{}\n".format(k, format_number(getattr(plant, v)))
                self.heritage_to_plant_attribute_list.setPlainText(message)

    def heritage_from_plant_list_item_clicked(self, item):
        plant_id = item.data(Qt.ItemDataRole.UserRole)
        self.id1 = plant_id
        self.heritage_man.id1 = self.id1
        self.refresh_plant_information()

    def heritage_to_plant_list_item_clicked(self, item):
        plant_id = item.data(Qt.ItemDataRole.UserRole)
        self.id2 = plant_id
        self.heritage_man.id2 = self.id2
        self.refresh_plant_information()

    def book_choice_changed(self):
        self.heritage_man.book_choice_index = self.book_choice.currentIndex()
        self.refresh_plant_list()

    def reinforce_number_box_changed(self):
        self.heritage_man.reinforce_number_index = (
            self.reinforce_number_box.currentIndex()
        )
        self.refresh_plant_list()

    def heritage_btn_clicked(self):
        if self.id1 is None:
            self.usersettings.logger.log("请先选择植物一")
            return
        if self.id2 is None:
            self.usersettings.logger.log("请先选择植物二")
            return
        if self.id1 == self.id2:
            self.usersettings.logger.log("植物一和植物二不能相同")
            return
        self.heritage_btn.setDisabled(True)
        QApplication.processEvents()
        try:
            book_name = self.book_choice.currentText()
            if book_name == "全属性":
                result = self.heritage_man.exchange_all(self.id1, self.id2)
            else:
                reinforce_number = int(self.reinforce_number_box.currentText())
                book_id = self.heritage_man.heritage_book_dict[book_name]
                result = self.heritage_man.exchange_one(
                    self.id1, self.id2, book_id, reinforce_number
                )
            self.usersettings.logger.log(result["result"])
            self.usersettings.repo.refresh_repository()
            if result["success"]:
                self.id1 = None
                self.heritage_man.id1 = self.id1
            self.refresh_plant_information()
            self.refresh_plant_list()
        except Exception as e:
            self.usersettings.logger.log("传承失败，异常种类：{}".format(type(e).__name__))
            return
        finally:
            self.heritage_btn.setEnabled(True)

    def refresh_plant_list(self):
        self.heritage_from_plant_list.clear()
        self.heritage_to_plant_list.clear()
        current_attribute_name = self.book_choice.currentText()
        if current_attribute_name == "全属性":
            current_attribute_name = "HP"
        current_attribute = self.heritage_man.heritage_attribute_dict[
            current_attribute_name
        ]
        for plant in self.usersettings.repo.plants:
            if plant is None:
                continue
            msg = self.format_plant_info(plant) + "-{}:{}".format(
                current_attribute_name, format_number(getattr(plant, current_attribute))
            )
            item = QListWidgetItem(msg)
            item.setData(Qt.ItemDataRole.UserRole, plant.id)
            self.heritage_from_plant_list.addItem(item)
            item = QListWidgetItem(msg)
            item.setData(Qt.ItemDataRole.UserRole, plant.id)
            self.heritage_to_plant_list.addItem(item)

    def restore_data(self):
        self.id1 = self.heritage_man.id1
        if self.usersettings.repo.get_plant(self.id1) is None:
            self.id1 = self.heritage_man.id1 = None
        self.id2 = self.heritage_man.id2
        if self.usersettings.repo.get_plant(self.id2) is None:
            self.id2 = self.heritage_man.id2 = None
        for i in range(self.heritage_from_plant_list.count()):
            if (
                self.heritage_from_plant_list.item(i).data(Qt.ItemDataRole.UserRole)
                == self.id1
            ):
                self.heritage_from_plant_list.setCurrentRow(i)
                self.heritage_to_plant_list.setCurrentRow(i)
                break
        if self.heritage_man.book_choice_index is not None:
            self.book_choice.setCurrentIndex(self.heritage_man.book_choice_index)
        if self.heritage_man.reinforce_number_index is not None:
            self.reinforce_number_box.setCurrentIndex(
                self.heritage_man.reinforce_number_index
            )


class PlantRelativeWindow(QMainWindow):
    def __init__(self, usersettings: UserSettings, parent=None):
        super().__init__(parent=parent)
        self.usersettings = usersettings
        self.skill_stone_man = SkillStoneMan(
            self.usersettings.cfg, self.usersettings.lib
        )
        self.init_ui()
        self.current_plant_id = None
        self.current_skill_row_index = None
        self.refresh_plant_list()

    def init_ui(self):
        self.setWindowTitle("植物相关面板")

        # 将窗口居中显示，宽度为显示器宽度的60%，高度为显示器高度的50%
        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.7), int(screen_size.height() * 0.5))
        self.move(int(screen_size.width() * 0.15), int(screen_size.height() * 0.25))

        main_widget = QWidget()
        main_layout = QHBoxLayout()

        widget1 = QWidget()
        widget1.setMinimumWidth(int(self.width() * 0.15))
        widget1_layout = QVBoxLayout()
        widget1_layout.addWidget(QLabel("植物列表"))
        self.plant_list = QListWidget()
        self.plant_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.plant_list.itemClicked.connect(self.plant_list_item_clicked)
        widget1_layout.addWidget(self.plant_list)
        widget1.setLayout(widget1_layout)
        main_layout.addWidget(widget1)

        widget2 = QWidget()
        widget2.setMinimumWidth(int(self.width() * 0.15))
        widget2_layout = QVBoxLayout()
        widget2_layout.addWidget(QLabel("植物属性"))
        self.plant_attribute_list = QPlainTextEdit()
        self.plant_attribute_list.setReadOnly(True)
        widget2_layout.addWidget(self.plant_attribute_list)
        widget2.setLayout(widget2_layout)
        main_layout.addWidget(widget2)

        widget3 = QWidget()
        widget3.setMinimumWidth(int(self.width() * 0.10))
        widget3_layout = QVBoxLayout()
        self.refresh_plant_list_btn = QPushButton("刷新")
        self.refresh_plant_list_btn.clicked.connect(self.refresh_plant_list_btn_clicked)
        widget3_layout.addWidget(self.refresh_plant_list_btn)
        self.function_choice_box = QComboBox()
        self.function_choice_box.addItems(["技能升级"])
        self.function_choice_box.setCurrentIndex(0)
        widget3_layout.addWidget(self.function_choice_box)
        widget3.setLayout(widget3_layout)
        main_layout.addWidget(widget3)

        self.function_panel = QWidget()
        self.function_panel.setMinimumWidth(int(self.width() * 0.4))

        skill_panel_layout = QHBoxLayout()
        skill_panel_layout1 = QVBoxLayout()
        skill_panel_layout1.addWidget(QLabel("技能列表"))
        self.skill_list = QListWidget()
        self.skill_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.skill_list.itemClicked.connect(self.skill_list_item_clicked)
        skill_panel_layout1.addWidget(self.skill_list)
        skill_panel_layout.addLayout(skill_panel_layout1)
        skill_panel_layout2 = QVBoxLayout()
        self.skill_upgrade_btn = QPushButton("升级技能")
        self.skill_upgrade_btn.clicked.connect(self.skill_upgrade_btn_clicked)
        skill_panel_layout2.addWidget(self.skill_upgrade_btn)
        skill_panel_layout.addLayout(skill_panel_layout2)

        self.function_panel.setLayout(skill_panel_layout)

        main_layout.addWidget(self.function_panel)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def format_plant_info(self, plant: Plant):
        return "{}({})[{}]".format(
            plant.name(self.usersettings.lib),
            plant.grade,
            plant.quality_str,
        )

    def refresh_plant_list(self):
        self.plant_list.clear()
        for plant in self.usersettings.repo.plants:
            if plant is None:
                continue
            item = QListWidgetItem(self.format_plant_info(plant))
            item.setData(Qt.ItemDataRole.UserRole, plant.id)
            self.plant_list.addItem(item)

    def refresh_plant_attribute_textbox(self):
        if self.current_plant_id is None:
            self.plant_attribute_list.setPlainText("")
            return
        plant = self.usersettings.repo.get_plant(self.current_plant_id)
        if plant is None:
            self.plant_attribute_list.setPlainText("")
            self.current_plant_id = None
            self.usersettings.logger.log(
                "仓库里没有id为{}的植物，可能已被删除".format(self.current_plant_id)
            )
        else:
            message = self.format_plant_info(plant) + "\n"
            for (
                k,
                v,
            ) in self.usersettings.auto_synthesis_man.attribute2plant_attribute.items():
                message += "{}:{}\n".format(k, format_number(getattr(plant, v)))
            self.plant_attribute_list.setPlainText(message)

    def plant_list_item_clicked(self, item):
        plant_id = item.data(Qt.ItemDataRole.UserRole)
        plant = self.usersettings.repo.get_plant(plant_id)
        if plant is None:
            self.usersettings.logger.log("仓库里没有id为{}的植物，可能已被删除".format(plant_id))
            return
        self.current_plant_id = plant_id
        self.refresh_plant_attribute_textbox()
        if self.function_choice_box.currentIndex() == 0:
            self.refresh_skill_list()
            pass

    def refresh_plant_list_btn_clicked(self):
        self.usersettings.repo.refresh_repository()
        self.refresh_plant_list()
        self.refresh_plant_attribute_textbox()

    def refresh_skill_list(self):
        self.skill_list.clear()
        if self.current_plant_id is None:
            return
        plant = self.usersettings.repo.get_plant(self.current_plant_id)
        if plant is None:
            self.usersettings.logger.log(
                "仓库里没有id为{}的植物，可能已被删除".format(self.current_plant_id)
            )
            return
        for skill in plant.skills:
            item = QListWidgetItem(skill["name"] + f"(id:{skill['id']})")
            item.setData(Qt.ItemDataRole.UserRole, skill)
            self.skill_list.addItem(item)
        if plant.special_skill is not None:
            item = QListWidgetItem(plant.special_skill["name"] + f"(id:{skill['id']})")
            item.setData(Qt.ItemDataRole.UserRole, plant.special_skill)
            self.skill_list.addItem(item)

    def skill_list_item_clicked(self, item):
        self.current_skill_row_index = self.skill_list.row(item)

    def skill_upgrade_btn_clicked(self):
        self.skill_upgrade_btn.setDisabled(True)
        QApplication.processEvents()
        try:
            if self.current_plant_id is None:
                self.usersettings.logger.log("请先选择一个植物")
                return
            plant = self.usersettings.repo.get_plant(self.current_plant_id)
            if plant is None:
                self.usersettings.logger.log(
                    "仓库里没有id为{}的植物，可能已被删除".format(self.current_plant_id)
                )
                return
            skill_item = self.skill_list.currentItem()
            if skill_item is None:
                if self.current_skill_row_index is not None:
                    skill_item = self.skill_list.item(self.current_skill_row_index)
            if skill_item is None:
                self.usersettings.logger.log("请先选择一个技能")
                return
            skill = skill_item.data(Qt.ItemDataRole.UserRole)
            pre_skill = deepcopy(skill)
            result = self.skill_stone_man.upgrade_skill(plant.id, skill)
            if not result['success']:
                self.usersettings.logger.log(result['result'])
            else:
                if result["upgrade_success"]:
                    self.usersettings.logger.log("技能升级成功")
                    for s in plant.skills:
                        if (
                            s["id"] == pre_skill["id"]
                            and s["name"] == pre_skill["name"]
                        ):
                            s["id"] = skill["id"]
                            break
                    else:
                        if plant.special_skill is not None:
                            if (
                                plant.special_skill["id"] == pre_skill["id"]
                                and plant.special_skill["name"] == pre_skill["name"]
                            ):
                                plant.special_skill["id"] = skill["id"]
                    self.skill_list.setCurrentRow(self.current_skill_row_index)
                    self.refresh_skill_list()
                else:
                    self.usersettings.logger.log("技能升级失败")
        except Exception as e:
            self.usersettings.logger.log("技能升级异常，异常种类：{}".format(type(e).__name__))
            return
        finally:
            self.skill_upgrade_btn.setEnabled(True)


class ImageWindow(QMainWindow):
    def __init__(self, image, parent=None):
        super().__init__(parent=parent)
        if isinstance(image, str):
            image = QPixmap(image)
        if not isinstance(image, QPixmap):
            raise TypeError("图片类型错误。类型：{}".format(type(image)))
        self.image = image
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("图片")

        # 将窗口居中显示，宽度为显示器宽度的60%，高度为显示器高度的50%
        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.move(int(screen_size.width() * 0.1), int(screen_size.height() * 0.1))

        main_widget = QWidget()
        main_layout = QVBoxLayout()

        main_layout.addWidget(QLabel().setPixmap(self.image))
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)


class RequirePermissionWindow(QMainWindow):
    def __init__(self, msg, finish_queue):
        super().__init__()
        self.msg = msg
        self.finish_queue = finish_queue
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("警告：请确认操作！")

        # 将窗口居中显示，宽度为显示器宽度的35%，高度为显示器高度的25%
        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.35), int(screen_size.height() * 0.25))
        self.move(int(screen_size.width() * 0.325), int(screen_size.height() * 0.375))

        main_widget = QWidget()
        main_layout = QVBoxLayout()

        msg_label = QLabel(self.msg)
        msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(msg_label)

        btn_layout = QHBoxLayout()
        accept_btn = QPushButton("确认")
        accept_btn.clicked.connect(self.accept_btn_clicked)
        btn_layout.addWidget(accept_btn)
        refuse_btn = QPushButton("取消")
        refuse_btn.clicked.connect(self.refuse_btn_clicked)
        btn_layout.addWidget(refuse_btn)
        main_layout.addLayout(btn_layout)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def accept_btn_clicked(self):
        self.finish_queue.put(True)
        self.close()

    def refuse_btn_clicked(self):
        self.finish_queue.put(False)
        self.close()


_permission_window = []


def require_permission(msg):
    global _permission_window
    finish_queue = Queue()
    window = RequirePermissionWindow(msg, finish_queue)
    window.show()
    _permission_window = [w for w in _permission_window if w.isVisible()]
    _permission_window.append(window)
    while True:
        try:
            return finish_queue.get_nowait()
        except Exception:
            QApplication.processEvents()



