from queue import Queue
from copy import deepcopy
import concurrent.futures
from threading import Thread, Event
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
    QTabWidget,
)
from PyQt6.QtGui import QPixmap
from PyQt6 import QtGui
from PyQt6.QtCore import Qt, pyqtSignal

from ...repository import Repository
from ...library import Library, attribute2plant_attribute, talent_name_list
from ..wrapped import QLabel, WaitEventThread
from ..user import UserSettings
from ...utils.common import format_number, format_plant_info
from ...repository import Plant
from ..message import Logger
from ..user.auto_challenge import Challenge4Level

from ... import Config, Library, User


class PlantRelativeWindow(QMainWindow):
    def __init__(self, usersettings: UserSettings, parent=None):
        super().__init__(parent=parent)
        self.usersettings = usersettings
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("植物相关面板")

        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.7), int(screen_size.height() * 0.7))
        self.move(int(screen_size.width() * 0.15), int(screen_size.height() * 0.15))

        tab_widget = QTabWidget()
        tab_widget.setCurrentIndex(0)
        tab_widget.addTab(UpgradeSkillWidget(self.usersettings, self), "升级技能")
        tab_widget.addTab(UpgradeStoneWidget(self.usersettings, self), "升级宝石")

        self.setCentralWidget(tab_widget)


class UpgradeSkillWidget(QWidget):
    upgrade_finish_signal = pyqtSignal()
    upgrade_stopped_signal = pyqtSignal()

    def __init__(self, usersettings: UserSettings, parent):
        super().__init__(parent=parent)
        self.parent_widget = parent
        self.usersettings = usersettings
        self.interrupt_event = Event()
        self.rest_event = Event()
        self.rest_event.set()
        self.run_thread = None
        self.upgrade_finish_signal.connect(self.upgrade_finish)
        self.upgrade_stopped_signal.connect(self.upgrade_stopped)
        self.init_ui()
        self.refresh_plant_list()

    def init_ui(self):
        main_layout = QHBoxLayout()

        widget1 = QWidget()
        widget1.setFixedWidth(int(self.parent_widget.width() * 0.30))
        widget1_layout = QVBoxLayout()
        widget1_layout.addWidget(QLabel("植物列表"))
        self.plant_list = QListWidget()
        self.plant_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.plant_list.itemPressed.connect(self.plant_list_item_clicked)
        widget1_layout.addWidget(self.plant_list)
        widget1.setLayout(widget1_layout)
        main_layout.addWidget(widget1)

        widget2 = QWidget()
        widget2.setFixedWidth(int(self.parent_widget.width() * 0.50))
        widget2_layout = QVBoxLayout()
        widget2_layout.addWidget(QLabel("植物属性"))
        self.plant_attribute_list = QPlainTextEdit()
        self.plant_attribute_list.setReadOnly(True)
        widget2_layout.addWidget(self.plant_attribute_list)
        widget2.setLayout(widget2_layout)
        main_layout.addWidget(widget2)

        widget3 = QWidget()
        widget3.setMinimumWidth(int(self.parent_widget.width() * 0.20))
        widget3_layout = QVBoxLayout()
        widget3.setLayout(widget3_layout)
        main_layout.addWidget(widget3)
        self.refresh_plant_list_btn = QPushButton("刷新")
        self.refresh_plant_list_btn.clicked.connect(self.refresh_plant_list_btn_clicked)
        widget3_layout.addWidget(self.refresh_plant_list_btn)

        self.pool_size_combobox = QComboBox()
        self.pool_size_combobox.addItems([str(i) for i in range(1, 21)])
        self.pool_size_combobox.setCurrentIndex(
            self.usersettings.skill_stone_man.pool_size - 1
        )
        self.pool_size_combobox.currentIndexChanged.connect(
            self.pool_size_combobox_current_index_changed
        )
        widget3_layout.addWidget(self.pool_size_combobox)

        skill_panel_layout2 = QVBoxLayout()
        self.skill_upgrade_btn = QPushButton("全部升技能")
        self.skill_upgrade_btn.clicked.connect(self.skill_upgrade_btn_clicked)
        skill_panel_layout2.addWidget(self.skill_upgrade_btn)
        widget3_layout.addLayout(skill_panel_layout2)

        self.setLayout(main_layout)

    def pool_size_combobox_current_index_changed(self):
        self.usersettings.skill_stone_man.pool_size = (
            self.pool_size_combobox.currentIndex() + 1
        )

    def refresh_plant_list(self):
        self.plant_list.clear()
        for plant in self.usersettings.repo.plants:
            if plant is None:
                continue
            item = QListWidgetItem(format_plant_info(plant, self.usersettings.lib))
            item.setData(Qt.ItemDataRole.UserRole, plant.id)
            self.plant_list.addItem(item)

    def refresh_plant_attribute_textbox(self, plant: Plant = None):
        message = format_plant_info(
            plant,
            self.usersettings.lib,
            normal_skill=True,
            spec_skill=True,
            show_normal_attribute=True,
            need_tab=True,
        )
        self.plant_attribute_list.setPlainText(message)

    def plant_list_item_clicked(self, item):
        plant_id = item.data(Qt.ItemDataRole.UserRole)
        plant = self.usersettings.repo.get_plant(plant_id)
        if plant is None:
            self.usersettings.logger.log("仓库里没有id为{}的植物，可能已被删除".format(plant_id))
            return
        self.refresh_plant_attribute_textbox(plant)

    def refresh_plant_list_btn_clicked(self):
        self.usersettings.repo.refresh_repository()
        self.refresh_plant_list()
        self.refresh_plant_attribute_textbox()

    def upgrade_finish(self):
        self.refresh_plant_attribute_textbox()
        self.usersettings.repo.refresh_repository()
        self.skill_upgrade_btn.setText("全部升技能")
        self.run_thread = None
        self.interrupt_event.clear()

    def upgrade_stopped(self):
        self.skill_upgrade_btn.setText("全部升技能")
        self.skill_upgrade_btn.setEnabled(True)

    def skill_upgrade_btn_clicked(self):
        self.skill_upgrade_btn.setDisabled(True)
        QApplication.processEvents()
        if self.skill_upgrade_btn.text() == "全部升技能":
            try:
                selected_plant_id_list = [
                    item.data(Qt.ItemDataRole.UserRole)
                    for item in self.plant_list.selectedItems()
                ]

                if len(selected_plant_id_list) == 0:
                    self.usersettings.logger.log("请先选择一个植物")
                    return
                plant_list = [
                    self.usersettings.repo.get_plant(plant_id)
                    for plant_id in selected_plant_id_list
                ]
                plant_list = [plant for plant in plant_list if plant is not None]
                if len(plant_list) == 0:
                    self.usersettings.logger.log("选中的植物不存在")
                    return
                self.skill_upgrade_btn.setText("中止")
                self.run_thread = UpgradeSkillThread(
                    plant_list,
                    self.usersettings,
                    self.interrupt_event,
                    self.upgrade_finish_signal,
                    self.rest_event,
                )
                self.rest_event.clear()
                self.run_thread.start()
            finally:
                self.skill_upgrade_btn.setEnabled(True)
        elif self.skill_upgrade_btn.text() == "中止":
            self.interrupt_event.set()
            WaitEventThread(self.rest_event, self.upgrade_stopped_signal).start()
        else:
            self.skill_upgrade_btn.setEnabled(True)
            raise RuntimeError(f"未知按钮文本：{self.skill_upgrade_btn.text()}")


class UpgradeStoneWidget(QWidget):
    upgrade_finish_signal = pyqtSignal()
    upgrade_stopped_signal = pyqtSignal()

    def __init__(self, usersettings: UserSettings, parent):
        super().__init__(parent=parent)
        self.parent_widget = parent
        self.usersettings = usersettings
        self.interrupt_event = Event()
        self.rest_event = Event()
        self.rest_event.set()
        self.run_thread = None
        self.upgrade_finish_signal.connect(self.upgrade_finish)
        self.upgrade_stopped_signal.connect(self.upgrade_stopped)
        self.init_ui()
        self.refresh_plant_list()

    def init_ui(self):
        main_layout = QHBoxLayout()

        widget1 = QWidget()
        widget1.setFixedWidth(int(self.parent_widget.width() * 0.30))
        widget1_layout = QVBoxLayout()
        widget1_layout.addWidget(QLabel("植物列表"))
        self.plant_list = QListWidget()
        self.plant_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.plant_list.itemPressed.connect(self.plant_list_item_clicked)
        widget1_layout.addWidget(self.plant_list)
        widget1.setLayout(widget1_layout)
        main_layout.addWidget(widget1)

        widget2 = QWidget()
        widget2.setFixedWidth(int(self.parent_widget.width() * 0.50))
        widget2_layout = QVBoxLayout()
        widget2_layout.addWidget(QLabel("植物属性"))
        self.plant_attribute_list = QPlainTextEdit()
        self.plant_attribute_list.setReadOnly(True)
        widget2_layout.addWidget(self.plant_attribute_list)
        widget2.setLayout(widget2_layout)
        main_layout.addWidget(widget2)

        widget3 = QWidget()
        widget3.setMinimumWidth(int(self.parent_widget.width() * 0.20))
        widget3_layout = QVBoxLayout()
        widget3.setLayout(widget3_layout)
        main_layout.addWidget(widget3)
        self.refresh_plant_list_btn = QPushButton("刷新")
        self.refresh_plant_list_btn.clicked.connect(self.refresh_plant_list_btn_clicked)
        widget3_layout.addWidget(self.refresh_plant_list_btn)

        self.pool_size_combobox = QComboBox()
        self.pool_size_combobox.addItems([str(i) for i in range(1, 21)])
        self.pool_size_combobox.setCurrentIndex(
            self.usersettings.skill_stone_man.pool_size - 1
        )
        self.pool_size_combobox.currentIndexChanged.connect(
            self.pool_size_combobox_current_index_changed
        )
        widget3_layout.addWidget(self.pool_size_combobox)

        skill_panel_layout2 = QVBoxLayout()
        self.stone_upgrade_btn = QPushButton("全部升宝石")
        self.stone_upgrade_btn.clicked.connect(self.skill_upgrade_btn_clicked)
        skill_panel_layout2.addWidget(self.stone_upgrade_btn)
        widget3_layout.addLayout(skill_panel_layout2)

        self.setLayout(main_layout)

    def pool_size_combobox_current_index_changed(self):
        self.usersettings.skill_stone_man.pool_size = (
            self.pool_size_combobox.currentIndex() + 1
        )

    def refresh_plant_list(self):
        self.plant_list.clear()
        for plant in self.usersettings.repo.plants:
            if plant is None:
                continue
            item = QListWidgetItem(format_plant_info(plant, self.usersettings.lib))
            item.setData(Qt.ItemDataRole.UserRole, plant.id)
            self.plant_list.addItem(item)

    def refresh_plant_attribute_textbox(self, plant: Plant = None):
        message = format_plant_info(
            plant,
            self.usersettings.lib,
            show_normal_attribute=True,
            need_tab=True,
        )
        if plant is not None:
            for i in range(9):
                message += "\n    {}({}级)".format(
                    talent_name_list[i], plant.stone_level_list[i]
                )
            message += "\n    灵魂等级: {}级".format(plant.soul_level)
        self.plant_attribute_list.setPlainText(message)

    def plant_list_item_clicked(self, item):
        plant_id = item.data(Qt.ItemDataRole.UserRole)
        plant = self.usersettings.repo.get_plant(plant_id)
        if plant is None:
            self.usersettings.logger.log("仓库里没有id为{}的植物，可能已被删除".format(plant_id))
            return
        self.refresh_plant_attribute_textbox(plant)

    def refresh_plant_list_btn_clicked(self):
        self.usersettings.repo.refresh_repository()
        self.refresh_plant_list()
        self.refresh_plant_attribute_textbox()

    def upgrade_finish(self):
        self.refresh_plant_attribute_textbox()
        self.usersettings.repo.refresh_repository()
        self.stone_upgrade_btn.setText("全部升宝石")
        self.run_thread = None
        self.interrupt_event.clear()

    def upgrade_stopped(self):
        self.stone_upgrade_btn.setText("全部升宝石")
        self.stone_upgrade_btn.setEnabled(True)

    def skill_upgrade_btn_clicked(self):
        self.stone_upgrade_btn.setDisabled(True)
        QApplication.processEvents()
        if self.stone_upgrade_btn.text() == "全部升宝石":
            try:
                selected_plant_id_list = [
                    item.data(Qt.ItemDataRole.UserRole)
                    for item in self.plant_list.selectedItems()
                ]

                if len(selected_plant_id_list) == 0:
                    self.usersettings.logger.log("请先选择一个植物")
                    return
                plant_list = [
                    self.usersettings.repo.get_plant(plant_id)
                    for plant_id in selected_plant_id_list
                ]
                plant_list = [plant for plant in plant_list if plant is not None]
                if len(plant_list) == 0:
                    self.usersettings.logger.log("选中的植物不存在")
                    return
                self.stone_upgrade_btn.setText("中止")
                self.run_thread = UpgradeStoneThread(
                    plant_list,
                    self.usersettings,
                    self.interrupt_event,
                    self.upgrade_finish_signal,
                    self.rest_event,
                )
                self.rest_event.clear()
                self.run_thread.start()
            finally:
                self.stone_upgrade_btn.setEnabled(True)
        elif self.stone_upgrade_btn.text() == "中止":
            self.interrupt_event.set()
            WaitEventThread(self.rest_event, self.upgrade_stopped_signal).start()
        else:
            self.stone_upgrade_btn.setEnabled(True)
            raise RuntimeError(f"未知按钮文本：{self.stone_upgrade_btn.text()}")


class UpgradeSkillThread(Thread):
    def __init__(
        self,
        plant_list: list[Plant],
        usersettings: UserSettings,
        interrupt_event: Event,
        upgrade_finish_signal,
        rest_event: Event,
    ):
        super().__init__()
        self.plant_list = [plant for plant in plant_list if plant is not None]
        self.usersettings = usersettings
        self.interrupt_event = interrupt_event
        self.upgrade_finish_signal = upgrade_finish_signal
        self.rest_event = rest_event

    def upgrade_plant_skill(self, plant: Plant, skill):
        is_spec = False
        if int(skill['id']) == plant.special_skill_id:
            is_spec = True
        result = self.usersettings.skill_stone_man.upgrade_skill(
            plant.id, skill, is_spec
        )
        if result is None:
            return False
        if not result['success']:
            self.usersettings.logger.log(result['result'])
            return False
        else:
            skill_name = "{}({}级)".format(skill["name"], skill["grade"])
            if result["upgrade_success"]:
                self.usersettings.logger.log("{}升级成功".format(skill_name))
                for i, skill_id in enumerate(plant.skill_id_list):
                    if skill_id == int(skill["id"]):
                        plant.skill_id_list[i] = int(skill["next_grade_id"])
                        break
                else:
                    if plant.special_skill_id is not None:
                        if plant.special_skill_id == int(skill["id"]):
                            plant.special_skill_id = int(skill["next_grade_id"])
            else:
                self.usersettings.logger.log("{}升级失败，技能等级没有变化".format(skill_name))
                return False
        return True

    def upgrade(self):
        upgrade_list = []
        for plant in self.plant_list:
            if plant is None:
                continue
            for skill_id in plant.skill_id_list:
                skill = self.usersettings.lib.get_skill(skill_id)
                if int(skill['next_grade_id']) == 0:
                    continue
                upgrade_list.append((plant, self.usersettings.lib.get_skill(skill_id)))
            if plant.special_skill_id is not None:
                skill = self.usersettings.lib.get_spec_skill(plant.special_skill_id)
                if int(skill['next_grade_id']) == 0:
                    continue
                upgrade_list.append(
                    (
                        plant,
                        self.usersettings.lib.get_spec_skill(plant.special_skill_id),
                    )
                )
        while not self.interrupt_event.is_set():
            future_list = []
            reserved_index_list = []
            has_exception = False
            for plant, skill in upgrade_list:
                future_list.append(
                    self.pool.submit(self.upgrade_plant_skill, plant, skill)
                )
            for i, future in enumerate(concurrent.futures.as_completed(future_list)):
                if self.interrupt_event.is_set():
                    return
                try:
                    if future.result():
                        reserved_index_list.append(i)
                except Exception as e:
                    self.usersettings.logger.log(
                        "技能升级异常，异常种类：{}".format(type(e).__name__)
                    )
                    has_exception = True
                    reserved_index_list.append(i)

            if has_exception:
                self.usersettings.repo.refresh_repository()
            upgrade_list: list[tuple[Plant, dict]] = [
                upgrade_list[i] for i in reserved_index_list
            ]
            new_upgrade_list = []
            for plant, skill in upgrade_list:
                plant = self.usersettings.repo.get_plant(plant.id)
                if plant is None:
                    continue
                for skill_id in plant.skill_id_list:
                    if skill_id == int(skill["next_grade_id"]) or skill_id == int(
                        skill["id"]
                    ):
                        new_skill = self.usersettings.lib.get_skill(skill_id)
                        if int(new_skill['next_grade_id']) == 0:
                            break
                        new_upgrade_list.append((plant, new_skill))
                        break
                if plant.special_skill_id is not None:
                    if plant.special_skill_id == int(
                        skill["next_grade_id"]
                    ) or plant.special_skill_id == int(skill["id"]):
                        new_skill = self.usersettings.lib.get_spec_skill(
                            plant.special_skill_id
                        )
                        if not int(new_skill['next_grade_id']) == 0:
                            new_upgrade_list.append((plant, new_skill))
            upgrade_list = new_upgrade_list
            if len(upgrade_list) == 0:
                break

    def run(self):
        try:
            self.pool = concurrent.futures.ThreadPoolExecutor(
                max_workers=self.usersettings.skill_stone_man.pool_size
            )
            self.upgrade()
        finally:
            self.pool.shutdown(cancel_futures=True)
            self.upgrade_finish_signal.emit()
            self.rest_event.set()


class UpgradeStoneThread(Thread):
    def __init__(
        self,
        plant_list: list[Plant],
        usersettings: UserSettings,
        interrupt_event: Event,
        upgrade_finish_signal,
        rest_event: Event,
    ):
        super().__init__()
        self.plant_list = [plant for plant in plant_list if plant is not None]
        self.usersettings = usersettings
        self.interrupt_event = interrupt_event
        self.upgrade_finish_signal = upgrade_finish_signal
        self.rest_event = rest_event

    def upgrade_plant_stone(self, plant: Plant, stone_index, replace=False):
        result = self.usersettings.skill_stone_man.upgrade_stone(plant.id, stone_index)
        if result is None:
            return False
        if not result['success']:
            self.usersettings.logger.log(result['result'])
            return False
        result = result['result']
        if replace:
            plant.stone_level_list[stone_index] = int(result['talent']['talent'])
        return True

    def upgrade(self):
        upgrade_list = []
        for plant in self.plant_list:
            if plant is None:
                continue
            for i in range(9):
                if plant.stone_level_list[i] < 10:
                    upgrade_list.append((plant, i))
        while not self.interrupt_event.is_set():
            future_list = []
            reserved_index_list = []
            has_exception = False
            for plant, stone_index in upgrade_list:
                future_list.append(
                    self.pool.submit(self.upgrade_plant_stone, plant, stone_index)
                )
            for i, future in enumerate(concurrent.futures.as_completed(future_list)):
                if self.interrupt_event.is_set():
                    return
                try:
                    if future.result():
                        reserved_index_list.append(i)
                except Exception as e:
                    self.usersettings.logger.log(
                        "宝石升级异常，异常种类：{}".format(type(e).__name__)
                    )
                    has_exception = True
                    reserved_index_list.append(i)

            if has_exception:
                self.usersettings.repo.refresh_repository()
            upgrade_list: list[tuple[Plant, dict]] = [
                upgrade_list[i] for i in reserved_index_list
            ]
            new_upgrade_list = []
            for plant, stone_index in upgrade_list:
                plant = self.usersettings.repo.get_plant(plant.id)
                if plant is None:
                    continue
                if plant.stone_level_list[stone_index] < 10:
                    new_upgrade_list.append((plant, stone_index))
            upgrade_list = new_upgrade_list
            if len(upgrade_list) == 0:
                break

    def run(self):
        try:
            self.pool = concurrent.futures.ThreadPoolExecutor(
                max_workers=self.usersettings.skill_stone_man.pool_size
            )
            self.upgrade()
        finally:
            self.pool.shutdown(cancel_futures=True)
            self.upgrade_finish_signal.emit()
            self.rest_event.set()
