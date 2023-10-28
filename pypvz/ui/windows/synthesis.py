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
    QPlainTextEdit,
    QComboBox,
    QCheckBox,
    QApplication,
    QLineEdit,
)
from PyQt6 import QtGui
from PyQt6.QtCore import Qt, pyqtSignal, QThread

from ..wrapped import QLabel
from ..user import UserSettings
from ...utils.common import format_number
from ...repository import Plant


class AutoSynthesisWindow(QMainWindow):
    synthesis_finish_signal = pyqtSignal()
    refresh_all_signal = pyqtSignal()

    def __init__(self, usersettings: UserSettings, parent=None):
        super().__init__(parent=parent)
        self.usersettings = usersettings
        self.interrupt_event = Event()
        self.rest_event = Event()
        self.rest_event.set()
        self.run_thread = None
        self.refresh_all_signal.connect(self.refresh_all)
        self.synthesis_finish_signal.connect(self.synthesis_finish)
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

        widget6_2_layout = QHBoxLayout()
        widget6_2_layout.addWidget(QLabel("异常后继续合成："))
        self.force_synthesisi_checkbox = QCheckBox()
        self.force_synthesisi_checkbox.setChecked(
            self.usersettings.auto_synthesis_man.force_synthesis
        )
        self.force_synthesisi_checkbox.stateChanged.connect(
            self.force_synthesisi_checkbox_value_changed
        )
        widget6_2_layout.addWidget(self.force_synthesisi_checkbox)
        widget6_layout.addLayout(widget6_2_layout)

        widget6_layout.addStretch(1)

        widget6.setLayout(widget6_layout)
        main_layout.addWidget(widget6)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def force_synthesisi_checkbox_value_changed(self):
        self.usersettings.auto_synthesis_man.force_synthesis = (
            self.force_synthesisi_checkbox.isChecked()
        )

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
            if plant is None:
                continue
            item = QListWidgetItem(self.format_plant_info(plant))
            item.setData(Qt.ItemDataRole.UserRole, plant_id)
            self.plant_pool_list.addItem(item)

    def refresh_main_plant_text_box(self):
        if self.usersettings.auto_synthesis_man.main_plant_id is not None:
            plant = self.usersettings.repo.get_plant(
                self.usersettings.auto_synthesis_man.main_plant_id
            )
            if plant is not None:
                self.choose_main_plant_text_box.setPlainText(
                    self.format_plant_info(plant)
                )
                return
        self.choose_main_plant_text_box.setPlainText("")

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
        try:
            self.auto_synthesis_btn.setDisabled(True)
            QApplication.processEvents()
            if self.auto_synthesis_btn.text() == "全部合成":
                self.auto_synthesis_btn.setText("停止合成")
                self.run_thread = SynthesisThread(
                    self.usersettings,
                    self.synthesis_finish_signal,
                    self.interrupt_event,
                    self.refresh_all_signal,
                    self.need_synthesis,
                    self.rest_event,
                    force_synthesis=self.usersettings.auto_synthesis_man.force_synthesis,
                )
                self.rest_event.clear()
                self.run_thread.start()
            elif self.auto_synthesis_btn.text() == "停止合成":
                self.interrupt_event.set()
                self.rest_event.wait()
                self.auto_synthesis_btn.setText("全部合成")
            else:
                raise NotImplementedError(
                    "全部合成按钮文本：{} 未知".format(self.auto_synthesis_btn.text())
                )
        finally:
            self.auto_synthesis_btn.setEnabled(True)

    def synthesis_finish(self):
        self.auto_synthesis_btn.setText("全部合成")
        self.run_thread = None

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

    def closeEvent(self, event):
        if self.run_thread is not None:
            self.interrupt_event.set()
            self.rest_event.wait()
        super().closeEvent(event)


class SynthesisThread(QThread):
    def __init__(
        self,
        usersettings: UserSettings,
        synthesis_finish_signal,
        interrupt_event: Event,
        refresh_all_signal,
        need_synthesis,
        rest_event: Event,
        synthesis_number=None,
        force_synthesis=False,
    ):
        super().__init__()
        self.usersettings = usersettings
        self.synthesis_number = synthesis_number
        self.synthesis_finish_signal = synthesis_finish_signal
        self.interrupt_event = interrupt_event
        self.refresh_all_signal = refresh_all_signal
        self.need_synthesis = need_synthesis
        self.rest_event = rest_event
        self.force_synthesis = force_synthesis

    def synthesis(self):
        try:
            length = len(self.usersettings.auto_synthesis_man.auto_synthesis_pool_id)
            if self.synthesis_number is not None:
                length = min(self.synthesis_number, length)
            if length == 0:
                self.usersettings.logger.log("合成池为空")
                return
            elif length < 0:
                self.usersettings.logger.log("合成次数不能为负数")
                return
            self.usersettings.auto_synthesis_man.check_data()
            while (
                not (
                    len(self.usersettings.auto_synthesis_man.auto_synthesis_pool_id)
                    == 0
                )
                and length > 0
            ):
                if self.interrupt_event.is_set():
                    self.interrupt_event.clear()
                    self.usersettings.logger.log("中止合成")
                    return
                if not self.need_synthesis():
                    return
                result = self.usersettings.auto_synthesis_man.synthesis(
                    need_check=False
                )
                self.usersettings.logger.log(result['result'])
                self.usersettings.auto_synthesis_man.check_data()
                self.refresh_all_signal.emit()
                if not result["success"]:
                    self.usersettings.logger.log("合成异常，已跳出合成")
                    return
                length -= 1
            self.usersettings.logger.log("合成完成")
        except Exception as e:
            self.usersettings.logger.log("合成异常。异常种类：{}".format(type(e).__name__))
            if self.force_synthesis:
                self.usersettings.logger.log("重启合成")
                while True:
                    try:
                        if self.interrupt_event.is_set():
                            self.interrupt_event.clear()
                            self.usersettings.logger.log("中止合成")
                            return
                        self.usersettings.auto_synthesis_man.check_data()
                        break
                    except Exception as e:
                        self.usersettings.logger.log(
                            "重启异常，暂停1秒，继续重启（一直异常请手动终止）。异常种类：{}".format(type(e).__name__)
                        )
                        sleep(1)
                if self.usersettings.auto_synthesis_man.main_plant_id is None:
                    self.usersettings.logger.log("重新设置底座为合成池中最大属性的植物")
                    plant_id = (
                        self.usersettings.auto_synthesis_man.get_max_attribute_plant_id()
                    )
                    self.usersettings.auto_synthesis_man.main_plant_id = plant_id
                    self.usersettings.auto_synthesis_man.auto_synthesis_pool_id.remove(
                        plant_id
                    )
                self.synthesis()

    def run(self):
        try:
            self.synthesis()
        finally:
            self.synthesis_finish_signal.emit()
            self.rest_event.set()
