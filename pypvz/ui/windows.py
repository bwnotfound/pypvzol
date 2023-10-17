import logging
from copy import deepcopy
from time import sleep
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
    QLineEdit,
)
from PyQt6 import QtGui
from PyQt6.QtCore import Qt, pyqtSignal, QThread

from ..repository import Repository
from ..library import Library
from .wrapped import QLabel
from .user import UserSettings
from ..upgrade import UpgradeMan, HeritageMan, SkillStoneMan
from ..utils.common import format_number
from ..repository import Plant


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


class EvolutionPanelWindow(QMainWindow):
    refresh_signal = pyqtSignal()

    def __init__(self, usersettings: UserSettings, parent=None):
        super().__init__(parent=parent)
        self.usersettings = usersettings
        self.init_ui()
        self.refresh_signal.connect(self.refresh_evolution_path_list)

    def init_ui(self):
        self.setWindowTitle("进化面板")

        # 将窗口居中显示，宽度为显示器宽度的30%，高度为显示器高度的50%
        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.5), int(screen_size.height() * 0.5))
        self.move(int(screen_size.width() * 0.25), int(screen_size.height() * 0.25))

        main_widget = QWidget()
        main_layout = QHBoxLayout()

        plant_list_widget = QWidget()
        plant_list_widget.setFixedWidth(int(self.width() * 0.4))
        plant_list_layout = QVBoxLayout()
        plant_list_layout.addWidget(QLabel("植物列表"))
        self.plant_list = QListWidget()
        self.plant_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        for plant in self.usersettings.repo.plants:
            item = QListWidgetItem(
                f"{plant.name(self.usersettings.lib)}({plant.grade})"
            )
            item.setData(Qt.ItemDataRole.UserRole, plant.id)
            self.plant_list.addItem(item)
        plant_list_layout.addWidget(self.plant_list)
        plant_list_refresh_btn = QPushButton("刷新列表")
        plant_list_refresh_btn.clicked.connect(self.plant_list_refresh_btn_clicked)
        plant_list_layout.addWidget(plant_list_refresh_btn)
        plant_list_widget.setLayout(plant_list_layout)

        main_layout.addWidget(plant_list_widget)

        evolution_path_widget = QWidget()
        evolution_path_layout = QVBoxLayout()
        evolution_path_layout.addWidget(QLabel("进化路径"))
        self.evolution_path_list = QListWidget()
        self.evolution_path_list.setSelectionMode(
            QListWidget.SelectionMode.SingleSelection
        )
        self.refresh_evolution_path_list()
        evolution_path_layout.addWidget(self.evolution_path_list)
        evolution_path_setting_btn = QPushButton("修改进化路径")
        evolution_path_setting_btn.clicked.connect(
            self.evolution_path_setting_btn_clicked
        )
        evolution_path_layout.addWidget(evolution_path_setting_btn)
        evolution_path_add_btn = QPushButton("添加进化路径")
        evolution_path_add_btn.clicked.connect(self.evolution_path_add_btn_clicked)
        evolution_path_layout.addWidget(evolution_path_add_btn)
        evolution_path_remove_btn = QPushButton("删除进化路径")
        evolution_path_remove_btn.clicked.connect(
            self.evolution_path_remove_btn_clicked
        )
        evolution_path_layout.addWidget(evolution_path_remove_btn)

        evolution_path_widget.setLayout(evolution_path_layout)
        main_layout.addWidget(evolution_path_widget)

        evolution_start_btn = QPushButton("开始进化")
        evolution_start_btn.clicked.connect(self.evolution_start_btn_clicked)
        main_layout.addWidget(evolution_start_btn)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    @property
    def current_evolution_path_index(self):
        selected_data = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self.evolution_path_list.selectedItems()
        ]
        if len(selected_data) == 0:
            return None
        return selected_data[0]

    @property
    def selected_plant_id(self):
        selected_data = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self.plant_list.selectedItems()
        ]
        return selected_data

    @property
    def selected_plant_pid(self):
        selected_data = [
            self.usersettings.repo.get_plant(item.data(Qt.ItemDataRole.UserRole)).pid
            for item in self.plant_list.selectedItems()
        ]
        return selected_data

    def refresh_evolution_path_list(self):
        self.evolution_path_list.clear()
        for i, path in enumerate(
            self.usersettings.plant_evolution.saved_evolution_paths
        ):
            item = QListWidgetItem(
                f"{path[0].start_plant.name}({path[0].start_plant.use_condition})->{path[-1].start_plant.name}({path[-1].start_plant.use_condition})|||"
                + "->".join([item.start_plant.name for item in path])
            )
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.evolution_path_list.addItem(item)

    def evolution_start_btn_clicked(self):
        if self.current_evolution_path_index is None:
            self.usersettings.logger.log("请先选择一个进化路线")
            return
        if len(self.selected_plant_id) == 0:
            self.usersettings.logger.log("请先选择一个或多个植物")
            return
        for plant_id in self.selected_plant_id:
            result = self.usersettings.plant_evolution.plant_evolution_all(
                self.current_evolution_path_index, plant_id
            )
            self.usersettings.logger.log(result["result"])
        self.plant_list_refresh_btn_clicked()

    def plant_list_refresh_btn_clicked(self):
        self.plant_list.clear()
        self.usersettings.repo.refresh_repository()
        for plant in self.usersettings.repo.plants:
            item = QListWidgetItem(
                f"{plant.name(self.usersettings.lib)}({plant.grade})"
            )
            item.setData(Qt.ItemDataRole.UserRole, plant.id)
            self.plant_list.addItem(item)

    def evolution_path_setting_btn_clicked(self):
        if self.current_evolution_path_index is None:
            self.usersettings.logger.log("请先选择一个进化路线")
            return
        self.evolution_path_setting = EvolutionPathSetting(
            self.current_evolution_path_index,
            self.usersettings,
            self.refresh_signal,
            self,
        )
        self.evolution_path_setting.show()

    def evolution_path_add_btn_clicked(self):
        if len(self.selected_plant_pid) == 0:
            self.usersettings.logger.log("请先选择一个植物")
            return
        if len(self.selected_plant_pid) > 1:
            self.usersettings.logger.log("只能选择一个植物")
            return
        self.usersettings.plant_evolution.create_new_path(self.selected_plant_pid[0])
        self.refresh_evolution_path_list()

    def evolution_path_remove_btn_clicked(self):
        if self.current_evolution_path_index is None:
            return
        self.usersettings.plant_evolution.remove_path(self.current_evolution_path_index)
        self.refresh_evolution_path_list()


class EvolutionPathSetting(QMainWindow):
    def __init__(
        self,
        evolution_path_index: int,
        usersettings: UserSettings,
        refresh_signal,
        parent=None,
    ):
        super().__init__(parent=parent)
        self.usersettings = usersettings
        self.evolution_path_index = evolution_path_index
        self.init_ui()
        self.refresh_signal = refresh_signal

    def init_ui(self):
        self.setWindowTitle("进化设置面板")

        # 将窗口居中显示，宽度为显示器宽度的30%，高度为显示器高度的50%
        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.5), int(screen_size.height() * 0.5))
        self.move(int(screen_size.width() * 0.25), int(screen_size.height() * 0.25))

        self.main_widget = QWidget()
        self.main_layout = QHBoxLayout()

        self.evolution_panel = QWidget()
        self.evolution_panel_layout = QHBoxLayout()

        self.evolution_chain_panel_widget = QWidget()
        self.evolution_chain_panel_widget.setFixedWidth(int(self.width() * 0.35))
        self.evolution_chain_panel_layout = QVBoxLayout()
        self.evolution_chain_panel_layout.addWidget(QLabel("进化链路"))
        self.evolution_chain = QListWidget()
        self.evolution_chain_panel_layout.addWidget(self.evolution_chain)
        self.evolution_chain_panel_widget.setLayout(self.evolution_chain_panel_layout)
        self.evolution_panel_layout.addWidget(self.evolution_chain_panel_widget)
        self.evolution_choice = QListWidget()
        self.evolution_choice.itemClicked.connect(self.evolution_choice_item_clicked)
        self.evolution_panel_layout.addWidget(self.evolution_choice)
        self.evolution_panel.setLayout(self.evolution_panel_layout)
        self.main_layout.addWidget(self.evolution_panel)

        self.main_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.main_widget)
        self.refresh_evolution_panel()

    def refresh_evolution_panel(self):
        self.evolution_chain.clear()
        self.evolution_choice.clear()
        for i, evolution_path_item in enumerate(
            self.usersettings.plant_evolution.saved_evolution_paths[
                self.evolution_path_index
            ]
        ):
            item = QListWidgetItem(
                f"{evolution_path_item.start_plant.name}({evolution_path_item.start_plant.use_condition})"
            )
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.evolution_chain.addItem(item)
        start_plant = self.usersettings.plant_evolution.saved_evolution_paths[
            self.evolution_path_index
        ][-1].start_plant
        for i, evolution_item in enumerate(start_plant.evolution_path.evolutions):
            target_plant = self.usersettings.lib.get_plant_by_id(
                evolution_item["target_id"]
            )
            item = QListWidgetItem(f"{target_plant.name}({target_plant.use_condition})")
            item.setData(Qt.ItemDataRole.UserRole, i + 1)
            self.evolution_choice.addItem(item)

    def evolution_choice_item_clicked(self, item: QListWidgetItem):
        choice = item.data(Qt.ItemDataRole.UserRole)
        result = self.usersettings.plant_evolution.add_evolution(
            self.evolution_path_index,
            choice,
        )
        logging.info(result["result"])
        self.refresh_evolution_panel()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            selected_evolution_item = self.evolution_chain.currentItem()
            if selected_evolution_item is None:
                return
            selected_evolution_item_index: int = selected_evolution_item.data(
                Qt.ItemDataRole.UserRole
            )
            if selected_evolution_item_index == 0:
                logging.info("不能删除第一个进化元素")
                return
            result = self.usersettings.plant_evolution.remove_evolution(
                self.evolution_path_index,
                self.usersettings.plant_evolution.saved_evolution_paths[
                    self.evolution_path_index
                ][selected_evolution_item_index].start_plant.id,
            )
            logging.info(result["result"])
            self.refresh_evolution_panel()

    def closeEvent(self, event):
        self.refresh_signal.emit()
        return super().closeEvent(event)


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


class UpgradeQualityWindow(QMainWindow):
    def __init__(self, usersettings: UserSettings, parent=None):
        super().__init__(parent=parent)
        self.usersettings = usersettings
        self.upgradeMan = UpgradeMan(self.usersettings.cfg)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("升级品质")

        # 将窗口居中显示，宽度为显示器宽度的30%，高度为显示器高度的50%
        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.5), int(screen_size.height() * 0.5))
        self.move(int(screen_size.width() * 0.25), int(screen_size.height() * 0.25))

        main_widget = QWidget()
        main_layout = QHBoxLayout()

        plant_list_widget = QWidget()
        plant_list_widget.setFixedWidth(int(self.width() * 0.35))
        plant_list_layout = QVBoxLayout()
        plant_list_layout.addWidget(QLabel("植物列表"))
        self.plant_list = QListWidget()
        self.plant_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        plant_list_layout.addWidget(self.plant_list)
        plant_list_widget.setLayout(plant_list_layout)
        main_layout.addWidget(plant_list_widget)
        self.refresh_plant_list()

        self.upgrade_quality_choice = QComboBox()
        for quality_name in self.upgradeMan.quality_name:
            self.upgrade_quality_choice.addItem(quality_name)
        self.upgrade_quality_choice.setCurrentIndex(
            self.upgradeMan.quality_name.index("魔神")
        )
        main_layout.addWidget(self.upgrade_quality_choice)

        self.upgrade_quality_btn = upgrade_quality_btn = QPushButton("升级品质")
        upgrade_quality_btn.clicked.connect(self.upgrade_quality_btn_clicked)
        main_layout.addWidget(upgrade_quality_btn)

        self.show_all_info = QCheckBox("显示所有信息")
        self.show_all_info.setChecked(False)
        main_layout.addWidget(self.show_all_info)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def refresh_plant_list(self):
        self.plant_list.clear()
        for plant in self.usersettings.repo.plants:
            item = QListWidgetItem(
                f"{plant.name(self.usersettings.lib)}({plant.grade})[{plant.quality_str}]"
            )
            item.setData(Qt.ItemDataRole.UserRole, plant.id)
            self.plant_list.addItem(item)

    def upgrade_quality_btn_clicked(self):
        self.upgrade_quality_btn.setDisabled(True)
        QApplication.processEvents()
        try:
            selected_items = self.plant_list.selectedItems()
            if len(selected_items) == 0:
                self.usersettings.logger.log("请先选择一个植物")
                return
            selected_plant_id = [
                item.data(Qt.ItemDataRole.UserRole) for item in selected_items
            ]
            need_show_all_info = self.show_all_info.isChecked()
            target_quality_index = self.upgradeMan.quality_name.index(
                self.upgrade_quality_choice.currentText()
            )
            for plant_id in selected_plant_id:
                plant = self.usersettings.repo.get_plant(plant_id)
                if plant is None:
                    continue
                if plant.quality_index >= target_quality_index:
                    self.usersettings.logger.log(
                        f"{plant.name(self.usersettings.lib)}({plant.grade})品质已大于等于目标品质"
                    )
                    continue

                error_flag = False
                while True:
                    cnt, max_retry = 0, 15
                    while cnt < max_retry:
                        try:
                            result = self.upgradeMan.upgrade_quality(plant_id)
                        except Exception as e:
                            self.usersettings.logger.log(
                                f"刷品异常，已跳过该植物，同时暂停1秒。原因种类：{type(e).__name__}"
                            )
                            error_flag = True
                            sleep(1)
                            break
                        cnt += 1
                        if result['success']:
                            break
                        else:
                            if result['error_type'] == 6:
                                self.usersettings.logger.log(
                                    "请求升品过于频繁，选择等待1秒后重试，最多再重试{}".format(max_retry - cnt)
                                )
                                sleep(1)
                                continue
                            else:
                                self.usersettings.logger.log(result['result'])
                                error_flag = True
                                break
                    else:
                        self.usersettings.logger.log("重试次数过多，放弃升级品质")
                        error_flag = True
                    if error_flag:
                        break
                    cur_quality_index = self.upgradeMan.quality_name.index(
                        result['quality_name']
                    )
                    plant.quality_index = cur_quality_index
                    plant.quality_str = result['quality_name']
                    if cur_quality_index >= target_quality_index:
                        self.usersettings.logger.log(
                            f"{plant.name(self.usersettings.lib)}({plant.grade})升品完成"
                        )
                        break
                    msg = "{}({})升品成功。当前品质：{}".format(
                        plant.name(self.usersettings.lib),
                        plant.grade,
                        result['quality_name'],
                    )
                    logging.info(msg)
                    if need_show_all_info:
                        self.usersettings.logger.log(msg, False)
                self.refresh_plant_list()
                QApplication.processEvents()
            self.usersettings.logger.log(f"刷品结束")
            self.usersettings.repo.refresh_repository()
            self.refresh_plant_list()
        except Exception as e:
            self.usersettings.logger.log(f"刷品过程中出现异常，已停止。原因种类：{type(e).__name__}")
        finally:
            self.upgrade_quality_btn.setEnabled(True)


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


class AutoSynthesisWindow(QMainWindow):
    def __init__(self, usersettings: UserSettings, parent=None):
        super().__init__(parent=parent)
        self.usersettings = usersettings
        self.init_ui()
        self.refresh_all()

    def init_ui(self):
        self.setWindowTitle("自动合成")

        # 将窗口居中显示，宽度为显示器宽度的70%，高度为显示器高度的50%
        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.75), int(screen_size.height() * 0.5))
        self.move(int(screen_size.width() * 0.125), int(screen_size.height() * 0.25))

        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_layout.setSpacing(0)

        widget1 = QWidget()
        widget1.setFixedWidth(int(self.width() * 0.12))
        widget1_layout = QVBoxLayout()
        widget1_layout.addWidget(QLabel("合成书列表"))
        self.tool_list = QListWidget()
        self.tool_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        widget1_layout.addWidget(self.tool_list)
        widget1.setLayout(widget1_layout)
        main_layout.addWidget(widget1)

        widget2 = QWidget()
        widget2.setMinimumWidth(int(self.width() * 0.25))
        widget2_layout = QVBoxLayout()
        widget2_layout.addWidget(QLabel("植物列表"))
        self.plant_list = QListWidget()
        self.plant_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        widget2_layout.addWidget(self.plant_list)
        widget2.setLayout(widget2_layout)
        main_layout.addWidget(widget2)

        widget3 = QWidget()
        widget3.setFixedWidth(int(self.width() * 0.13))
        widget3_layout = QVBoxLayout()
        widget3_layout.addStretch(1)
        widget3_1 = QWidget()
        widget3_1_layout = QVBoxLayout()
        widget3_1_layout.addWidget(QLabel("选择合成属性"))
        self.auto_synthesis_attribute_choice = QComboBox()
        for name in self.usersettings.auto_synthesis_man.attribute_list:
            self.auto_synthesis_attribute_choice.addItem(name)
        self.auto_synthesis_attribute_choice.setCurrentIndex(
            self.usersettings.auto_synthesis_man.attribute_list.index(
                self.usersettings.auto_synthesis_man.chosen_attribute
            )
        )
        self.auto_synthesis_attribute_choice.currentIndexChanged.connect(
            self.auto_synthesis_attribute_choice_changed
        )
        widget3_1_layout.addWidget(self.auto_synthesis_attribute_choice)
        widget3_1.setLayout(widget3_1_layout)
        widget3_layout.addWidget(widget3_1)
        widget3_2 = QWidget()
        widget3_2_layout = QVBoxLayout()
        widget3_2_layout.addWidget(QLabel("选择增强卷轴数量"))
        self.reinforce_number_choice = QComboBox()
        for i in range(0, 11):
            self.reinforce_number_choice.addItem(str(i))
        self.reinforce_number_choice.setCurrentIndex(
            self.usersettings.auto_synthesis_man.reinforce_number
        )
        self.reinforce_number_choice.currentIndexChanged.connect(
            self.reinforce_number_choice_changed
        )
        widget3_2_layout.addWidget(self.reinforce_number_choice)
        widget3_2.setLayout(widget3_2_layout)
        widget3_layout.addWidget(widget3_2)
        plant_import_btn = QPushButton("导入合成池")
        plant_import_btn.clicked.connect(self.plant_import_btn_clicked)
        widget3_layout.addWidget(plant_import_btn)
        main_plant_set_btn = QPushButton("设置主植物(底座)")
        main_plant_set_btn.clicked.connect(self.main_plant_set_btn_clicked)
        widget3_layout.addWidget(main_plant_set_btn)
        main_plant_remove_btn = QPushButton("移除主植物(底座)")
        main_plant_remove_btn.clicked.connect(self.main_plant_remove_btn_clicked)
        widget3_layout.addWidget(main_plant_remove_btn)
        widget3_layout.addStretch(1)
        widget3.setLayout(widget3_layout)
        main_layout.addWidget(widget3)

        widget4 = QWidget()
        widget4.setMinimumWidth(int(self.width() * 0.25))
        widget4_layout = QVBoxLayout()
        widget4_layout.addWidget(QLabel("合成池"))
        self.plant_pool_list = QListWidget()
        self.plant_pool_list.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection
        )
        widget4_layout.addWidget(self.plant_pool_list)
        widget4.setLayout(widget4_layout)
        main_layout.addWidget(widget4)

        widget5 = QWidget()
        widget5.setFixedWidth(int(self.width() * 0.15))
        widget5_layout = QVBoxLayout()
        widget5_layout.addWidget(QLabel("当前主植物(底座)"))
        self.choose_main_plant_text_box = QPlainTextEdit()
        self.choose_main_plant_text_box.setReadOnly(True)
        widget5_layout.addWidget(self.choose_main_plant_text_box)
        widget5.setLayout(widget5_layout)
        main_layout.addWidget(widget5)

        widget6 = QWidget()
        widget6.setFixedWidth(int(self.width() * 0.15))
        widget6_layout = QVBoxLayout()
        widget6_layout.addStretch(1)

        widget6_1_layout = QVBoxLayout()
        widget6_1_layout.addWidget(QLabel("合成数值终点"))
        widget6_1_1_layout = QHBoxLayout()
        self.mantissa_line_edit = QLineEdit()
        self.mantissa_line_edit.setValidator(QtGui.QDoubleValidator())
        self.mantissa_line_edit.setText(
            str(self.usersettings.auto_synthesis_man.end_mantissa)
        )
        self.mantissa_line_edit.textChanged.connect(
            self.mantissa_line_edit_value_changed
        )
        widget6_1_1_layout.addWidget(self.mantissa_line_edit)
        widget6_1_1_layout.addWidget(QLabel("x10的"))
        self.exponent_line_edit = QLineEdit()
        self.exponent_line_edit.setValidator(QtGui.QIntValidator())
        self.exponent_line_edit.setText(
            str(self.usersettings.auto_synthesis_man.end_exponent)
        )
        self.exponent_line_edit.textChanged.connect(
            self.exponent_line_edit_value_changed
        )
        widget6_1_1_layout.addWidget(self.exponent_line_edit)
        widget6_1_1_layout.addWidget(QLabel("次方亿"))
        widget6_1_layout.addLayout(widget6_1_1_layout)
        widget6_layout.addLayout(widget6_1_layout)

        self.auto_synthesis_btn = auto_synthesis_btn = QPushButton("全部合成")
        auto_synthesis_btn.clicked.connect(self.auto_synthesis_btn_clicked)
        widget6_layout.addWidget(auto_synthesis_btn)
        self.auto_synthesis_single_btn = auto_synthesis_single_btn = QPushButton("合成一次")
        auto_synthesis_single_btn.clicked.connect(
            self.auto_synthesis_single_btn_clicked
        )
        widget6_layout.addWidget(auto_synthesis_single_btn)

        widget6_layout.addStretch(1)

        widget6.setLayout(widget6_layout)
        main_layout.addWidget(widget6)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def mantissa_line_edit_value_changed(self):
        try:
            float(self.mantissa_line_edit.text())
        except ValueError:
            self.mantissa_line_edit.setText("1.0")
        mantissa = float(self.mantissa_line_edit.text())
        self.usersettings.auto_synthesis_man.end_mantissa = mantissa

    def exponent_line_edit_value_changed(self):
        try:
            int(self.exponent_line_edit.text())
        except ValueError:
            self.exponent_line_edit.setText("0")
        exponent = int(self.exponent_line_edit.text())
        self.usersettings.auto_synthesis_man.end_exponent = exponent

    def format_plant_info(self, plant):
        if isinstance(plant, str):
            plant = int(plant)
        if isinstance(plant, int):
            plant = self.usersettings.repo.get_plant(plant)
        assert isinstance(plant, Plant), type(plant).__name__
        return "{}({})[{}]-{}:{}".format(
            plant.name(self.usersettings.lib),
            plant.grade,
            plant.quality_str,
            self.usersettings.auto_synthesis_man.chosen_attribute.replace("特", ""),
            format_number(
                getattr(
                    plant,
                    self.usersettings.auto_synthesis_man.attribute2plant_attribute[
                        self.usersettings.auto_synthesis_man.chosen_attribute
                    ],
                )
            ),
        )

    def get_end_value(self):
        mantissa = float(self.mantissa_line_edit.text())
        exponent = int(self.exponent_line_edit.text())
        return mantissa * (10 ** (exponent + 8))

    def get_main_plant_attribute(self):
        if self.usersettings.auto_synthesis_man.main_plant_id is None:
            return None
        plant = self.usersettings.repo.get_plant(
            self.usersettings.auto_synthesis_man.main_plant_id
        )
        if plant is None:
            return None
        return getattr(
            plant,
            self.usersettings.auto_synthesis_man.attribute2plant_attribute[
                self.usersettings.auto_synthesis_man.chosen_attribute
            ],
        )

    def refresh_tool_list(self):
        self.tool_list.clear()
        for (
            item_id
        ) in self.usersettings.auto_synthesis_man.attribute_book_dict.values():
            tool_item = self.usersettings.repo.get_tool(item_id)
            if tool_item is None:
                continue
            item = QListWidgetItem(
                "{}({})".format(
                    self.usersettings.lib.get_tool_by_id(item_id).name,
                    tool_item['amount'],
                )
            )
            self.tool_list.addItem(item)

    def refresh_plant_list(self):
        self.plant_list.clear()
        for plant in self.usersettings.repo.plants:
            if (
                plant.id in self.usersettings.auto_synthesis_man.auto_synthesis_pool_id
                or plant.id == self.usersettings.auto_synthesis_man.main_plant_id
            ):
                continue
            item = QListWidgetItem(self.format_plant_info(plant))
            item.setData(Qt.ItemDataRole.UserRole, plant.id)
            self.plant_list.addItem(item)

    def refresh_plant_pool_list(self):
        self.plant_pool_list.clear()
        for plant_id in self.usersettings.auto_synthesis_man.auto_synthesis_pool_id:
            plant = self.usersettings.repo.get_plant(plant_id)
            item = QListWidgetItem(self.format_plant_info(plant))
            item.setData(Qt.ItemDataRole.UserRole, plant_id)
            self.plant_pool_list.addItem(item)

    def refresh_main_plant_text_box(self):
        self.choose_main_plant_text_box.setPlainText(
            self.format_plant_info(self.usersettings.auto_synthesis_man.main_plant_id)
            if (self.usersettings.auto_synthesis_man.main_plant_id is not None)
            else ""
        )

    def auto_synthesis_attribute_choice_changed(self):
        self.usersettings.auto_synthesis_man.chosen_attribute = (
            self.auto_synthesis_attribute_choice.currentText()
        )
        self.refresh_plant_list()
        self.refresh_plant_pool_list()
        self.refresh_main_plant_text_box()

    def reinforce_number_choice_changed(self):
        self.usersettings.auto_synthesis_man.reinforce_number = int(
            self.reinforce_number_choice.currentText()
        )

    def refresh_all(self):
        self.refresh_tool_list()
        self.refresh_plant_list()
        self.refresh_plant_pool_list()
        self.refresh_main_plant_text_box()

    def plant_import_btn_clicked(self):
        selected_plant_id = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self.plant_list.selectedItems()
        ]
        if len(selected_plant_id) == 0:
            self.usersettings.logger.log("请先选择一个植物再导入合成池")
            return
        for plant_id in selected_plant_id:
            self.usersettings.auto_synthesis_man.auto_synthesis_pool_id.add(plant_id)
        self.usersettings.auto_synthesis_man.check_data()
        self.refresh_plant_list()
        self.refresh_plant_pool_list()

    def main_plant_set_btn_clicked(self):
        selected_plant_id = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self.plant_list.selectedItems()
        ]
        if len(selected_plant_id) == 0:
            self.usersettings.logger.log("请先选择一个植物再设置主植物(底座)")
            return
        if len(selected_plant_id) > 1:
            self.usersettings.logger.log("一次只能设置一个主植物(底座)")
            return
        plant_id = selected_plant_id[0]
        self.usersettings.auto_synthesis_man.main_plant_id = plant_id
        self.refresh_main_plant_text_box()
        self.refresh_plant_list()

    def main_plant_remove_btn_clicked(self):
        self.usersettings.auto_synthesis_man.main_plant_id = None
        self.refresh_main_plant_text_box()
        self.refresh_plant_list()

    def need_synthesis(self):
        target_value = self.get_end_value()
        current_value = self.get_main_plant_attribute()
        if current_value is None:
            self.usersettings.logger.log("未设置底座")
            return False
        if current_value >= target_value:
            self.usersettings.logger.log("底座已达到目标值")
            return False
        return True

    def auto_synthesis_single_btn_clicked(self):
        self.auto_synthesis_single_btn.setDisabled(True)
        QApplication.processEvents()
        try:
            if not self.need_synthesis():
                return
            result = self.usersettings.auto_synthesis_man.synthesis()
            self.usersettings.logger.log(result['result'])
            self.usersettings.auto_synthesis_man.check_data()
            self.refresh_all()
        except Exception as e:
            self.usersettings.logger.log("合成异常。异常种类：{}".format(type(e).__name__))
        finally:
            self.auto_synthesis_single_btn.setEnabled(True)

    def auto_synthesis_btn_clicked(self):
        self.auto_synthesis_btn.setDisabled(True)
        QApplication.processEvents()
        try:
            length = len(self.usersettings.auto_synthesis_man.auto_synthesis_pool_id)
            if length == 0:
                self.usersettings.logger.log("合成池为空")
                return
            self.usersettings.auto_synthesis_man.check_data()
            while (
                not (
                    len(self.usersettings.auto_synthesis_man.auto_synthesis_pool_id)
                    == 0
                )
                and length > 0
            ):
                if not self.need_synthesis():
                    return
                result = self.usersettings.auto_synthesis_man.synthesis(
                    need_check=False
                )
                self.usersettings.logger.log(result['result'])
                self.usersettings.auto_synthesis_man.check_data()
                self.refresh_all()
                QApplication.processEvents()
                if not result["success"]:
                    self.usersettings.logger.log("合成异常，已跳出合成")
                    return
                length -= 1
            self.usersettings.logger.log("合成完成")
        except Exception as e:
            self.usersettings.logger.log("合成异常。异常种类：{}".format(type(e).__name__))
        finally:
            self.auto_synthesis_btn.setEnabled(True)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            selected_items = self.plant_pool_list.selectedItems()
            selected_items_id = [
                item.data(Qt.ItemDataRole.UserRole) for item in selected_items
            ]
            if len(selected_items_id) == 0:
                self.usersettings.logger.log("请先在合成池选择一个植物再删除")
                return
            for plant_id in selected_items_id:
                try:
                    self.usersettings.auto_synthesis_man.auto_synthesis_pool_id.remove(
                        plant_id
                    )
                except KeyError:
                    plant = self.usersettings.repo.get_plant(plant_id)
                    if plant is None:
                        self.usersettings.logger.log(
                            "仓库里没有id为{}的植物，可能已被删除".format(plant_id)
                        )
                    self.usersettings.logger.log(
                        "合成池里没有植物{}".format(self.format_plant_info(plant))
                    )
            self.refresh_plant_list()
            self.refresh_plant_pool_list()


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
                        if s["id"] == pre_skill["id"] and s["name"] == pre_skill["name"]:
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