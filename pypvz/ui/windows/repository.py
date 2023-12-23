import logging
import concurrent.futures
from threading import Event, Thread
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QTabWidget,
    QComboBox,
    QApplication,
    QSpinBox,
)
from PyQt6 import QtGui
from PyQt6.QtCore import Qt, pyqtSignal

from ...repository import Repository
from ...library import Library
from ..wrapped import QLabel
from ..user import UserSettings
from ..message import Logger

from ... import Library
from ..wrapped import signal_block_emit, WaitEventThread


class AutoUseItemSettingWindow(QMainWindow):
    refresh_all_signal = pyqtSignal(Event)
    use_item_finish_signal = pyqtSignal()
    use_item_stop_signal = pyqtSignal()

    def __init__(self, usersettings: UserSettings, parent=None):
        super().__init__(parent=parent)
        self.usersettings = usersettings
        self.run_thread = None
        self.refresh_all_signal.connect(self.refresh_all)
        self.use_item_finish_signal.connect(self.use_item_finished)
        self.use_item_stop_signal.connect(self.use_item_stoped)
        self.rest_event = Event()
        self.rest_event.set()
        self.interrupt_event = Event()
        self.init_ui()
        self.refresh_all()

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
        use_item_panel_widget.setFixedWidth(int(self.width() * 0.3))
        use_item_panel_layout = QVBoxLayout()
        use_item_panel_layout.addStretch(1)

        layout = QHBoxLayout()
        self.use_item_all_btn = QPushButton("全部使用")
        self.use_item_all_btn.clicked.connect(self.use_item_btn_clicked)
        layout.addWidget(self.use_item_all_btn)
        layout.addWidget(QLabel("并发线程数:"))
        self.pool_size_combobox = QComboBox()
        self.pool_size_combobox.addItems([str(i) for i in range(1, 51)])
        self.pool_size_combobox.setCurrentIndex(2)
        layout.addWidget(self.pool_size_combobox)
        use_item_panel_layout.addLayout(layout)

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

    def refresh_plant_list(self):
        self.plant_list.clear()
        for plant in self.usersettings.repo.plants:
            item = QListWidgetItem(
                f"{plant.name(self.usersettings.lib)} ({plant.grade})[{plant.quality_str}]"
            )
            item.setData(Qt.ItemDataRole.UserRole, plant.id)
            self.plant_list.addItem(item)

    def refresh_all(self, event: Event = None):
        self.refresh_item_list()
        self.refresh_plant_list()
        if event is not None:
            event.set()

    def get_selected_tool(self):
        cur_index = self.item_list_tab.currentIndex()
        if cur_index == 0:
            selected_items = self.item_list.selectedItems()
        elif cur_index == 1:
            selected_items = self.box_list.selectedItems()
        else:
            self.usersettings.logger.log("请选择道具或宝箱")
            return []
        return selected_items

    def part_use_item_btn_clicked(self):
        self.part_use_item_btn.setDisabled(True)
        QApplication.processEvents()
        try:
            selected_items = self.get_selected_tool()
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

    def use_item_finished(self):
        self.use_item_all_btn.setText("全部使用")
        self.run_thread = None
        self.interrupt_event.clear()

    def use_item_stoped(self):
        self.use_item_all_btn.setText("全部使用")
        self.use_item_all_btn.setEnabled(True)

    def use_item_btn_clicked(self):
        self.use_item_all_btn.setDisabled(True)
        QApplication.processEvents()
        if self.use_item_all_btn.text() == "全部使用":
            try:
                selected_items = self.get_selected_tool()
                if len(selected_items) == 0:
                    self.usersettings.logger.log("请先选中物品")
                    return
                tool_id_list = [
                    item.data(Qt.ItemDataRole.UserRole) for item in selected_items
                ]
                self.use_item_all_btn.setText("停止使用")
                self.run_thread = UseItemThread(
                    tool_id_list,
                    self.usersettings.repo,
                    self.usersettings.lib,
                    self.usersettings.logger,
                    self.use_item_finish_signal,
                    self.interrupt_event,
                    self.refresh_all_signal,
                    self.rest_event,
                    pool_size=self.pool_size_combobox.currentIndex() + 1,
                )
                self.rest_event.clear()
                self.run_thread.start()
            finally:
                self.use_item_all_btn.setEnabled(True)
        elif self.use_item_all_btn.text() == "停止使用":
            self.interrupt_event.set()
            WaitEventThread(self.rest_event, self.use_item_stop_signal).start()
        else:
            self.use_item_all_btn.setEnabled(True)
            raise NotImplementedError(
                "全部使用按钮文本：{} 未知".format(self.use_item_all_btn.text())
            )

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            pass

    def closeEvent(self, event):
        if self.run_thread is not None:
            self.interrupt_event.set()
            # self.rest_event.wait()
        super().closeEvent(event)


class UseItemThread(Thread):
    def __init__(
        self,
        use_item_id_list: list,
        repo: Repository,
        lib: Library,
        logger: Logger,
        use_item_finish_signal,
        interrupt_event: Event,
        refresh_all_signal,
        rest_event: Event,
        pool_size=3,
    ):
        super().__init__()
        self.use_item_id_list = use_item_id_list
        self.lib = lib
        self.repo = repo
        self.logger = logger
        self.use_item_finish_signal = use_item_finish_signal
        self.interrupt_event = interrupt_event
        self.refresh_all_signal = refresh_all_signal
        self.rest_event = rest_event
        self.pool_size = pool_size

    def _use_item(self, tool_id):
        repo_tool = self.repo.get_tool(tool_id)
        if repo_tool is None:
            return
        tool_type = self.lib.get_tool_by_id(tool_id).type
        amount = repo_tool['amount']
        while amount > 0:
            if self.interrupt_event.is_set():
                return
            use_amount = min(amount, 99999)
            if tool_type == 3:
                result = self.repo.open_box(tool_id, use_amount, self.lib)
                self.logger.log(result['result'])
                if not result['success']:
                    break
                if result['open_amount'] == 0:
                    self.logger.log("宝箱打开0个，可能有其他问题，跳过开箱")
                    break
                amount -= result['open_amount']
            else:
                result = self.repo.use_item(tool_id, use_amount, self.lib)
                self.logger.log(result['result'])

    def use_item(self):
        tool_id_set = set(self.use_item_id_list)
        while True:
            if self.interrupt_event.is_set():
                return
            use_item_id_list = list(tool_id_set)
            futures = [
                self.pool.submit(self._use_item, tool_id)
                for tool_id in use_item_id_list
            ]
            for i, result in enumerate(futures):
                if self.interrupt_event.is_set():
                    break
                try:
                    result.result()
                    tool_id_set.remove(use_item_id_list[i])
                except Exception as e:
                    self.logger.log(
                        "使用{}出现异常，异常类型：{}".format(
                            self.lib.get_tool_by_id(use_item_id_list[i]).name,
                            type(e).__name__,
                        )
                    )
            self.repo.refresh_repository()
            signal_block_emit(self.refresh_all_signal)
            if self.interrupt_event.is_set() or len(tool_id_set) == 0:
                return

    def run(self):
        try:
            self.pool = concurrent.futures.ThreadPoolExecutor(
                max_workers=self.pool_size
            )
            self.use_item()
        finally:
            self.use_item_finish_signal.emit()
            self.rest_event.set()
