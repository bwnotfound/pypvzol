from threading import Thread, Event

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
    QCheckBox,
    QSpinBox,
)
from PyQt6 import QtGui
from PyQt6.QtCore import Qt, pyqtSignal

from ..wrapped import QLabel, WaitEventThread
from ..user import UserSettings


class OpenFubenWindow(QMainWindow):
    open_fuben_finish_signal = pyqtSignal()
    open_fuben_stopped_signal = pyqtSignal()

    def __init__(self, usersettings: UserSettings, parent=None):
        super().__init__(parent=parent)
        self.usersettings = usersettings
        self.interrupt_event = Event()
        self.rest_event = Event()
        self.rest_event.set()
        self.run_thread = None
        self.current_widget = None
        self.open_fuben_finish_signal.connect(self.open_fuben_finish)
        self.open_fuben_stopped_signal.connect(self.open_fuben_stopped)
        self.init_ui()
        self.refresh_world_fuben_level_choice_box()
        self.refresh_ignored_level_list_widget()
        self.refresh_plant_list()
        self.refresh_team_list()

    def init_ui(self):
        self.setWindowTitle("副本开图设置")

        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.7), int(screen_size.height() * 0.6))
        self.move(int(screen_size.width() * 0.15), int(screen_size.height() * 0.2))

        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_layout.setSpacing(3)

        widget2 = QWidget()
        widget2.setMinimumWidth(int(self.width() * 0.2))
        layout2 = QVBoxLayout()
        layout2.addWidget(QLabel("植物列表"))
        self.plant_list = QListWidget()
        self.plant_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        layout2.addWidget(self.plant_list)
        widget2.setLayout(layout2)

        widget3 = QWidget()
        widget3.setMinimumWidth(int(self.width() * 0.10))
        layout3 = QVBoxLayout()
        self.set_plant_team_btn = QPushButton("添加出战植物")
        self.set_plant_team_btn.clicked.connect(self.set_plant_team_btn_clicked)
        layout3.addWidget(self.set_plant_team_btn)
        widget3.setLayout(layout3)

        widget4 = QWidget()
        widget4.setMinimumWidth(int(self.width() * 0.2))
        layout4 = QVBoxLayout()
        self.team_list_widget = QListWidget()
        self.team_list_widget.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection
        )
        self.team_list_widget.itemPressed.connect(self.team_list_widget_item_pressed)
        layout4.addWidget(self.team_list_widget)
        widget4.setLayout(layout4)

        tab_widget = QTabWidget()

        world_fuben_widget = QWidget()
        world_fuben_layout = QVBoxLayout()
        world_fuben_widget.setLayout(world_fuben_layout)
        tab_widget.addTab(world_fuben_widget, "世界副本")

        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        widget.setFixedHeight(int(self.height() * 0.6))
        world_fuben_layout.addWidget(widget)
        layout1 = QHBoxLayout()
        layout.addWidget(QLabel("需要忽略的副本"))
        layout.addLayout(layout1)
        self.world_fuben_layout_choice_box = QComboBox()
        self.world_fuben_layout_choice_box.addItems(
            ["炽热沙漠", "幽静树海", "冰火世界", "死亡峡谷", "荒原驿道"]
        )
        self.world_fuben_layout_choice_box.setCurrentIndex(0)
        self.world_fuben_layout_choice_box.currentIndexChanged.connect(
            self.world_fuben_layer_choice_box_currentIndexChanged
        )
        layout1.addWidget(self.world_fuben_layout_choice_box)
        self.world_fuben_level_choice_box = QComboBox()
        layout1.addWidget(self.world_fuben_level_choice_box)
        layout1 = QHBoxLayout()
        layout.addLayout(layout1)
        refresh_world_fuben_layer_info_btn = QPushButton("刷新副本信息")
        refresh_world_fuben_layer_info_btn.clicked.connect(
            self.refresh_world_fuben_layer_info_btn_clicked
        )
        layout1.addWidget(refresh_world_fuben_layer_info_btn)
        add_to_ignored_level_btn = QPushButton("添加到忽略列表")
        add_to_ignored_level_btn.clicked.connect(self.add_to_ignored_level_btn_clicked)
        layout1.addWidget(add_to_ignored_level_btn)
        self.ignored_level_list_widget = QListWidget()
        self.ignored_level_list_widget.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection
        )
        self.ignored_level_list_widget.itemPressed.connect(
            self.ignored_level_list_widget_item_pressed
        )
        layout.addWidget(self.ignored_level_list_widget)

        layout = QHBoxLayout()
        self.world_fuben_max_pool_size = QComboBox()
        self.world_fuben_max_pool_size.addItems([str(i) for i in range(1, 21)])
        self.world_fuben_max_pool_size.setCurrentIndex(
            self.usersettings.open_fuben_man.max_pool_size - 1
        )
        self.world_fuben_max_pool_size.currentIndexChanged.connect(
            self.world_fuben_max_pool_size_currentIndexChanged
        )
        layout.addWidget(QLabel("并发数："))
        layout.addWidget(self.world_fuben_max_pool_size)
        world_fuben_layout.addLayout(layout)

        layout = QHBoxLayout()
        self.world_fuben_min_challenge_amount = QComboBox()
        self.world_fuben_min_challenge_amount.addItems([str(i) for i in range(1, 21)])
        self.world_fuben_min_challenge_amount.setCurrentIndex(
            self.usersettings.open_fuben_man.min_challenge_amount - 1
        )
        self.world_fuben_min_challenge_amount.currentIndexChanged.connect(
            self.world_fuben_min_challenge_amount_currentIndexChanged
        )
        layout.addWidget(QLabel("每批最少挑战次数："))
        layout.addWidget(self.world_fuben_min_challenge_amount)
        world_fuben_layout.addLayout(layout)

        layout = QHBoxLayout()
        world_fuben_layout.addLayout(layout)
        self.need_recover_checkbox = QCheckBox("需要回复")
        self.need_recover_checkbox.setChecked(
            self.usersettings.open_fuben_man.need_recover
        )
        self.need_recover_checkbox.stateChanged.connect(
            self.need_recover_checkbox_stateChanged
        )
        layout.addWidget(self.need_recover_checkbox)
        layout1 = QHBoxLayout()
        layout1.addStretch(1)
        # 创建正浮点数输入框，要求值在0~100之间
        self.recover_threshold_input = QSpinBox()
        self.recover_threshold_input.setMinimum(0)
        self.recover_threshold_input.setMaximum(99)
        self.recover_threshold_input.setValue(
            int(self.usersettings.open_fuben_man.recover_threshold * 100)
        )
        self.recover_threshold_input.valueChanged.connect(
            self.recover_threshold_input_valueChanged
        )
        layout1.addWidget(self.recover_threshold_input)
        layout1.addWidget(QLabel("%"))
        layout1.addStretch(1)
        layout.addLayout(layout1)
        self.recover_choice_box = QComboBox()
        recover_choice_list = ["低级血瓶", "中级血瓶", "高级血瓶"]
        self.recover_choice_box.addItems(recover_choice_list)
        self.recover_choice_box.setCurrentIndex(
            recover_choice_list.index(self.usersettings.open_fuben_man.recover_choice)
        )
        self.recover_choice_box.currentIndexChanged.connect(
            self.recover_choice_box_currentIndexChanged
        )
        layout.addWidget(self.recover_choice_box)

        self.world_fuben_start_btn = QPushButton("开始")
        self.world_fuben_start_btn.clicked.connect(self.wrold_fuben_start_btn_clicked)
        world_fuben_layout.addWidget(self.world_fuben_start_btn)

        main_layout.addWidget(widget2)
        main_layout.addWidget(widget3)
        main_layout.addWidget(widget4)
        main_layout.addWidget(tab_widget)
        main_widget.setLayout(main_layout)

        self.setCentralWidget(main_widget)

    def format_plant_info(self, plant):
        if isinstance(plant, str):
            plant = int(plant)
        if isinstance(plant, int):
            plant = self.usersettings.repo.get_plant(plant)
        msg = "{}({})[{}]".format(
            plant.name(self.usersettings.lib),
            plant.grade,
            plant.quality_str,
            self.usersettings.lib.get_spec_skill(plant.special_skill_id),
        )
        if plant.special_skill_id is not None:
            spec_skill = self.usersettings.lib.get_spec_skill(plant.special_skill_id)
            msg += " 专属:{}({}级)".format(spec_skill["name"], spec_skill['grade'])
        return msg
    
    def need_recover_checkbox_stateChanged(self):
        self.usersettings.open_fuben_man.need_recover = self.need_recover_checkbox.isChecked()
    
    def recover_threshold_input_valueChanged(self, value):
        self.usersettings.open_fuben_man.recover_threshold = value / 100
    
    def recover_choice_box_currentIndexChanged(self):
        text = self.recover_choice_box.currentText()
        self.usersettings.open_fuben_man.recover_choice = text

    def team_list_widget_item_pressed(self):
        self.current_widget = self.team_list_widget

    def ignored_level_list_widget_item_pressed(self):
        self.current_widget = self.ignored_level_list_widget

    def world_fuben_layer_choice_box_currentIndexChanged(self):
        self.refresh_world_fuben_level_choice_box()

    def refresh_world_fuben_level_choice_box(self):
        current_layer_index = self.world_fuben_layout_choice_box.currentIndex()
        self.world_fuben_level_choice_box.clear()
        fuben_layer_info = self.usersettings.open_fuben_man.fuben_layer_info_list[
            current_layer_index
        ]
        if fuben_layer_info is None:
            return
        for cave in fuben_layer_info:
            self.world_fuben_level_choice_box.addItem(str(cave.name), cave)
        self.world_fuben_level_choice_box.setCurrentIndex(0)

    def refresh_world_fuben_layer_info_btn_clicked(self):
        self.usersettings.open_fuben_man.refresh_fuben_info()
        self.refresh_world_fuben_level_choice_box()

    def add_to_ignored_level_btn_clicked(self):
        cave = self.world_fuben_level_choice_box.currentData()
        if cave is None:
            self.usersettings.logger.log("未选择副本")
            return
        for c in self.usersettings.open_fuben_man.ignored_cave_list:
            if c.cave_id == cave.cave_id:
                break
        else:
            self.usersettings.open_fuben_man.ignored_cave_list.append(cave)
            self.refresh_ignored_level_list_widget()
            return
        self.usersettings.logger.log("世界副本{}已经在忽略列表中".format(cave.name))

    def refresh_ignored_level_list_widget(self):
        self.ignored_level_list_widget.clear()
        for cave in self.usersettings.open_fuben_man.ignored_cave_list:
            item = QListWidgetItem()
            item.setText(cave.name)
            item.setData(Qt.ItemDataRole.UserRole, cave)
            self.ignored_level_list_widget.addItem(item)

    def world_fuben_max_pool_size_currentIndexChanged(self, index):
        self.usersettings.open_fuben_man.max_pool_size = index + 1

    def world_fuben_min_challenge_amount_currentIndexChanged(self, index):
        self.usersettings.open_fuben_man.min_challenge_amount = index + 1

    def refresh_plant_list(self):
        self.plant_list.clear()
        for plant in self.usersettings.repo.plants:
            if plant.id in self.usersettings.open_fuben_man.team:
                continue
            item = QListWidgetItem(self.format_plant_info(plant))
            item.setData(Qt.ItemDataRole.UserRole, plant.id)
            self.plant_list.addItem(item)

    def refresh_team_list(self):
        self.team_list_widget.clear()
        for plant_id in self.usersettings.open_fuben_man.team:
            plant = self.usersettings.repo.get_plant(plant_id)
            if plant is None:
                continue
            item = QListWidgetItem(self.format_plant_info(plant))
            item.setData(Qt.ItemDataRole.UserRole, plant.id)
            self.team_list_widget.addItem(item)

    def set_plant_team_btn_clicked(self):
        self.usersettings.open_fuben_man.team.extend(
            [
                item.data(Qt.ItemDataRole.UserRole)
                for item in self.plant_list.selectedItems()
            ]
        )
        self.refresh_team_list()
        self.refresh_plant_list()

    def open_fuben_finish(self):
        self.run_thread = None
        self.interrupt_event.clear()
        self.world_fuben_start_btn.setText("开始")

    def open_fuben_stopped(self):
        self.world_fuben_start_btn.setText("开始")
        self.world_fuben_start_btn.setEnabled(True)

    def wrold_fuben_start_btn_clicked(self):
        self.world_fuben_start_btn.setDisabled(True)
        QApplication.processEvents()
        if self.world_fuben_start_btn.text() == "开始":
            try:
                if len(self.usersettings.open_fuben_man.team) == 0:
                    self.usersettings.logger.log("未设置出战植物")
                    return
                self.world_fuben_start_btn.setText("暂停")
                self.run_thread = OpenFubenThread(
                    self.usersettings,
                    self.open_fuben_finish_signal,
                    self.interrupt_event,
                    self.rest_event,
                )
                self.rest_event.clear()
                self.run_thread.start()
            finally:
                self.world_fuben_start_btn.setEnabled(True)
        elif self.world_fuben_start_btn.text() == "暂停":
            self.interrupt_event.set()
            WaitEventThread(self.rest_event, self.open_fuben_stopped_signal).start()
        else:
            self.world_fuben_start_btn.setEnabled(True)
            raise RuntimeError(f"未知按钮文本：{self.world_fuben_start_btn.text()}")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Backspace or event.key() == Qt.Key.Key_Delete:
            if self.current_widget is self.team_list_widget:
                items = [
                    item.data(Qt.ItemDataRole.UserRole)
                    for item in self.team_list_widget.selectedItems()
                ]
                self.usersettings.open_fuben_man.team = [
                    plant_id
                    for plant_id in self.usersettings.open_fuben_man.team
                    if plant_id not in items
                ]
                self.refresh_team_list()
                self.refresh_plant_list()
            elif self.current_widget is self.ignored_level_list_widget:
                items = [
                    item.data(Qt.ItemDataRole.UserRole)
                    for item in self.ignored_level_list_widget.selectedItems()
                ]
                cave_id_set = set()
                for cave in items:
                    cave_id_set.add(cave.cave_id)
                self.usersettings.open_fuben_man.ignored_cave_list = [
                    cave
                    for cave in self.usersettings.open_fuben_man.ignored_cave_list
                    if cave.cave_id not in cave_id_set
                ]
                self.refresh_ignored_level_list_widget()


class OpenFubenThread(Thread):
    def __init__(
        self,
        usersettings: UserSettings,
        open_fuben_finish_signal,
        interrupt_event: Event,
        rest_event: Event,
    ):
        super().__init__()
        self.usersettings = usersettings
        self.open_fuben_finish_signal = open_fuben_finish_signal
        self.interrupt_event = interrupt_event
        self.rest_event = rest_event

    def run(self):
        try:
            self.usersettings.open_fuben_man.start_world_fuben(self.interrupt_event)
        finally:
            self.open_fuben_finish_signal.emit()
            self.rest_event.set()
