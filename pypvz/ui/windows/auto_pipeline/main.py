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
)
from PyQt6 import QtGui
from PyQt6.QtCore import Qt, pyqtSignal

from ...wrapped import QLabel
from ...user import UserSettings
from ...user import PipelineScheme, Pipeline


class PipelineSettingWindow(QMainWindow):
    def __init__(self, usersettings: UserSettings, parent=None):
        super().__init__(parent=parent)
        self.usersettings = usersettings
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

        self.scheme_choose_widget.setLayout(self.scheme_choose_layout)
        self.main_layout.addWidget(self.scheme_choose_widget)

        self.scheme_widget = SchemeWidget()
        self.main_layout.addWidget(self.scheme_widget)
        self.main_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.main_widget)

    def refresh_scheme_list(self):
        self.scheme_list.clear()
        for scheme in self.usersettings.pipeline_man.scheme_list:
            item = QListWidgetItem(scheme.name)
            item.setData(Qt.ItemDataRole.UserRole, scheme)
            self.scheme_list.addItem(item)

    def choose_scheme(self, scheme: PipelineScheme):
        self.scheme_widget.switch_scheme(scheme)

    def scheme_list_item_clicked(self, item: QListWidgetItem):
        scheme = item.data(Qt.ItemDataRole.UserRole)
        self.scheme_name_inputbox.setText(scheme.name)
        self.choose_scheme(scheme)

    def scheme_add_btn_clicked(self):
        self.usersettings.pipeline_man.new_scheme()
        self.refresh_scheme_list()

    def scheme_remove_btn_clicked(self):
        self.usersettings.pipeline_man.remove_scheme(
            self.scheme_list.currentItem().data(Qt.ItemDataRole.UserRole)
        )

    def scheme_rename_btn_clicked(self):
        if self.scheme_list.currentItem() is None:
            self.usersettings.logger.log("未选中任何方案")
            return
        self.scheme_list.currentItem().data(
            Qt.ItemDataRole.UserRole
        ).name = self.scheme_name_inputbox.text()
        self.refresh_scheme_list()


class SchemeWidget(QWidget):
    change_pipeline1_choice_index_signal = pyqtSignal(int)
    change_pipeline2_choice_index_signal = pyqtSignal(int)
    change_pipeline3_choice_index_signal = pyqtSignal(int)
    change_pipeline4_choice_index_signal = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.main_layout = QHBoxLayout()
        self.main_layout.setSpacing(10)
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
        if self.pipeline_scheme is None:
            for i in reversed(range(self.main_layout.count())):
                self.main_layout.itemAt(i).widget().deleteLater()
        else:
            self.init_ui()

    def init_ui(self):
        # pipeline1_layout = QVBoxLayout()
        # pipeline1_layout.addStretch(1)
        # info_label = QLabel("第一步\n目的是获得接下来使用的植物")
        # info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # pipeline1_layout.addWidget(info_label)
        # self.pipeline1_combobox = QComboBox()
        # for pipeline in self.pipeline_scheme.pipeline1:
        #     self.pipeline1_combobox.addItem(pipeline.name)
        # self.pipeline1_combobox.setCurrentIndex(
        #     self.pipeline_scheme.pipeline1_choice_index
        # )
        # pipeline1_layout.addWidget(self.pipeline1_combobox)

        # # self.pipeline1_setting_btn = QPushButton("设置")
        # # self.pipeline1_setting_btn.clicked.connect(self.pipeline1_setting_btn_clicked)
        # # pipeline1_layout.addWidget(self.pipeline1_combobox)
        # pipeline1_layout.addStretch(1)
        # self.main_layout.addLayout(pipeline1_layout)
        self.pipeline1_widget = PipelineSettingWidget(
            "第一步\n目的是获得接下来使用的植物",
            self.pipeline_scheme.pipeline1,
            self.pipeline_scheme.pipeline1_choice_index,
            self.change_pipeline1_choice_index_signal,
            self,
        )
        self.pipeline1_widget.setFixedWidth(int(self.width() * 0.25))
        self.main_layout.addWidget(self.pipeline1_widget)

        pipeline2_layout = QVBoxLayout()
        pipeline2_layout.addStretch(1)
        info_label = QLabel("第二步\n设置练级")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pipeline2_layout.addWidget(info_label)
        self.pipeline2_combobox = QComboBox()
        for pipeline in self.pipeline_scheme.pipeline2:
            self.pipeline2_combobox.addItem(pipeline.name)
        self.pipeline2_combobox.setCurrentIndex(
            self.pipeline_scheme.pipeline2_choice_index
        )
        pipeline2_layout.addWidget(self.pipeline2_combobox)

        # self.pipeline2_setting_btn = QPushButton("设置")
        # self.pipeline2_setting_btn.clicked.connect(self.pipeline2_setting_btn_clicked)
        # pipeline2_layout.addWidget(self.pipeline2_combobox)
        pipeline2_layout.addStretch(1)
        self.main_layout.addLayout(pipeline2_layout)

        pipeline3_layout = QVBoxLayout()
        pipeline3_layout.addStretch(1)
        info_label = QLabel("第三步\n选择对植物进行怎样的处理")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pipeline3_layout.addWidget(info_label)
        self.pipeline3_combobox = QComboBox()
        for pipeline in self.pipeline_scheme.pipeline3:
            self.pipeline3_combobox.addItem(pipeline.name)
        self.pipeline3_combobox.setCurrentIndex(
            self.pipeline_scheme.pipeline3_choice_index
        )
        pipeline3_layout.addWidget(self.pipeline3_combobox)

        # self.pipeline3_setting_btn = QPushButton("设置")
        # self.pipeline3_setting_btn.clicked.connect(self.pipeline3_setting_btn_clicked)
        # pipeline3_layout.addWidget(self.pipeline3_combobox)
        pipeline3_layout.addStretch(1)
        self.main_layout.addLayout(pipeline3_layout)

        pipeline4_layout = QVBoxLayout()
        pipeline4_layout.addStretch(1)
        info_label = QLabel("第四步\n选择如何最后消耗植物")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pipeline4_layout.addWidget(info_label)
        self.pipeline4_combobox = QComboBox()
        for pipeline in self.pipeline_scheme.pipeline4:
            self.pipeline4_combobox.addItem(pipeline.name)
        self.pipeline4_combobox.setCurrentIndex(
            self.pipeline_scheme.pipeline4_choice_index
        )
        pipeline4_layout.addWidget(self.pipeline4_combobox)

        # self.pipeline4_setting_btn = QPushButton("设置")
        # self.pipeline4_setting_btn.clicked.connect(self.pipeline4_setting_btn_clicked)
        # pipeline4_layout.addWidget(self.pipeline4_combobox)
        pipeline4_layout.addStretch(1)
        self.main_layout.addLayout(pipeline4_layout)

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
            ].setting_widget()
            self.pipeline_setting_widget_layout.addWidget(setting_widget)
        if self.pipeline_list[self.pipeline_choice_index].has_setting_window():
            self.pipeline1_setting_btn.setEnabled(True)
        else:
            self.pipeline1_setting_btn.setDisabled(True)

    def pipeline_setting_btn_clicked(self):
        if self.pipeline_list[self.pipeline_choice_index].has_setting_window():
            self.setting_window = self.pipeline_list[
                self.pipeline_choice_index
            ].setting_window()
            self.setting_window.show()

    def pipeline_combobox_currentIndexChanged(self):
        self.pipeline_choice_index = self.pipeline_combobox.currentIndex()
        self.change_choice_index_signal.emit(self.pipeline_combobox.currentIndex())
        self.refresh()
