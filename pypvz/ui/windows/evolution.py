import logging
from time import sleep
from threading import Event
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QCheckBox,
    QApplication,
)
from PyQt6 import QtGui
from PyQt6.QtCore import Qt, pyqtSignal, QThread

from ..wrapped import QLabel, signal_block_emit
from ..user import UserSettings


class EvolutionPanelWindow(QMainWindow):
    refresh_path_panel_signal = pyqtSignal(Event)
    refresh_plant_list_signal = pyqtSignal()
    evolution_finish_signal = pyqtSignal()

    def __init__(self, usersettings: UserSettings, parent=None):
        super().__init__(parent=parent)
        self.usersettings = usersettings
        self.force_evolution = True
        self.init_ui()
        self.rest_event = Event()
        self.rest_event.set()
        self.run_thread = None
        self.refresh_path_panel_signal.connect(self.refresh_evolution_path_list)
        self.refresh_plant_list_signal.connect(self.refresh_plant_list)

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

        right_panel_layout = QVBoxLayout()

        self.evolution_start_btn = evolution_start_btn = QPushButton("开始进化")
        evolution_start_btn.clicked.connect(self.evolution_start_btn_clicked)
        right_panel_layout.addWidget(evolution_start_btn)

        self.force_evolution_checkbox = force_evolution_checkbox = QCheckBox("强制进化")
        force_evolution_checkbox.setChecked(self.force_evolution)
        force_evolution_checkbox.stateChanged.connect(
            self.force_evolution_checkbox_stateChanged
        )
        right_panel_layout.addWidget(force_evolution_checkbox)

        main_layout.addLayout(right_panel_layout)

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

    def force_evolution_checkbox_stateChanged(self):
        self.force_evolution = self.force_evolution_checkbox.isChecked()

    def refresh_evolution_path_list(self, event: Event = None):
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
        if event is not None:
            event.set()

    def evolution_start_btn_clicked(self):
        try:
            self.evolution_start_btn.setDisabled(True)
            QApplication.processEvents()
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
        except Exception as e:
            self.usersettings.logger.log(str(e))
        finally:
            self.evolution_start_btn.setEnabled(True)

    def refresh_plant_list(self):
        self.plant_list.clear()
        for plant in self.usersettings.repo.plants:
            item = QListWidgetItem(
                f"{plant.name(self.usersettings.lib)}({plant.grade})"
            )
            item.setData(Qt.ItemDataRole.UserRole, plant.id)
            self.plant_list.addItem(item)

    def plant_list_refresh_btn_clicked(self):
        self.usersettings.repo.refresh_repository()
        self.refresh_plant_list()

    def evolution_path_setting_btn_clicked(self):
        if self.current_evolution_path_index is None:
            self.usersettings.logger.log("请先选择一个进化路线")
            return
        self.evolution_path_setting = EvolutionPathSetting(
            self.current_evolution_path_index,
            self.usersettings,
            self.refresh_path_panel_signal,
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


class EvolutionPanelThread(QThread):
    def __init__(
        self,
        current_evolution_path_index,
        selected_plant_id,
        usersettings: UserSettings,
        evolution_finish_signal,
        interrupt_event: Event,
        refresh_signal,
        rest_event: Event,
        force_evolution=False,
    ):
        super().__init__()
        self.current_evolution_path_index = current_evolution_path_index
        self.selected_plant_id = selected_plant_id
        self.usersettings = usersettings
        self.evolution_finish_signal = evolution_finish_signal
        self.interrupt_event = interrupt_event
        self.refresh_signal = refresh_signal
        self.rest_event = rest_event
        self.force_evolution = force_evolution

    def evolution(self):
        try:
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
            signal_block_emit(self.refresh_signal)
        except Exception as e:
            if not self.force_evolution:
                raise e
            self.usersettings.logger.log("进化异常中断，选择暂停1秒重试。异常种类：" + type(e).__name__)
            sleep(1)
            self.usersettings.repo.refresh_repository()

    def run(self):
        try:
            self.evolution()
        except Exception as e:
            self.usersettings.logger.log("进化异常中断，异常种类：" + type(e).__name__)
        finally:
            self.rest_event.set()
            self.evolution_finish_signal.emit()


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
