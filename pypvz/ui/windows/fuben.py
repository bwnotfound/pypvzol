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
)
from PyQt6 import QtGui
from PyQt6.QtCore import Qt, pyqtSignal

from ..wrapped import QLabel
from ..user import UserSettings
from ...utils.common import format_plant_info


class FubenSelectWindow(QMainWindow):
    def __init__(
        self, usersettings: UserSettings, refresh_signal: pyqtSignal, parent=None
    ):
        super().__init__(parent)
        self.usersettings = usersettings
        self.refresh_signal = refresh_signal
        self.fuben_layer_cache = {}
        self.usersettings.fuben_man.switch_fuben_layer(1)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("练级设置")

        # 将窗口居中显示，宽度为显示器宽度的30%，高度为显示器高度的50%
        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.4), int(screen_size.height() * 0.5))
        self.move(int(screen_size.width() * 0.3), int(screen_size.height() * 0.25))

        main_widget = QWidget()
        main_layout = QHBoxLayout()

        cave_type_widget = QWidget()
        cave_type_widget.setFixedWidth(int(self.width() * 0.4))
        cave_type_layout = QVBoxLayout()
        cave_type_layout.addWidget(QLabel("副本层级"))
        self.cave_type_list_widget = QListWidget()
        cave_type_layout.addWidget(self.cave_type_list_widget)
        cave_type_widget.setLayout(cave_type_layout)
        self.cave_type_list_widget.itemClicked.connect(
            self.cave_type_list_widget_clicked
        )
        for i, name in enumerate(
            ["炽热沙漠", "幽静树海", "冰火世界", "死亡峡谷", "荒原驿道"]
        ):
            item = QListWidgetItem("{}".format(name))
            item.setData(Qt.ItemDataRole.UserRole, i + 1)
            self.cave_type_list_widget.addItem(item)
        main_layout.addWidget(cave_type_widget)

        cave_widget = QWidget()
        cave_widget.setFixedWidth(int(self.width() * 0.4))
        cave_layout = QVBoxLayout()
        cave_layout.addWidget(QLabel("洞口"))
        self.cave_list_widget = QListWidget()
        self.cave_list_widget.itemClicked.connect(self.cave_list_widget_clicked)
        cave_layout.addWidget(self.cave_list_widget)
        cave_widget.setLayout(cave_layout)
        main_layout.addWidget(cave_widget)

        switch_fuben_layer_widget = QWidget()
        switch_fuben_layer_widget.setFixedWidth(int(self.width() * 0.2))
        switch_fuben_layer_layout = QVBoxLayout()
        switch_fuben_layer_layout.addStretch(1)
        switch_fuben_layer_layout.addWidget(QLabel("切换副本层级"))
        self.switch_fuben_layer_combobox = QComboBox()
        self.switch_fuben_layer_combobox.addItems(["第一层", "第二层"])
        self.switch_fuben_layer_combobox.setCurrentIndex(
            self.usersettings.fuben_man.current_fuben_layer - 1
        )
        self.switch_fuben_layer_combobox.currentIndexChanged.connect(
            self.switch_fuben_layer_combobox_index_changed
        )
        switch_fuben_layer_layout.addWidget(self.switch_fuben_layer_combobox)
        switch_fuben_layer_layout.addStretch(1)
        switch_fuben_layer_widget.setLayout(switch_fuben_layer_layout)
        main_layout.addWidget(switch_fuben_layer_widget)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def switch_fuben_layer_combobox_index_changed(self):
        layer = self.switch_fuben_layer_combobox.currentIndex() + 1
        self.usersettings.fuben_man.switch_fuben_layer(layer)
        self.refresh_cave_list()

    def refresh_cave_list(self):
        layer = self.cave_type_list_widget.currentItem().data(Qt.ItemDataRole.UserRole)
        global_layer = self.usersettings.fuben_man.current_fuben_layer
        fuben_layer_cache = self.fuben_layer_cache.get(global_layer, None)
        if fuben_layer_cache is None:
            self.fuben_layer_cache[global_layer] = {}
            fuben_layer_cache = self.fuben_layer_cache[global_layer]
        if fuben_layer_cache.get(layer, None) is None:
            caves = self.usersettings.fuben_man.get_caves(layer)
            fuben_layer_cache[layer] = caves
        else:
            caves = fuben_layer_cache[layer]
        self.cave_list_widget.clear()
        for i, cave in enumerate(caves):
            item = QListWidgetItem(
                cave.format_info(lib=self.usersettings.lib, show_reward=True)
            )
            item.setData(Qt.ItemDataRole.UserRole, (global_layer, cave, layer, i + 1))
            self.cave_list_widget.addItem(item)

    def cave_type_list_widget_clicked(self):
        self.refresh_cave_list()

    def cave_list_widget_clicked(self, item):
        global_layer, cave, layer, number = item.data(Qt.ItemDataRole.UserRole)
        self.usersettings.fuben_man.add_cave(
            cave, layer, number, global_layer=global_layer
        )
        self.refresh_signal.emit()


class FubenSettingWindow(QMainWindow):
    refresh_signal = pyqtSignal()

    def __init__(self, usersettings: UserSettings, parent=None):
        super().__init__(parent=parent)
        self.usersettings = usersettings
        self.last_focus_list_widget = None
        self.init_ui()
        self.refresh_cave_list()
        self.refresh_plant_list()
        self.refresh_team_list()
        self.refresh_signal.connect(self.refresh_cave_list)

    def init_ui(self):
        self.setWindowTitle("副本挑战设置")

        # 将窗口居中显示，宽度为显示器宽度的30%，高度为显示器高度的50%
        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.7), int(screen_size.height() * 0.5))
        self.move(int(screen_size.width() * 0.15), int(screen_size.height() * 0.25))

        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_layout.setSpacing(3)

        widget1 = QWidget()
        widget1.setMinimumWidth(int(self.width() * 0.2))
        layout1 = QVBoxLayout()
        layout1_1 = QHBoxLayout()
        layout1_1.addWidget(QLabel("副本洞口"))
        self.add_fuben_button = QPushButton("添加洞口")
        self.add_fuben_button.clicked.connect(self.add_fuben_button_clicked)
        layout1_1.addWidget(self.add_fuben_button)
        layout1.addLayout(layout1_1)
        self.fuben_list_widget = QListWidget()
        self.fuben_list_widget.itemClicked.connect(self.fuben_list_widget_clicked)
        self.fuben_list_widget.setSelectionMode(
            QListWidget.SelectionMode.SingleSelection
        )
        layout1.addWidget(self.fuben_list_widget)
        widget1.setLayout(layout1)

        widget2 = QWidget()
        widget2.setMinimumWidth(int(self.width() * 0.25))
        layout2 = QVBoxLayout()
        layout2.addWidget(QLabel("植物列表"))
        self.plant_list = QListWidget()
        self.plant_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        layout2.addWidget(self.plant_list)
        widget2.setLayout(layout2)

        widget3 = QWidget()
        widget3.setMinimumWidth(int(self.width() * 0.1))
        layout3 = QVBoxLayout()
        self.set_plant_team_btn = QPushButton("添加出战植物")
        self.set_plant_team_btn.clicked.connect(self.set_plant_team_btn_clicked)
        layout3.addWidget(self.set_plant_team_btn)
        widget3.setLayout(layout3)

        widget4 = QWidget()
        widget4.setMinimumWidth(int(self.width() * 0.25))
        layout4 = QVBoxLayout()
        self.team_list_widget = QListWidget()
        self.team_list_widget.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection
        )
        self.team_list_widget.itemPressed.connect(self.team_list_widget_pressed)
        layout4.addWidget(self.team_list_widget)
        widget4.setLayout(layout4)

        widget5 = QWidget()
        widget5.setMinimumWidth(int(self.width() * 0.2))
        layout5 = QVBoxLayout()
        layout5.addStretch(1)
        self.need_recovery_checkbox = QCheckBox("是否需要恢复:")
        self.need_recovery_checkbox.stateChanged.connect(
            self.need_recovery_checkbox_state_changed
        )
        self.need_recovery_checkbox.setChecked(
            self.usersettings.fuben_man.need_recovery
        )
        layout5.addWidget(self.need_recovery_checkbox)
        self.recovery_combo = QComboBox()
        self.recovery_combo.addItems(["低级血瓶", "中级血瓶", "高级血瓶"])
        self.recovery_combo.currentIndexChanged.connect(
            self.recovery_combo_index_changed
        )
        self.recovery_combo.setCurrentText(
            self.usersettings.fuben_man.recover_hp_choice
        )
        layout5.addWidget(self.recovery_combo)
        self.use_fuben_book_enabled_checkbox = QCheckBox("是否自动使用副本书:")
        self.use_fuben_book_enabled_checkbox.setChecked(
            self.usersettings.fuben_man.use_fuben_book_enabled
        )
        self.use_fuben_book_enabled_checkbox.stateChanged.connect(
            self.use_fuben_book_enabled_checkbox_state_changed
        )
        layout5.addWidget(self.use_fuben_book_enabled_checkbox)
        layout = QHBoxLayout()
        layout.addWidget(QLabel("并发数:"))
        self.pool_size_combobox = QComboBox()
        self.pool_size_combobox.addItems([str(i) for i in range(1, 21)])
        self.pool_size_combobox.setCurrentIndex(
            self.usersettings.fuben_man.pool_size - 1
        )
        self.pool_size_combobox.currentIndexChanged.connect(
            self.pool_size_combobox_index_changed
        )
        layout.addWidget(self.pool_size_combobox)
        layout5.addLayout(layout)
        layout5.addStretch(1)
        widget5.setLayout(layout5)

        main_layout.addWidget(widget1)
        main_layout.addWidget(widget2)
        main_layout.addWidget(widget3)
        main_layout.addWidget(widget4)
        main_layout.addWidget(widget5)
        main_widget.setLayout(main_layout)

        self.setCentralWidget(main_widget)

    def use_fuben_book_enabled_checkbox_state_changed(self):
        self.usersettings.fuben_man.use_fuben_book_enabled = (
            self.use_fuben_book_enabled_checkbox.isChecked()
        )

    def pool_size_combobox_index_changed(self):
        self.usersettings.fuben_man.pool_size = (
            self.pool_size_combobox.currentIndex() + 1
        )

    def need_recovery_checkbox_state_changed(self):
        self.usersettings.fuben_man.need_recovery = (
            self.need_recovery_checkbox.isChecked()
        )

    def recovery_combo_index_changed(self):
        self.usersettings.fuben_man.recover_hp_choice = (
            self.recovery_combo.currentText()
        )

    def format_plant_info(self, plant):
        return format_plant_info(plant, self.usersettings.lib)

    def refresh_plant_list(self):
        self.plant_list.clear()
        for plant in self.usersettings.repo.plants:
            if plant.id in self.usersettings.fuben_man.team:
                continue
            item = QListWidgetItem(self.format_plant_info(plant))
            item.setData(Qt.ItemDataRole.UserRole, plant.id)
            self.plant_list.addItem(item)

    def refresh_cave_list(self):
        self.fuben_list_widget.clear()
        for sc in self.usersettings.fuben_man.caves:
            item = QListWidgetItem(
                sc.cave.format_info(lib=self.usersettings.lib, show_reward=True)
            )
            item.setData(Qt.ItemDataRole.UserRole, sc)
            self.fuben_list_widget.addItem(item)

    def refresh_team_list(self):
        self.team_list_widget.clear()
        for plant_id in self.usersettings.fuben_man.team:
            plant = self.usersettings.repo.get_plant(plant_id)
            if plant is None:
                continue
            item = QListWidgetItem(self.format_plant_info(plant))
            item.setData(Qt.ItemDataRole.UserRole, plant.id)
            self.team_list_widget.addItem(item)

    def fuben_list_widget_clicked(self):
        self.last_focus_list_widget = self.fuben_list_widget

    def add_fuben_button_clicked(self):
        self.fuben_select_window = FubenSelectWindow(
            self.usersettings, self.refresh_signal, self
        )
        self.fuben_select_window.show()

    def set_plant_team_btn_clicked(self):
        self.usersettings.fuben_man.team.extend(
            [
                item.data(Qt.ItemDataRole.UserRole)
                for item in self.plant_list.selectedItems()
            ]
        )
        self.refresh_team_list()
        self.refresh_plant_list()

    def team_list_widget_pressed(self):
        self.last_focus_list_widget = self.team_list_widget

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Backspace or event.key() == Qt.Key.Key_Delete:
            if self.last_focus_list_widget is None:
                return
            items = [
                item.data(Qt.ItemDataRole.UserRole)
                for item in self.last_focus_list_widget.selectedItems()
            ]
            if self.last_focus_list_widget is self.fuben_list_widget:
                for sc in items:
                    self.usersettings.fuben_man.delete_cave(sc)
                self.refresh_cave_list()
            elif self.last_focus_list_widget is self.team_list_widget:
                self.usersettings.fuben_man.team = [
                    plant_id
                    for plant_id in self.usersettings.fuben_man.team
                    if plant_id not in items
                ]
                self.refresh_team_list()
                self.refresh_plant_list()
