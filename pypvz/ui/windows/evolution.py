import logging
import concurrent.futures
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
    QComboBox,
)
from PyQt6 import QtGui
from PyQt6.QtCore import Qt, pyqtSignal, QThread

from ..wrapped import QLabel, signal_block_emit, WaitEventThread
from ..user import UserSettings


class EvolutionPanelWindow(QMainWindow):
    refresh_path_panel_signal = pyqtSignal()
    refresh_plant_list_signal = pyqtSignal(Event)
    evolution_finish_signal = pyqtSignal()
    evolution_stop_signal = pyqtSignal()

    def __init__(self, usersettings: UserSettings, parent=None):
        super().__init__(parent=parent)
        self.usersettings = usersettings
        self.init_ui()
        self.rest_event = Event()
        self.rest_event.set()
        self.interrupt_event = Event()
        self.run_thread = None
        self.refresh_path_panel_signal.connect(self.refresh_evolution_path_list)
        self.refresh_plant_list_signal.connect(self.refresh_plant_list)
        self.evolution_finish_signal.connect(self.evolution_finished)
        self.evolution_stop_signal.connect(self.evolution_stopped)

    def init_ui(self):
        self.setWindowTitle("进化面板")

        # 将窗口居中显示，宽度为显示器宽度的30%，高度为显示器高度的50%
        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.6), int(screen_size.height() * 0.5))
        self.move(int(screen_size.width() * 0.2), int(screen_size.height() * 0.25))

        main_widget = QWidget()
        main_layout = QHBoxLayout()

        plant_list_widget = QWidget()
        plant_list_widget.setFixedWidth(int(self.width() * 0.3))
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
        evolution_path_widget.setFixedWidth(int(self.width() * 0.45))
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
        right_panel_layout.addStretch(1)

        self.evolution_start_btn = QPushButton("开始进化")
        self.evolution_start_btn.clicked.connect(self.evolution_start_btn_clicked)
        right_panel_layout.addWidget(self.evolution_start_btn)

        layout = QHBoxLayout()
        layout.addWidget(QLabel("并发线程数:"))
        self.pool_size_combobox = QComboBox()
        self.pool_size_combobox.addItems([str(i) for i in range(1, 31)])
        self.pool_size_combobox.setCurrentIndex(2)
        layout.addWidget(self.pool_size_combobox)
        right_panel_layout.addLayout(layout)

        right_panel_layout.addStretch(1)
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

    def evolution_finished(self):
        self.evolution_start_btn.setText("开始进化")
        self.run_thread = None
        self.interrupt_event.clear()

    def evolution_stopped(self):
        self.evolution_start_btn.setText("开始进化")
        self.evolution_start_btn.setEnabled(True)

    def evolution_start_btn_clicked(self):
        self.evolution_start_btn.setDisabled(True)
        QApplication.processEvents()
        if self.evolution_start_btn.text() == "开始进化":
            try:
                if self.current_evolution_path_index is None:
                    self.usersettings.logger.log("请先选择一个进化路线")
                    return
                if len(self.selected_plant_id) == 0:
                    self.usersettings.logger.log("请先选择一个或多个植物")
                    return
                self.evolution_start_btn.setText("停止进化")
                self.run_thread = EvolutionPanelThread(
                    self.current_evolution_path_index,
                    self.selected_plant_id,
                    self.usersettings,
                    self.evolution_finish_signal,
                    self.interrupt_event,
                    self.refresh_plant_list_signal,
                    self.rest_event,
                    pool_size=self.pool_size_combobox.currentIndex() + 1,
                )
                self.rest_event.clear()
                self.run_thread.start()
            finally:
                self.evolution_start_btn.setEnabled(True)
        elif self.evolution_start_btn.text() == "停止进化":
            self.interrupt_event.set()
            WaitEventThread(self.rest_event, self.evolution_stop_signal).start()
        else:
            self.evolution_start_btn.setEnabled(True)
            raise NotImplementedError(
                "开始进化按钮文本：{} 未知".format(self.evolution_start_btn.text())
            )

    def refresh_plant_list(self, event: Event = None):
        self.plant_list.clear()
        for plant in self.usersettings.repo.plants:
            item = QListWidgetItem(
                f"{plant.name(self.usersettings.lib)}({plant.grade})"
            )
            item.setData(Qt.ItemDataRole.UserRole, plant.id)
            self.plant_list.addItem(item)
        if event is not None:
            event.set()

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
        pool_size=3,
    ):
        super().__init__()
        self.current_evolution_path_index = current_evolution_path_index
        self.selected_plant_id = selected_plant_id
        self.usersettings = usersettings
        self.evolution_finish_signal = evolution_finish_signal
        self.interrupt_event = interrupt_event
        self.refresh_signal = refresh_signal
        self.rest_event = rest_event
        self.pool_size = pool_size

    def _evolution(self, plant_id):
        result = self.usersettings.plant_evolution.plant_evolution_all(
            self.current_evolution_path_index,
            plant_id,
            self.interrupt_event,
        )
        self.usersettings.logger.log(result["result"])

    def evolution(self):
        evolution_plant_id_set = set(self.selected_plant_id)
        while True:
            if self.interrupt_event.is_set():
                return
            plant_id_list = list(evolution_plant_id_set)
            futures = [
                self.pool.submit(self._evolution, plant_id)
                for plant_id in plant_id_list
            ]
            for i, result in enumerate(futures):
                if self.interrupt_event.is_set():
                    break
                try:
                    result.result()
                    evolution_plant_id_set.remove(plant_id_list[i])
                except Exception as e:
                    plant = self.usersettings.repo.get_plant(plant_id_list[i])
                    if plant is None:
                        self.usersettings.logger.log(
                            "进化植物不存在并出现异常，异常种类：{}".format(type(e).__name__)
                        )
                    else:
                        self.usersettings.logger.log(
                            "进化植物{}出现异常，异常种类：{}".format(
                                plant.name(self.usersettings.lib), type(e).__name__
                            )
                        )
            self.usersettings.repo.refresh_repository()
            signal_block_emit(self.refresh_signal)
            if self.interrupt_event.is_set() or len(evolution_plant_id_set) == 0:
                return

    def run(self):
        try:
            self.pool = concurrent.futures.ThreadPoolExecutor(
                max_workers=self.pool_size
            )
            self.evolution()
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
