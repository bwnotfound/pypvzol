from time import sleep
import logging
from threading import Event, Thread
import concurrent.futures

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QComboBox,
    QCheckBox,
    QApplication,
)
from PyQt6 import QtGui
from PyQt6.QtCore import Qt, pyqtSignal

from ..wrapped import QLabel, signal_block_emit, WaitEventThread
from ..user import UserSettings
from ...utils.common import format_plant_info
from ... import Repository, UpgradeMan, Library


class UpgradeQualityWindow(QMainWindow):
    upgrade_finish_signal = pyqtSignal()
    refresh_signal = pyqtSignal(Event)
    upgrade_quality_stoped_signal = pyqtSignal()

    def __init__(self, usersettings: UserSettings, parent=None):
        super().__init__(parent=parent)
        self.usersettings = usersettings
        self.upgradeMan = UpgradeMan(self.usersettings.cfg)
        self.interrupt_event = Event()
        self.rest_event = Event()
        self.rest_event.set()
        self.run_thread = None
        self.refresh_signal.connect(self.refresh_plant_list)
        self.upgrade_finish_signal.connect(self.upgrade_finish)
        self.upgrade_quality_stoped_signal.connect(self.upgrade_quality_stoped)
        self.pool_size = 3
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

        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_layout.addStretch(1)

        layout1 = QHBoxLayout()

        self.upgrade_quality_choice = QComboBox()
        for quality_name in self.upgradeMan.quality_name:
            self.upgrade_quality_choice.addItem(quality_name)
        self.upgrade_quality_choice.setCurrentIndex(
            self.upgradeMan.quality_name.index("魔神")
        )
        layout1.addWidget(self.upgrade_quality_choice)

        self.upgrade_quality_btn = upgrade_quality_btn = QPushButton("全部刷品")
        upgrade_quality_btn.clicked.connect(self.upgrade_quality_btn_clicked)
        layout1.addWidget(upgrade_quality_btn)

        right_layout.addLayout(layout1)

        pool_layout = QHBoxLayout()
        pool_layout.addWidget(QLabel("刷品并发数"))
        self.pool_size_combobox = QComboBox()
        self.pool_size_combobox.addItems([str(i) for i in range(1, 21)])
        self.pool_size_combobox.setCurrentIndex(self.pool_size - 1)
        self.pool_size_combobox.currentIndexChanged.connect(
            self.pool_size_combobox_current_index_changed
        )
        pool_layout.addWidget(self.pool_size_combobox)
        right_layout.addLayout(pool_layout)

        self.show_all_info = QCheckBox("显示所有信息")
        self.show_all_info.setChecked(False)
        right_layout.addWidget(self.show_all_info)

        right_layout.addStretch(1)

        right_widget.setLayout(right_layout)
        main_layout.addWidget(right_widget)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def pool_size_combobox_current_index_changed(self):
        self.pool_size = self.pool_size_combobox.currentIndex() + 1

    def refresh_plant_list(self, event: Event = None):
        self.plant_list.clear()
        for plant in self.usersettings.repo.plants:
            item = QListWidgetItem(format_plant_info(plant, self.usersettings.lib))
            item.setData(Qt.ItemDataRole.UserRole, plant.id)
            self.plant_list.addItem(item)
        if event is not None:
            event.set()

    def upgrade_quality_stoped(self):
        self.upgrade_quality_btn.setText("全部刷品")
        self.upgrade_quality_btn.setEnabled(True)

    def upgrade_quality_btn_clicked(self):
        self.upgrade_quality_btn.setDisabled(True)
        QApplication.processEvents()
        if self.upgrade_quality_btn.text() == "全部刷品":
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
                self.upgrade_quality_btn.setText("中止刷品")
                self.run_thread = UpgradeQualityThread(
                    self.usersettings.repo,
                    self.usersettings.lib,
                    self.usersettings.logger,
                    self.upgradeMan,
                    selected_plant_id,
                    target_quality_index,
                    need_show_all_info,
                    self.upgrade_finish_signal,
                    self.interrupt_event,
                    self.refresh_signal,
                    self.rest_event,
                    pool_size=self.pool_size,
                )
                self.interrupt_event.clear()
                self.rest_event.clear()
                self.run_thread.start()
            finally:
                self.upgrade_quality_btn.setEnabled(True)
        elif self.upgrade_quality_btn.text() == "中止刷品":
            self.interrupt_event.set()
            WaitEventThread(self.rest_event, self.upgrade_quality_stoped_signal).start()
        else:
            self.upgrade_quality_btn.setEnabled(True)
            raise RuntimeError(f"未知按钮文本：{self.upgrade_quality_btn.text()}")

    def upgrade_finish(self):
        self.usersettings.repo.refresh_repository()
        self.refresh_signal.emit(Event())
        self.upgrade_quality_btn.setText("全部刷品")
        self.run_thread = None
        self.interrupt_event.clear()

    def closeEvent(self, event):
        if self.run_thread is not None:
            self.interrupt_event.set()
            # self.rest_event.wait()
        return super().closeEvent(event)


class UpgradeQualityThread(Thread):
    def __init__(
        self,
        repo: Repository,
        lib: Library,
        logger,
        upgrade_man: UpgradeMan,
        selected_plant_id,
        target_quality_index,
        need_show_all_info,
        upgrade_finish_signal,
        interrupt_event: Event,
        refresh_signal,
        rest_event: Event,
        pool_size=3,
    ):
        super().__init__()
        self.repo = repo
        self.lib = lib
        self.logger = logger
        self.upgrade_man = upgrade_man
        self.need_show_all_info = need_show_all_info
        self.selected_plant_id = selected_plant_id
        self.target_quality_index = target_quality_index
        self.upgrade_finish_signal = upgrade_finish_signal
        self.interrupt_event = interrupt_event
        self.refresh_signal = refresh_signal
        self.rest_event = rest_event
        self.pool_size = pool_size

    def _upgrade_quality(self, plant_id):
        has_failure = False
        try:
            if self.interrupt_event.is_set():
                return True
            plant = self.repo.get_plant(plant_id)
            if plant is None:
                return True
            if plant.quality_index >= self.target_quality_index:
                self.logger.reverse_log(
                    f"{plant.name(self.lib)}({plant.grade})品质已大于等于目标品质",
                    self.need_show_all_info,
                )
                return True
            error_flag = False
            while True:
                if self.interrupt_event.is_set():
                    return True
                result = self.upgrade_man.upgrade_quality(plant_id)
                if not result['success']:
                    if result['error_type'] == 3:
                        self.logger.log("品质刷新书不足，已停止刷品")
                        return True
                    else:
                        self.logger.reverse_log(
                            result['result'] + "。已跳过该植物", self.need_show_all_info
                        )
                        error_flag = True
                if error_flag:
                    has_failure = True
                    break
                cur_quality_index = self.upgrade_man.quality_name.index(
                    result['quality_name']
                )
                plant.quality_index = cur_quality_index
                plant.quality_str = result['quality_name']
                if cur_quality_index >= self.target_quality_index:
                    self.logger.log(f"{plant.name(self.lib)}({plant.grade})升品完成")
                    break
                msg = "{}({})升品成功。当前品质：{}".format(
                    plant.name(self.lib),
                    plant.grade,
                    result['quality_name'],
                )
                self.logger.reverse_log(msg, self.need_show_all_info)
            signal_block_emit(self.refresh_signal)
        except Exception as e:
            self.logger.log(f"刷品过程中出现异常，已跳过当前植物。原因种类：{type(e).__name__}")
            has_failure = True
        if has_failure:
            return False
        return True

    def upgrade_quality(self):
        plant_id_set = set(self.selected_plant_id)
        while True:
            self.repo.refresh_repository()
            plant_id_list = list(plant_id_set)
            futures = [
                self.pool.submit(self._upgrade_quality, plant_id)
                for plant_id in plant_id_list
            ]
            for i, result in enumerate(futures):
                try:
                    if result.result():
                        plant_id_set.remove(plant_id_list[i])
                except Exception as e:
                    logging.warning("刷品过程中出现异常，异常类型：{}".format(type(e).__name__))
            if len(plant_id_set) == 0:
                break
            self.logger.log("刷品过程中出现异常，重启刷品，一共还剩{}个植物需重新刷品".format(len(plant_id_set)))

    def run(self):
        try:
            self.pool = concurrent.futures.ThreadPoolExecutor(
                max_workers=self.pool_size
            )
            self.upgrade_quality()
        finally:
            self.pool.shutdown()
            if self.upgrade_finish_signal is not None:
                self.upgrade_finish_signal.emit()
            self.rest_event.set()
