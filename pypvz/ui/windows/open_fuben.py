from threading import Thread, Event
from PyQt6.QtGui import QKeyEvent

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
from ..message import Logger
from ..user import UserSettings
from ... import WebRequest, Repository
from ...utils.recover import RecoverMan


class OpenFubenWindow(QMainWindow):
    open_fuben_finish_signal = pyqtSignal()
    open_fuben_stopped_signal = pyqtSignal()
    stone_fuben_finish_signal = pyqtSignal()
    stone_fuben_stopped_signal = pyqtSignal()

    def __init__(self, usersettings: UserSettings, parent=None):
        super().__init__(parent=parent)
        self.usersettings = usersettings
        self.world_fuben_interrupt_event = Event()
        self.world_fuben_rest_event = Event()
        self.world_fuben_rest_event.set()
        self.stone_fuben_interrupt_event = Event()
        self.stone_fuben_rest_event = Event()
        self.stone_fuben_rest_event.set()
        self.world_fuben_run_thread = None
        self.stone_fuben_run_thread = None
        self.current_widget = None
        self.open_fuben_finish_signal.connect(self.open_fuben_finish)
        self.open_fuben_stopped_signal.connect(self.open_fuben_stopped)
        self.stone_fuben_finish_signal.connect(self.stone_fuben_finish)
        self.stone_fuben_stopped_signal.connect(self.stone_fuben_stopped)
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
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        main_layout.setSpacing(3)

        widget2 = QWidget()
        widget2.setMinimumWidth(int(self.width() * 0.2))
        layout2 = QVBoxLayout()
        layout2.addWidget(QLabel("植物列表"))
        self.plant_list = QListWidget()
        self.plant_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        layout2.addWidget(self.plant_list)
        widget2.setLayout(layout2)
        main_layout.addWidget(widget2)

        widget3 = QWidget()
        widget3.setMinimumWidth(int(self.width() * 0.10))
        layout3 = QVBoxLayout()
        self.set_plant_team_btn = QPushButton("添加出战植物")
        self.set_plant_team_btn.clicked.connect(self.set_plant_team_btn_clicked)
        layout3.addWidget(self.set_plant_team_btn)
        widget3.setLayout(layout3)
        main_layout.addWidget(widget3)

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
        main_layout.addWidget(widget4)

        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)

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
        self.world_fuben_start_btn.clicked.connect(self.world_fuben_start_btn_clicked)
        world_fuben_layout.addWidget(self.world_fuben_start_btn)

        stone_fuben_widget = QWidget()
        stone_fuben_layout = QVBoxLayout()
        stone_fuben_widget.setLayout(stone_fuben_layout)
        tab_widget.addTab(stone_fuben_widget, "宝石副本")
        stone_fuben_layout.addStretch(1)

        # 将label居中显示
        label = QLabel(
            "---------注意---------\n"
            "该功能用于打三星宝石关\n"
            "原理是挑战设定的起始关到终止关\n"
            "挑战失败后会自动回复并继续挑战\n"
            "挑战成功一关后会自动挑战下一关\n"
            "直到选中的关卡都被挑战通过"
        )
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stone_fuben_layout.addWidget(label)
        layout = QHBoxLayout()
        stone_fuben_layout.addLayout(layout)
        layout.addWidget(QLabel("起始层:"))
        self.start_layer = QComboBox()
        self.start_layer.addItems([str(i) for i in range(1, 9 + 1)])
        self.start_layer.setCurrentIndex(0)
        layout.addWidget(self.start_layer)
        layout.addWidget(QLabel("终点层:"))
        self.end_layer = QComboBox()
        self.end_layer.addItems([str(i) for i in range(1, 9 + 1)])
        self.end_layer.setCurrentIndex(0)
        layout.addWidget(self.end_layer)
        layout = QHBoxLayout()
        stone_fuben_layout.addLayout(layout)
        layout.addWidget(QLabel("起始关:"))
        self.start_level = QComboBox()
        self.start_level.addItems([str(i) for i in range(1, 36 + 1)])
        self.start_level.setCurrentIndex(0)
        layout.addWidget(self.start_level)
        layout.addWidget(QLabel("终点关:"))
        self.end_level = QComboBox()
        self.end_level.addItems([str(i) for i in range(1, 36 + 1)])
        self.end_level.setCurrentIndex(0)
        layout.addWidget(self.end_level)

        self.need_recover_checkbox = QCheckBox("需要回复")
        self.need_recover_checkbox.setChecked(True)
        layout.addWidget(self.need_recover_checkbox)
        layout1 = QHBoxLayout()
        layout1.addStretch(1)
        # 创建正浮点数输入框，要求值在0~100之间
        self.recover_threshold_input = QSpinBox()
        self.recover_threshold_input.setMinimum(0)
        self.recover_threshold_input.setMaximum(99)
        self.recover_threshold_input.setValue(0)
        self.recover_threshold_input.valueChanged.connect(
            self.recover_threshold_input_valueChanged
        )
        layout1.addWidget(self.recover_threshold_input)
        layout1.addWidget(QLabel("%"))
        layout1.addStretch(1)
        layout.addLayout(layout1)

        self.stone_fuben_start_btn = QPushButton("开始")
        self.stone_fuben_start_btn.clicked.connect(self.stone_fuben_start_btn_clicked)
        stone_fuben_layout.addWidget(self.stone_fuben_start_btn)

        stone_fuben_layout.addStretch(1)

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
        self.usersettings.open_fuben_man.need_recover = (
            self.need_recover_checkbox.isChecked()
        )

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
        self.world_fuben_run_thread = None
        self.world_fuben_interrupt_event.clear()
        self.world_fuben_start_btn.setText("开始")

    def open_fuben_stopped(self):
        self.world_fuben_start_btn.setText("开始")
        self.world_fuben_start_btn.setEnabled(True)

    def stone_fuben_finish(self):
        self.stone_fuben_run_thread = None
        self.stone_fuben_interrupt_event.clear()
        self.stone_fuben_start_btn.setText("开始")

    def stone_fuben_stopped(self):
        self.stone_fuben_start_btn.setText("开始")
        self.stone_fuben_start_btn.setEnabled(True)

    def world_fuben_start_btn_clicked(self):
        self.world_fuben_start_btn.setDisabled(True)
        QApplication.processEvents()
        if self.world_fuben_start_btn.text() == "开始":
            try:
                if len(self.usersettings.open_fuben_man.team) == 0:
                    self.usersettings.logger.log("未设置出战植物")
                    return
                self.world_fuben_start_btn.setText("暂停")
                self.world_fuben_run_thread = OpenFubenThread(
                    self.usersettings,
                    self.open_fuben_finish_signal,
                    self.world_fuben_interrupt_event,
                    self.world_fuben_rest_event,
                )
                self.world_fuben_interrupt_event.clear()
                self.world_fuben_rest_event.clear()
                self.world_fuben_run_thread.start()
            finally:
                self.world_fuben_start_btn.setEnabled(True)
        elif self.world_fuben_start_btn.text() == "暂停":
            self.world_fuben_interrupt_event.set()
            WaitEventThread(
                self.world_fuben_rest_event, self.open_fuben_stopped_signal
            ).start()
        else:
            self.world_fuben_start_btn.setEnabled(True)
            raise RuntimeError(f"未知按钮文本：{self.world_fuben_start_btn.text()}")

    def stone_fuben_start_btn_clicked(self):
        self.stone_fuben_start_btn.setDisabled(True)
        QApplication.processEvents()
        if self.stone_fuben_start_btn.text() == "开始":
            try:
                if len(self.usersettings.open_fuben_man.team) == 0:
                    self.usersettings.logger.log("未设置出战植物")
                    return
                start_layer, end_layer = (
                    int(self.start_layer.currentText()),
                    int(self.end_layer.currentText()),
                )
                if end_layer < start_layer:
                    self.usersettings.logger.log("终点层数小于起始层数")
                    return
                start_level, end_level = (
                    int(self.start_level.currentText()),
                    int(self.end_level.currentText()),
                )
                if end_level < start_level:
                    self.usersettings.logger.log("终点关卡小于起始关卡")
                    return
                challenge_list = [
                    (layer, level, 3)
                    for layer in range(start_layer, end_layer + 1)
                    for level in range(start_level, end_level + 1)
                ]
                if len(challenge_list) == 0:
                    self.usersettings.logger.log("挑战列表为空")
                    return
                self.stone_fuben_start_btn.setText("暂停")
                recover_threshold = (
                    self.recover_threshold_input.value() / 100
                    if self.need_recover_checkbox.isChecked()
                    else None
                )
                self.stone_fuben_run_thread = StoneChallengeThread(
                    self.usersettings.cfg,
                    self.usersettings.repo,
                    self.usersettings.logger,
                    challenge_list,
                    self.usersettings.open_fuben_man.team,
                    recover_threshold,
                    self.stone_fuben_finish_signal,
                    self.stone_fuben_interrupt_event,
                    self.stone_fuben_rest_event,
                )
                self.stone_fuben_interrupt_event.clear()
                self.stone_fuben_rest_event.clear()
                self.stone_fuben_run_thread.start()
            finally:
                self.stone_fuben_start_btn.setEnabled(True)
        elif self.stone_fuben_start_btn.text() == "暂停":
            self.stone_fuben_interrupt_event.set()
            WaitEventThread(
                self.stone_fuben_rest_event, self.stone_fuben_stopped_signal
            ).start()
        else:
            self.stone_fuben_start_btn.setEnabled(True)
            raise RuntimeError(f"未知按钮文本：{self.stone_fuben_start_btn.text()}")

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


class StoneChallengeThread(Thread):
    def __init__(
        self,
        cfg,
        repo: Repository,
        logger: Logger,
        challenge_list,  # (layer, level, difficulty)
        plant_id_list,
        recover_threshold,
        finish_signal,
        interrupt_event: Event,
        rest_event: Event,
    ):
        super().__init__()
        self.wr = WebRequest(cfg)
        self.logger = logger
        self.repo = repo
        self.recover_man = RecoverMan(cfg)
        self.finish_signal = finish_signal
        self.interrupt_event = interrupt_event
        self.rest_event = rest_event
        self.challenge_list = challenge_list
        self.plant_id_list = plant_id_list
        self.recover_threshold = recover_threshold
        assert len(plant_id_list) > 0, "未设置出战植物"
        assert len(challenge_list) > 0, "未设置挑战列表"

    def recover(self):
        if self.recover_threshold is None:
            return True
        self.repo.refresh_repository()
        cnt, max_retry = 0, 20
        success_num_all = 0
        while cnt < max_retry:
            recover_list = []
            for plant_id in self.plant_id_list:
                plant = self.repo.get_plant(plant_id)
                if plant is None:
                    continue
                if plant.hp_now / plant.hp_max <= self.recover_threshold:
                    recover_list.append(plant_id)
            if len(recover_list) == 0:
                return True
            success_num, fail_num = self.recover_man.recover_list(
                recover_list, choice="高级血瓶"
            )
            success_num_all += success_num
            if fail_num == 0:
                break
            self.logger.log("尝试恢复植物血量。成功{}，失败{}".format(success_num, fail_num))
            self.repo.refresh_repository(logger=self.logger)
            cnt += 1
        else:
            self.logger.log("尝试恢复植物血量失败，退出运行")
            return False
        self.repo.refresh_repository()
        if success_num_all > 0:
            self.logger.log("成功给{}个植物回复血量".format(success_num_all))
        return True

    def _challenge(self, layer, level, difficulty):
        body = [float(layer * 100 + level), self.plant_id_list, float(difficulty)]
        response = self.wr.amf_post_retry(
            body, "api.stone.challenge", "/pvz/amf/", "挑战宝石副本", allow_empty=True
        )
        if response is None:
            return {
                "success": False,
                "result": "挑战失败，大概率因为植物没血了",
            }
        if response.status == 1:
            return {
                "success": False,
                "result": response.body.description,
            }
        return {
            "success": True,
            "result": response.body,
        }

    def challenge(self, layer, level, difficulty):
        while True:
            if self.interrupt_event.is_set():
                return False
            result = self._challenge(layer, level, difficulty)
            if not result["success"]:
                self.logger.log(result["result"])
                return False
            is_winning = result["result"]["is_winning"]
            msg = "挑战宝石关卡{}-{}".format(layer * 100 + level, difficulty)
            if is_winning:
                self.logger.log(msg + "成功")
                return True
            else:
                self.logger.log(msg + "失败")
                if not self.recover():
                    self.logger.log("尝试恢复植物血量失败，退出运行")
                    return False
                continue

    def run(self):
        try:
            if not self.recover():
                self.logger.log("尝试恢复植物血量失败，退出运行")
                return
            for layer, level, difficulty in self.challenge_list:
                if self.interrupt_event.is_set():
                    return
                if not self.challenge(layer, level, difficulty):
                    return
        finally:
            self.finish_signal.emit()
            self.rest_event.set()
