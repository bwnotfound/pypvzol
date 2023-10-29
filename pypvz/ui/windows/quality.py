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
    QComboBox,
    QCheckBox,
    QApplication,
)
from PyQt6 import QtGui
from PyQt6.QtCore import Qt, pyqtSignal, QThread

from ..wrapped import QLabel
from ..user import UserSettings
from ...upgrade import UpgradeMan



class UpgradeQualityWindow(QMainWindow):
    upgrade_finish_signal = pyqtSignal()
    refresh_signal = pyqtSignal()

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
        self.force_upgrade = True
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

        self.force_upgrade_checkbox = QCheckBox("异常后继续刷品")
        self.force_upgrade_checkbox.setChecked(self.force_upgrade)
        self.force_upgrade_checkbox.stateChanged.connect(
            self.force_upgrade_checkbox_state_changed
        )
        right_layout.addWidget(self.force_upgrade_checkbox)

        self.show_all_info = QCheckBox("显示所有信息")
        self.show_all_info.setChecked(False)
        right_layout.addWidget(self.show_all_info)

        right_layout.addStretch(1)

        right_widget.setLayout(right_layout)
        main_layout.addWidget(right_widget)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def force_upgrade_checkbox_state_changed(self):
        self.force_upgrade = self.force_upgrade_checkbox.isChecked()

    def refresh_plant_list(self):
        self.plant_list.clear()
        for plant in self.usersettings.repo.plants:
            item = QListWidgetItem(
                f"{plant.name(self.usersettings.lib)}({plant.grade})[{plant.quality_str}]"
            )
            item.setData(Qt.ItemDataRole.UserRole, plant.id)
            self.plant_list.addItem(item)

    def upgrade_quality_btn_clicked(self):
        try:
            self.upgrade_quality_btn.setDisabled(True)
            QApplication.processEvents()
            if self.upgrade_quality_btn.text() == "全部刷品":
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
                    self.usersettings,
                    self.upgradeMan,
                    selected_plant_id,
                    target_quality_index,
                    need_show_all_info,
                    self.upgrade_finish_signal,
                    self.interrupt_event,
                    self.refresh_signal,
                    self.rest_event,
                    force_upgrade=self.force_upgrade,
                )
                self.rest_event.clear()
                self.run_thread.start()
            elif self.upgrade_quality_btn.text() == "中止刷品":
                self.upgrade_quality_btn.setText("全部刷品")
                self.interrupt_event.set()
                self.rest_event.wait()
            else:
                raise RuntimeError(f"未知按钮文本：{self.upgrade_quality_btn.text()}")
        finally:
            self.upgrade_quality_btn.setEnabled(True)

    def upgrade_finish(self):
        self.usersettings.repo.refresh_repository()
        self.refresh_signal.emit()
        self.upgrade_quality_btn.setText("全部刷品")
        self.run_thread = None

    def closeEvent(self, event):
        if self.run_thread is not None:
            self.interrupt_event.set()
            self.rest_event.wait()
        return super().closeEvent(event)


class UpgradeQualityThread(QThread):
    def __init__(
        self,
        usersettings: UserSettings,
        upgrade_man: UpgradeMan,
        selected_plant_id,
        target_quality_index,
        need_show_all_info,
        upgrade_finish_signal,
        interrupt_event: Event,
        refresh_signal,
        rest_event: Event,
        force_upgrade=False,
    ):
        super().__init__()
        self.usersettings = usersettings
        self.upgrade_man = upgrade_man
        self.need_show_all_info = need_show_all_info
        self.selected_plant_id = selected_plant_id
        self.target_quality_index = target_quality_index
        self.upgrade_finish_signal = upgrade_finish_signal
        self.interrupt_event = interrupt_event
        self.refresh_signal = refresh_signal
        self.rest_event = rest_event
        self.force_upgrade = force_upgrade

    def upgrade_quality(self):
        has_failure = False
        try:
            for plant_id in self.selected_plant_id:
                if self.interrupt_event.is_set():
                    self.interrupt_event.clear()
                    self.usersettings.logger.reverse_log("中止刷品")
                    return
                plant = self.usersettings.repo.get_plant(plant_id)
                if plant is None:
                    continue
                if plant.quality_index >= self.target_quality_index:
                    self.usersettings.logger.reverse_log(
                        f"{plant.name(self.usersettings.lib)}({plant.grade})品质已大于等于目标品质",
                        self.need_show_all_info,
                    )
                    continue

                error_flag = False
                while True:
                    cnt, max_retry = 0, 15
                    while cnt < max_retry:
                        if self.interrupt_event.is_set():
                            self.interrupt_event.clear()
                            self.usersettings.logger.reverse_log("中止刷品")
                            return
                        cnt += 1
                        try:
                            result = self.upgrade_man.upgrade_quality(plant_id)
                        except Exception as e:
                            self.usersettings.logger.reverse_log(
                                f"刷品异常，已跳过该植物，同时暂停1秒。原因种类：{type(e).__name__}",
                                self.need_show_all_info,
                            )
                            error_flag = True
                            sleep(1)
                            break
                        if result['success']:
                            break
                        if result['error_type'] == 3:
                            self.usersettings.logger.log("品质刷新书不足，已停止刷品")
                            return
                        if result['error_type'] == 6:
                            self.usersettings.logger.reverse_log(
                                "请求升品过于频繁，选择等待1秒后重试，最多再重试{}".format(max_retry - cnt),
                                self.need_show_all_info,
                            )
                            sleep(1)
                            continue
                        else:
                            self.usersettings.logger.reverse_log(
                                result['result'] + "。已跳过该植物", self.need_show_all_info
                            )
                            error_flag = True
                            break
                    else:
                        self.usersettings.logger.reverse_log(
                            "重试次数过多，放弃升级品质，跳过该植物", self.need_show_all_info
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
                        self.usersettings.logger.log(
                            f"{plant.name(self.usersettings.lib)}({plant.grade})升品完成"
                        )
                        break
                    msg = "{}({})升品成功。当前品质：{}".format(
                        plant.name(self.usersettings.lib),
                        plant.grade,
                        result['quality_name'],
                    )
                    self.usersettings.logger.reverse_log(msg, self.need_show_all_info)
                self.refresh_signal.emit()
            self.usersettings.logger.log(f"刷品结束")
        except Exception as e:
            self.usersettings.logger.log(
                f"刷品过程中出现异常，已停止。原因种类：{type(e).__name__}"
            )
            has_failure = True
        if has_failure and self.force_upgrade:
            self.usersettings.logger.log("刷品过程中出现异常，重启刷品")
            self.usersettings.repo.refresh_repository()
            self.upgrade_quality()

    def run(self):
        try:
            self.upgrade_quality()
        finally:
            self.upgrade_finish_signal.emit()
            self.rest_event.set()