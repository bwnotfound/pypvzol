import logging
import concurrent.futures
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
)
from PyQt6 import QtGui
from PyQt6.QtCore import Qt, pyqtSignal, QThread

from ..repository import Repository
from ..library import Library
from .wrapped import QLabel
from .user import UserSettings
from ..upgrade import UpgradeMan
from .message import Logger


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
        item = self.evolution_path_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    @property
    def current_plant_id(self):
        item = self.plant_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    @property
    def current_plant_pid(self):
        item = self.plant_list.currentItem()
        if item is None:
            return None
        id = item.data(Qt.ItemDataRole.UserRole)
        return self.usersettings.repo.get_plant(id).pid

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
        if self.current_evolution_path_index is None or self.current_plant_id is None:
            return
        result = self.usersettings.plant_evolution.plant_evolution_all(
            self.current_evolution_path_index, self.current_plant_id
        )
        self.usersettings.logger.log(result["result"])
        logging.info(result["result"])

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
            logging.info("请先选择一个进化路线")
            return
        self.evolution_path_setting = EvolutionPathSetting(
            self.current_evolution_path_index,
            self.usersettings,
            self.refresh_signal,
            self,
        )
        self.evolution_path_setting.show()

    def evolution_path_add_btn_clicked(self):
        if self.current_plant_pid is None:
            return
        self.usersettings.plant_evolution.create_new_path(self.current_plant_pid)
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
        item_list_layout.addWidget(item_list_tab)

        item_list_widget.setLayout(item_list_layout)
        main_layout.addWidget(item_list_widget)
        self.refresh_item_list()

        use_item_panel_widget = QWidget()
        use_item_panel_layout = QVBoxLayout()
        use_item_panel_layout.addStretch(1)

        self.use_item_all_btn = use_item_all_btn = QPushButton("全部使用")
        use_item_all_btn.clicked.connect(self.use_item_all_btn_clicked)
        use_item_panel_layout.addWidget(use_item_all_btn)

        self.auto_use_item_btn = auto_use_item_btn = QPushButton("设为自动使用")
        auto_use_item_btn.clicked.connect(self.auto_use_item_btn_clicked)
        use_item_panel_layout.addWidget(auto_use_item_btn)

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
        self.refresh_auto_use_item_list()
        auto_use_item_list_layout.addWidget(self.auto_use_item_list)
        auto_use_item_list_widget.setLayout(auto_use_item_list_layout)
        main_layout.addWidget(auto_use_item_list_widget)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def refresh_item_list(self):
        self.item_list.clear()
        for tool in self.usersettings.repo.tools:
            lib_tool = self.usersettings.lib.get_tool_by_id(tool['id'])
            item = QListWidgetItem(f"{lib_tool.name}({tool['amount']})")
            item.setData(Qt.ItemDataRole.UserRole, tool['id'])
            self.item_list.addItem(item)
            if lib_tool.type == 3:
                item = QListWidgetItem(f"{lib_tool.name}({tool['amount']})")
                item.setData(Qt.ItemDataRole.UserRole, tool['id'])
                self.box_list.addItem(item)

    def refresh_auto_use_item_list(self):
        self.auto_use_item_list.clear()
        for tool_id in self.usersettings.auto_use_item_list:
            lib_tool = self.usersettings.lib.get_tool_by_id(tool_id)
            item = QListWidgetItem(f"{lib_tool.name}")
            item.setData(Qt.ItemDataRole.UserRole, tool_id)
            self.auto_use_item_list.addItem(item)

    def use_item_all_btn_clicked(self):
        cur_index = self.item_list_tab.currentIndex()
        if cur_index == 0:
            selected_items = self.item_list.selectedItems()
        elif cur_index == 1:
            selected_items = self.box_list.selectedItems()
        else:
            raise NotImplementedError
        for item in selected_items:
            tool_id = item.data(Qt.ItemDataRole.UserRole)
            repo_tool = self.usersettings.repo.get_tool(tool_id)
            if repo_tool is None:
                continue
            tool_type = self.usersettings.lib.get_tool_by_id(tool_id).type
            amount = repo_tool['amount']
            if tool_type == 3:
                while amount > 10:
                    result = self.usersettings.repo.open_box(
                        tool_id, 10, self.usersettings.lib
                    )
                    self.usersettings.logger.log(result['result'])
                    amount -= 10
                result = self.usersettings.repo.open_box(
                    tool_id, amount, self.usersettings.lib
                )
            else:
                result = self.usersettings.repo.use_item(
                    tool_id, amount, self.usersettings.lib
                )
            self.usersettings.logger.log(result['result'])
            for i in range(len(self.usersettings.repo.tools)):
                if self.usersettings.repo.tools[i]['id'] == tool_id:
                    break
            else:
                raise RuntimeError("tool not found")
            self.usersettings.repo.tools.pop(i)
        self.usersettings.repo.refresh_repository()
        self.refresh_item_list()

    def auto_use_item_btn_clicked(self):
        cur_index = self.item_list_tab.currentIndex()
        if cur_index == 0:
            self.usersettings.logger.log("现在只支持自动打开宝箱")
            return
        elif cur_index == 1:
            selected_items = self.box_list.selectedItems()
        else:
            raise NotImplementedError
        for item in selected_items:
            self.usersettings.auto_use_item_list.append(
                item.data(Qt.ItemDataRole.UserRole)
            )
        self.refresh_auto_use_item_list()

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
    upgrade_finished_signal = pyqtSignal(int)
    def __init__(self, usersettings: UserSettings, parent=None):
        super().__init__(parent=parent)
        self.usersettings = usersettings
        self.upgradeMan = UpgradeMan(self.usersettings.cfg)
        self.init_ui()
        self.upgrade_thread = None
        self.upgrade_finished_signal.connect(self.upgrade_finished)

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
            len(self.upgradeMan.quality_name) - 1
        )
        main_layout.addWidget(self.upgrade_quality_choice)

        upgrade_quality_btn = QPushButton("升级品质")
        upgrade_quality_btn.clicked.connect(self.upgrade_quality_btn_clicked)
        main_layout.addWidget(upgrade_quality_btn)

        self.show_all_info = QCheckBox("显示所有信息")
        self.show_all_info.setChecked(True)
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
        if self.upgrade_thread is not None:
            self.usersettings.logger.log("正在升级品质，请稍后再试")
        selected_items = self.plant_list.selectedItems()
        if len(selected_items) == 0:
            logging.info("请先选择一个植物")
            self.usersettings.logger.log("请先选择一个植物")
            return
        selected_plant_id = [
            item.data(Qt.ItemDataRole.UserRole) for item in selected_items
        ]
        need_show_all_info = self.show_all_info.isChecked()
        args = []
        for plant_id in selected_plant_id:
            args.append(
                (
                    plant_id,
                    self.upgradeMan.quality_name.index(
                        self.upgrade_quality_choice.currentText()
                    ),
                    need_show_all_info,
                    self.upgradeMan,
                    self.usersettings.logger,
                )
            )
        self.upgrade_thread = UpgradeQualityThread(
            args, self.upgrade_finished_signal, self
        )
        self.upgrade_thread.start()
        
    def upgrade_finished(self, length):
        self.usersettings.logger.log(f"升级品质完成，共升级{length}个植物")
        self.upgrade_thread = None
        
def _upgrade_quality(args):
    plant_id, target_index, show_all_info, upgradeMan, logger = args
    while True:
        result = upgradeMan.upgrade_quality(plant_id)
        logging.info(result['result'])
        if show_all_info:
            logger.log(result['result'], False)
        if result['success']:
            cur_quality_index = upgradeMan.quality_name.index(
                result['quality_name']
            )
            if cur_quality_index >= target_index:
                logger.log(result['result'])
                break

class UpgradeQualityThread(QThread):
    def __init__(self, arg_list, finish_signal, parent=None):
        super().__init__(parent=parent)
        self.arg_list = arg_list
        self.finish_signal = finish_signal
        
    def run(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            result = executor.map(_upgrade_quality, self.arg_list)
        length = len(list(result))
        self.finish_signal.emit(length)
        
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
