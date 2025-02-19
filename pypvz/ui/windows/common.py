from queue import Queue

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QComboBox,
    QCheckBox,
    QApplication,
)
from PyQt6.QtGui import QPixmap
from PyQt6 import QtGui
from PyQt6.QtCore import Qt, pyqtSignal

from ...repository import Repository
from ...library import Library
from ..wrapped import QLabel
from ..user import UserSettings
from ...utils.common import format_number, format_plant_info
from ...repository import Plant
from ..message import Logger
from ..user.auto_challenge import Challenge4Level
from ...utils.common import signal_block_emit

from ... import Config, Library, User


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
            item = QListWidgetItem(format_plant_info(plant, self.lib))
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

    def __init__(
        self,
        cfg: Config,
        user: User,
        logger: Logger,
        challenge4Level: Challenge4Level,
        parent=None,
    ):
        super().__init__(parent=parent)
        self.cfg = cfg
        self.user = user
        self.logger = logger
        self.challenge4Level = challenge4Level
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
        if self.cfg.server == "私服":
            result = self.challenge4Level.caveMan.switch_garden_layer(1, self.logger)
            widget3_2_layout = QHBoxLayout()
            widget3_2_layout.addWidget(QLabel("选择花园层级:"))
            self.logger.log(result["result"])
            if not result["success"]:
                self.close()
            self.current_garden_layer_choice = QComboBox()
            self.current_garden_layer_choice.addItems(["1", "2", "3", "4", "5", "6", "7"])
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
                    self.logger.log("洞口{}异常".format(cave.format_name()))
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
        self.challenge4Level.caveMan.switch_garden_layer(index + 1, self.logger)
        self.refresh_cave_list()

    def get_caves(self, cave_type, cave_layer):
        if not hasattr(self, "_caves"):
            self._caves = {}
        format_name = "{}-{}".format(cave_type, cave_layer)
        if self.cfg.server == "私服" and cave_type <= 3:
            format_name += "-{}".format(self.current_garden_layer_choice.currentIndex())
        result = self._caves.get(format_name)
        if result is None:
            if cave_type <= 3:
                caves = self.challenge4Level.caveMan.get_caves(
                    self.user.id,
                    cave_type,
                    cave_layer,
                    logger=self.logger,
                )
            elif cave_type == 4:
                caves = self.challenge4Level.caveMan.get_caves(
                    cave_layer, cave_type, logger=self.logger
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
        difficulty = self.difficulty_choice.currentIndex() + 1
        if self.cfg.server == "私服":
            if cave.type == 4:
                difficulty = 1
            self.challenge4Level.add_cave(
                cave,
                difficulty=difficulty,
                garden_layer=self.current_garden_layer_choice.currentIndex() + 1,
                use_sand=self.need_use_sand.isChecked(),
            )
        else:
            self.challenge4Level.add_cave(cave, difficulty=difficulty)
        self.cave_add_update.emit()


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
                self.usersettings.logger.log(
                    "仓库里没有id为{}的植物，可能已被删除".format(self.id1)
                )
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
                self.usersettings.logger.log(
                    "仓库里没有id为{}的植物，可能已被删除".format(self.id2)
                )
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
            if not result["success"]:
                self.usersettings.logger.log(result["result"])
        except Exception as e:
            self.usersettings.logger.log(
                "传承失败，异常种类：{}".format(type(e).__name__)
            )
            return
        finally:
            self.usersettings.repo.refresh_repository()
            self.refresh_plant_information()
            self.refresh_plant_list()
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
    def __init__(self, msg, finish_queue, yes_msg="确认", no_msg="取消"):
        super().__init__()
        self.msg = msg
        self.finish_queue = finish_queue
        self.yes_msg = yes_msg
        self.no_msg = no_msg
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("警告：请确认操作！")

        # 将窗口居中显示，宽度为显示器宽度的35%，高度为显示器高度的25%
        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.35), int(screen_size.height() * 0.35))
        self.move(int(screen_size.width() * 0.325), int(screen_size.height() * 0.325))

        main_widget = QWidget()
        main_layout = QVBoxLayout()

        msg_label = QLabel(self.msg)
        # 令msg_label文字可以复制
        msg_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(msg_label)

        btn_layout = QHBoxLayout()
        accept_btn = QPushButton(self.yes_msg)
        accept_btn.clicked.connect(self.accept_btn_clicked)
        btn_layout.addWidget(accept_btn)
        refuse_btn = QPushButton(self.no_msg)
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

    def closeEvent(self, event):
        self.finish_queue.put(False)
        self.close()
        return super().closeEvent(event)


_permission_window = []


def require_permission(msg, yes_msg="确认", no_msg="取消"):
    global _permission_window
    finish_queue = Queue()
    window = RequirePermissionWindow(msg, finish_queue, yes_msg=yes_msg, no_msg=no_msg)
    window.show()
    _permission_window = [w for w in _permission_window if w.isVisible()]
    _permission_window.append(window)
    while True:
        try:
            return finish_queue.get_nowait()
        except Exception:
            QApplication.processEvents()


def delete_layout_children(layout):
    for i in reversed(range(layout.count())):
        item = layout.itemAt(i)
        layout.removeItem(item)
        if item.widget():
            item.widget().deleteLater()
