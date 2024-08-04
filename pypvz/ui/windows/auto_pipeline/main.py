from threading import Event
from queue import Queue

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QComboBox,
    QLineEdit,
    QApplication,
    QCheckBox,
)
from PyQt6 import QtGui
from PyQt6.QtCore import Qt, pyqtSignal

from ...wrapped import QLabel
from ...user import UserSettings, PipelineScheme, Pipeline
from .run_thread import RunSchemeThread
from ....utils.common import WaitEventThread


class PipelineSettingWindow(QMainWindow):
    finish_signal = pyqtSignal()
    stop_signal = pyqtSignal()

    def __init__(self, usersettings: UserSettings, parent=None):
        super().__init__(parent=parent)
        self.usersettings = usersettings
        self.stop_queue = Queue()
        self.rest_event = Event()
        self.run_thread = None
        self.finish_signal.connect(self.finish_signal_handler)
        self.stop_signal.connect(self.stop_handler)
        self.init_ui()
        self.refresh_scheme_list()

    def init_ui(self):
        self.setWindowTitle("全自动流水线设置")

        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.8), int(screen_size.height() * 0.6))
        self.move(int(screen_size.width() * 0.1), int(screen_size.height() * 0.2))

        self.main_widget = QWidget()
        self.main_layout = QHBoxLayout()
        self.main_layout.setSpacing(10)

        self.scheme_choose_widget = QWidget()
        self.scheme_choose_widget.setFixedWidth(int(self.width() * 0.2))
        self.scheme_choose_layout = QVBoxLayout()
        self.scheme_choose_layout.addWidget(QLabel("方案列表"))
        self.scheme_list = QListWidget()
        self.scheme_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.scheme_list.itemClicked.connect(self.scheme_list_item_clicked)
        self.scheme_choose_layout.addWidget(self.scheme_list)

        self.scheme_name_layout = QHBoxLayout()
        self.scheme_name_layout.addWidget(QLabel("方案名称"))
        self.scheme_name_inputbox = QLineEdit()
        self.scheme_name_layout.addWidget(self.scheme_name_inputbox)
        self.scheme_choose_layout.addLayout(self.scheme_name_layout)

        self.scheme_add_btn = QPushButton("新加方案")
        self.scheme_add_btn.clicked.connect(self.scheme_add_btn_clicked)
        self.scheme_choose_layout.addWidget(self.scheme_add_btn)

        self.scheme_remove_btn = QPushButton("删除方案")
        self.scheme_remove_btn.clicked.connect(self.scheme_remove_btn_clicked)
        self.scheme_choose_layout.addWidget(self.scheme_remove_btn)

        self.scheme_rename_btn = QPushButton("重命名方案")
        self.scheme_rename_btn.clicked.connect(self.scheme_rename_btn_clicked)
        self.scheme_choose_layout.addWidget(self.scheme_rename_btn)
        self.scheme_choose_layout.addWidget(QLabel("\n"))

        self.start_btn = QPushButton("开始")
        self.start_btn.clicked.connect(self.start_btn_clicked)
        self.scheme_choose_layout.addWidget(self.start_btn)
        self.stop_after_finish_checkbox = QCheckBox("一周期完成后才停止")
        self.stop_after_finish_checkbox.setChecked(
            self.usersettings.pipeline_man.stop_after_finish
        )
        self.stop_after_finish_checkbox.stateChanged.connect(
            self.stop_after_finish_checkbox_stateChanged
        )
        self.scheme_choose_layout.addWidget(self.stop_after_finish_checkbox)

        self.scheme_choose_widget.setLayout(self.scheme_choose_layout)
        self.main_layout.addWidget(self.scheme_choose_widget)

        self.scheme_widget = SchemeWidget()
        self.main_layout.addWidget(self.scheme_widget)
        self.main_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.main_widget)

    def stop_after_finish_checkbox_stateChanged(self):
        self.usersettings.pipeline_man.stop_after_finish = (
            self.stop_after_finish_checkbox.isChecked()
        )

    def refresh_scheme_list(self):
        self.scheme_list.clear()
        for scheme in self.usersettings.pipeline_man.scheme_list:
            item = QListWidgetItem(scheme.name)
            item.setData(Qt.ItemDataRole.UserRole, scheme)
            self.scheme_list.addItem(item)

    def choose_scheme(self, scheme: PipelineScheme):
        self.scheme_widget.switch_scheme(scheme)

    def current_scheme(self):
        items = self.scheme_list.selectedItems()
        if len(items) == 0:
            return None
        item = items[0]
        return item.data(Qt.ItemDataRole.UserRole)

    def scheme_list_item_clicked(self, item: QListWidgetItem):
        scheme = item.data(Qt.ItemDataRole.UserRole)
        self.scheme_name_inputbox.setText(scheme.name)
        self.choose_scheme(scheme)

    def scheme_add_btn_clicked(self):
        self.usersettings.pipeline_man.new_scheme()
        self.refresh_scheme_list()

    def scheme_remove_btn_clicked(self):
        scheme = self.current_scheme()
        if scheme is None:
            self.usersettings.logger.log("未选中任何方案")
            return
        self.usersettings.pipeline_man.remove_scheme(scheme)
        self.choose_scheme(None)
        self.refresh_scheme_list()

    def scheme_rename_btn_clicked(self):
        scheme = self.current_scheme()
        if scheme is None:
            self.usersettings.logger.log("未选中任何方案")
            return
        scheme.name = self.scheme_name_inputbox.text()
        self.refresh_scheme_list()

    def start_btn_clicked(self):
        scheme = self.current_scheme()
        if scheme is None:
            self.usersettings.logger.log("未选中任何方案")
            return
        self.start_btn.setDisabled(True)
        QApplication.processEvents()
        if self.start_btn.text() == "开始":
            try:
                self.start_btn.setText("停止")
                self.run_thread = RunSchemeThread(
                    scheme,
                    self.stop_queue,
                    self.finish_signal,
                    self.rest_event,
                    self.usersettings.pipeline_man.stop_after_finish,
                )
                self.rest_event.clear()
                self.run_thread.start()
            finally:
                self.start_btn.setEnabled(True)
        elif self.start_btn.text() == "停止":
            self.stop_queue.put(True)
            WaitEventThread(self.rest_event, self.stop_signal).start()
        else:
            self.start_btn.setEnabled(True)
            raise NotImplementedError(
                "开始全自动按钮文本：{} 未知".format(self.start_btn.text())
            )

    def stop_handler(self):
        self.start_btn.setText("开始")
        self.start_btn.setEnabled(True)

    def finish_signal_handler(self):
        self.start_btn.setText("开始")
        self.run_thread = None
        while self.stop_queue.qsize() > 0:
            self.stop_queue.get()

    def closeEvent(self, event):
        if self.run_thread is not None:
            self.stop_queue.put(True)
            # self.rest_event.wait()
        super().closeEvent(event)


class SchemeWidget(QWidget):
    change_pipeline1_choice_index_signal = pyqtSignal(int)
    change_pipeline2_choice_index_signal = pyqtSignal(int)
    change_pipeline3_choice_index_signal = pyqtSignal(int)
    change_pipeline4_choice_index_signal = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.main_layout = QHBoxLayout()
        self.main_layout.setSpacing(0)
        self.setLayout(self.main_layout)
        self.change_pipeline1_choice_index_signal.connect(
            self.change_pipeline1_choice_index
        )
        self.change_pipeline2_choice_index_signal.connect(
            self.change_pipeline2_choice_index
        )
        self.change_pipeline3_choice_index_signal.connect(
            self.change_pipeline3_choice_index
        )
        self.change_pipeline4_choice_index_signal.connect(
            self.change_pipeline4_choice_index
        )

    def switch_scheme(self, pipeline_scheme: PipelineScheme):
        self.pipeline_scheme = pipeline_scheme
        from ..common import delete_layout_children

        delete_layout_children(self.main_layout)
        if self.pipeline_scheme is not None:
            self.init_ui()

    def init_ui(self):
        self.pipeline1_widget = PipelineSettingWidget(
            "第一步\n目的是获得接下来使用的植物",
            self.pipeline_scheme.pipeline1,
            self.pipeline_scheme.pipeline1_choice_index,
            self.change_pipeline1_choice_index_signal,
            parent=self,
        )
        self.pipeline1_widget.setMaximumWidth(int(self.width() * 0.25))
        self.main_layout.addWidget(self.pipeline1_widget)

        self.pipeline2_widget = PipelineSettingWidget(
            "第二步\n设置练级",
            self.pipeline_scheme.pipeline2,
            self.pipeline_scheme.pipeline2_choice_index,
            self.change_pipeline2_choice_index_signal,
            parent=self,
        )
        self.pipeline2_widget.setMaximumWidth(int(self.width() * 0.25))
        self.main_layout.addWidget(self.pipeline2_widget)

        self.pipeline3_widget = PipelineSettingWidget(
            "第三步\n选择对植物进行怎样的处理",
            self.pipeline_scheme.pipeline3,
            self.pipeline_scheme.pipeline3_choice_index,
            self.change_pipeline3_choice_index_signal,
            parent=self,
        )
        self.pipeline3_widget.setMaximumWidth(int(self.width() * 0.25))
        self.main_layout.addWidget(self.pipeline3_widget)

        self.pipeline4_widget = PipelineSettingWidget(
            "第四步\n选择如何最后消耗植物",
            self.pipeline_scheme.pipeline4,
            self.pipeline_scheme.pipeline4_choice_index,
            self.change_pipeline4_choice_index_signal,
            parent=self,
        )
        self.pipeline4_widget.setMaximumWidth(int(self.width() * 0.25))
        self.main_layout.addWidget(self.pipeline4_widget)

    def change_pipeline1_choice_index(self, index):
        self.pipeline_scheme.pipeline1_choice_index = index

    def change_pipeline2_choice_index(self, index):
        self.pipeline_scheme.pipeline2_choice_index = index

    def change_pipeline3_choice_index(self, index):
        self.pipeline_scheme.pipeline3_choice_index = index

    def change_pipeline4_choice_index(self, index):
        self.pipeline_scheme.pipeline4_choice_index = index


class PipelineSettingWidget(QWidget):
    def __init__(
        self,
        msg,
        pipeline_list: list[Pipeline],
        pipeline_choice_index: int,
        change_choice_index_signal,
        parent=None,
    ):
        super().__init__(parent=parent)
        self.parent_widget = parent
        self.msg = msg
        self.pipeline_list = pipeline_list
        self.pipeline_choice_index = pipeline_choice_index
        self.change_choice_index_signal = change_choice_index_signal
        self.init_ui()
        self.refresh()

    def init_ui(self):
        pipeline_layout = QVBoxLayout()
        pipeline_layout.addStretch(1)

        info_label = QLabel(self.msg)
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pipeline_layout.addWidget(info_label)

        layout1 = QHBoxLayout()

        self.pipeline_combobox = QComboBox()
        for pipeline in self.pipeline_list:
            self.pipeline_combobox.addItem(pipeline.name)
        self.pipeline_combobox.setCurrentIndex(self.pipeline_choice_index)
        self.pipeline_combobox.currentIndexChanged.connect(
            self.pipeline_combobox_currentIndexChanged
        )
        layout1.addWidget(self.pipeline_combobox)

        self.pipeline1_setting_btn = QPushButton("设置")
        self.pipeline1_setting_btn.clicked.connect(self.pipeline_setting_btn_clicked)
        layout1.addWidget(self.pipeline1_setting_btn)

        pipeline_layout.addLayout(layout1)

        self.pipeline_setting_widget_layout = QHBoxLayout()
        pipeline_layout.addLayout(self.pipeline_setting_widget_layout)

        pipeline_layout.addStretch(1)
        self.setLayout(pipeline_layout)

    def refresh(self):
        from ..common import delete_layout_children

        delete_layout_children(self.pipeline_setting_widget_layout)
        if self.pipeline_list[self.pipeline_choice_index].has_setting_widget():
            setting_widget = self.pipeline_list[
                self.pipeline_choice_index
            ].setting_widget(parent=self.parent_widget)
            self.pipeline_setting_widget_layout.addWidget(setting_widget)
        if self.pipeline_list[self.pipeline_choice_index].has_setting_window():
            self.pipeline1_setting_btn.setEnabled(True)
        else:
            self.pipeline1_setting_btn.setDisabled(True)

    def pipeline_setting_btn_clicked(self):
        if self.pipeline_list[self.pipeline_choice_index].has_setting_window():
            self.setting_window = self.pipeline_list[
                self.pipeline_choice_index
            ].setting_window(parent=self.parent_widget)
            self.setting_window.show()

    def pipeline_combobox_currentIndexChanged(self):
        self.pipeline_choice_index = self.pipeline_combobox.currentIndex()
        self.change_choice_index_signal.emit(self.pipeline_combobox.currentIndex())
        self.refresh()
