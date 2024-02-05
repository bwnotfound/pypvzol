from time import sleep
from threading import Event
import typing
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


class RepositoryRecordWindow(QMainWindow):
    def __init__(self, usersettings: UserSettings, parent=None):
        super().__init__(parent)
        self.usersettings = usersettings
        self.init_ui()
        self.refresh_repository_list()
        self.refresh_record_list()
        self.refresh_record_ignore_tool_list()

    def init_ui(self):
        self.setWindowTitle("仓库记录")

        # 将窗口居中显示，宽度为显示器宽度的50%，高度为显示器高度的50%
        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.5), int(screen_size.height() * 0.5))
        self.move(int(screen_size.width() * 0.25), int(screen_size.height() * 0.25))

        main_widget = QWidget()
        main_layout = QHBoxLayout()

        widget1 = QWidget()
        widget1.setMinimumWidth(int(self.width() * 0.27))
        layout1 = QVBoxLayout()
        layout1.addWidget(QLabel("仓库物品"))
        self.repository_list = QListWidget()
        self.repository_list.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection
        )
        layout1.addWidget(self.repository_list)
        widget1.setLayout(layout1)
        main_layout.addWidget(widget1)

        widget2 = QWidget()
        widget2.setMinimumWidth(int(self.width() * 0.27))
        layout2 = QVBoxLayout()
        layout2.addWidget(QLabel("记录结果（改变量）"))
        self.record_list = QListWidget()
        self.record_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        layout2.addWidget(self.record_list)
        widget2.setLayout(layout2)
        main_layout.addWidget(widget2)

        widget3 = QWidget()
        widget3.setMinimumWidth(int(self.width() * 0.27))
        layout3 = QVBoxLayout()
        layout3.addWidget(QLabel("屏蔽物品列表"))
        self.record_ignore_tool_list = QListWidget()
        self.record_ignore_tool_list.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection
        )
        layout3.addWidget(self.record_ignore_tool_list)
        widget3.setLayout(layout3)
        main_layout.addWidget(widget3)

        widget4 = QWidget()
        widget4.setMinimumWidth(int(self.width() * 0.16))
        layout4 = QVBoxLayout()
        layout4.addStretch(1)
        self.set_record_point_btn = QPushButton("设置记录点")
        self.set_record_point_btn.clicked.connect(self.set_record_point_btn_clicked)
        layout4.addWidget(self.set_record_point_btn)
        self.refresh_repository_btn = QPushButton("刷新仓库")
        self.refresh_repository_btn.clicked.connect(self.refresh_repository_btn_clicked)
        layout4.addWidget(self.refresh_repository_btn)
        self.set_record_ignore_tool_btn = QPushButton("设置为屏蔽物品")
        self.set_record_ignore_tool_btn.clicked.connect(
            self.set_record_ignore_tool_btn_clicked
        )
        layout4.addWidget(self.set_record_ignore_tool_btn)
        layout4.addStretch(1)
        widget4.setLayout(layout4)
        main_layout.addWidget(widget4)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def refresh_record_ignore_tool_list(self):
        self.record_ignore_tool_list.clear()
        for tool_id in self.usersettings.record_ignore_tool_id_set:
            item = QListWidgetItem(self.usersettings.lib.get_tool_by_id(tool_id).name)
            item.setData(Qt.ItemDataRole.UserRole, tool_id)
            self.record_ignore_tool_list.addItem(item)

    def refresh_repository_list(self):
        self.repository_list.clear()
        for tool in self.usersettings.repo.tools:
            item = QListWidgetItem(
                "{}({})".format(
                    self.usersettings.lib.get_tool_by_id(tool['id']).name,
                    tool['amount'],
                )
            )
            item.setData(Qt.ItemDataRole.UserRole, tool['id'])
            self.repository_list.addItem(item)

    def refresh_record_list(self):
        self.record_list.clear()
        exist_tool_dict = {
            k: False for k in self.usersettings.record_repository_tool_dict.keys()
        }
        delta_tool_list = []
        for tool in self.usersettings.repo.tools:
            if tool['id'] not in self.usersettings.record_repository_tool_dict:
                delta_tool_list.append((tool['id'], tool['amount']))
            else:
                exist_tool_dict[tool['id']] = True
                if (
                    tool['amount']
                    != self.usersettings.record_repository_tool_dict[tool['id']]
                ):
                    delta_tool_list.append(
                        (
                            tool['id'],
                            tool['amount']
                            - self.usersettings.record_repository_tool_dict[tool['id']],
                        )
                    )
        for k, v in exist_tool_dict.items():
            if not v:
                delta_tool_list.append(
                    (k, -self.usersettings.record_repository_tool_dict[k])
                )
        delta_tool_list = list(
            filter(
                lambda x: x[0] not in self.usersettings.record_ignore_tool_id_set,
                delta_tool_list,
            )
        )
        for tool in delta_tool_list:
            item = QListWidgetItem(
                "{}({})".format(
                    self.usersettings.lib.get_tool_by_id(tool[0]).name,
                    tool[1],
                )
            )
            item.setData(Qt.ItemDataRole.UserRole, tool[0])
            self.record_list.addItem(item)

    def set_record_point_btn_clicked(self):
        try:
            self.set_record_point_btn.setDisabled(True)
            QApplication.processEvents()
            self.usersettings.record_repository_tool_dict = {
                tool['id']: tool['amount'] for tool in self.usersettings.repo.tools
            }
            self.refresh_record_list()
        finally:
            self.set_record_point_btn.setEnabled(True)

    def refresh_repository_btn_clicked(self):
        try:
            self.refresh_repository_btn.setDisabled(True)
            QApplication.processEvents()
            self.usersettings.repo.refresh_repository()
            self.refresh_repository_list()
            self.refresh_record_list()
        finally:
            self.refresh_repository_btn.setEnabled(True)

    def set_record_ignore_tool_btn_clicked(self):
        try:
            self.set_record_ignore_tool_btn.setDisabled(True)
            QApplication.processEvents()
            for item in self.record_list.selectedItems():
                self.usersettings.record_ignore_tool_id_set.add(
                    item.data(Qt.ItemDataRole.UserRole)
                )
            self.refresh_record_list()
            self.refresh_record_ignore_tool_list()
        finally:
            self.set_record_ignore_tool_btn.setEnabled(True)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Backspace or event.key() == Qt.Key.Key_Delete:
            for item in self.record_ignore_tool_list.selectedItems():
                tool_id = item.data(Qt.ItemDataRole.UserRole)
                if tool_id in self.usersettings.record_ignore_tool_id_set:
                    self.usersettings.record_ignore_tool_id_set.remove(tool_id)
            self.refresh_record_ignore_tool_list()
            self.refresh_record_list()
