from PyQt6 import QtGui
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QGridLayout,
    QCheckBox,
    QPlainTextEdit,
    QSpinBox,
    QComboBox,
)
from PyQt6.QtCore import Qt, pyqtSignal

from pypvz.ui.wrapped import QLabel
from pypvz.ui.windows.common import (
    AddCaveWindow,
    SetPlantListWindow,
)
from ..user.auto_challenge import Challenge4Level, SingleCave
from ... import Config, Repository, User, Library
from ..message import Logger


class Challenge4levelSettingWindow(QMainWindow):
    selectd_cave_update = pyqtSignal()

    set_plant_list_over = pyqtSignal(list)

    def __init__(
        self,
        cfg: Config,
        lib: Library,
        repo: Repository,
        user: User,
        logger: Logger,
        challenge4Level: Challenge4Level,
        parent=None,
    ):
        super().__init__(parent=parent)
        self.cfg = cfg
        self.lib = lib
        self.repo = repo
        self.user = user
        self.logger = logger
        self.challenge4Level = challenge4Level
        self.selectd_cave: SingleCave = None
        self.set_plant_list_result = []
        self.delete_last_selected_list = None
        self.init_ui()
        self.selectd_cave_update.connect(self.update_selectd_cave)
        self.update_cave_list()
        self.update_main_plant_list()
        self.update_trash_plant_list()

    def init_ui(self):
        self.setWindowTitle("练级设置")

        # 将窗口居中显示，宽度为显示器宽度的40%，高度为显示器高度的60%
        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.4), int(screen_size.height() * 0.8))
        self.move(int(screen_size.width() * 0.3), int(screen_size.height() * 0.05))

        main_widget = QWidget()
        main_layout = QHBoxLayout()

        left_panel = QWidget()
        left_panel_layout = QGridLayout()
        caves_widget = QWidget()
        caves_layout = QVBoxLayout()
        top_layout = QHBoxLayout()
        text = QLabel("洞口:")
        btn = QPushButton("选择洞口")
        btn.clicked.connect(self.add_cave_btn_clicked)
        top_layout.addWidget(text)
        top_layout.addStretch(1)
        top_layout.addWidget(btn)
        self.cave_list = cave_list = QListWidget()
        cave_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        cave_list.itemClicked.connect(self.cave_list_item_clicked)
        caves_layout.addLayout(top_layout)
        caves_layout.addWidget(cave_list)
        caves_widget.setLayout(caves_layout)
        left_panel_layout.addWidget(caves_widget, 0, 0)

        friend_list_panel = QWidget()
        friend_list_panel_layout = QVBoxLayout()
        top_layout = QHBoxLayout()
        text = QLabel("要打的好友列表")
        top_layout.addWidget(text)
        top_layout.addStretch(1)
        self.friend_list = friend_list = QListWidget()
        friend_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        friend_list.itemPressed.connect(self.friend_list_item_clicked)
        friend_list_panel_layout.addLayout(top_layout)
        friend_list_panel_layout.addWidget(friend_list)
        friend_list_panel.setLayout(friend_list_panel_layout)
        left_panel_layout.addWidget(friend_list_panel, 0, 1)

        main_plant_list_panel = QWidget()
        main_plant_list_panel_layout = QVBoxLayout()
        top_layout = QHBoxLayout()
        text = QLabel("主力植物")
        top_layout.addWidget(text)
        top_layout.addStretch(1)
        self.main_plant_setting_btn = btn = QPushButton("设置")
        btn.clicked.connect(self.set_main_plant_btn_clicked)

        top_layout.addWidget(btn)
        self.main_plant_list = main_plant_list = QListWidget()
        main_plant_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        main_plant_list.itemPressed.connect(self.main_plant_list_item_clicked)
        main_plant_list.itemSelectionChanged.connect(
            self.main_plant_list_item_selection_changed
        )
        main_plant_list_panel_layout.addLayout(top_layout)
        main_plant_list_panel_layout.addWidget(main_plant_list)
        main_plant_list_panel.setLayout(main_plant_list_panel_layout)
        left_panel_layout.addWidget(main_plant_list_panel, 1, 0)

        trash_plant_list_panel = QWidget()
        trash_plant_list_panel_layout = QVBoxLayout()
        top_layout = QHBoxLayout()
        text = QLabel("练级植物")
        top_layout.addWidget(text)
        top_layout.addStretch(1)
        self.trash_plant_setting_btn = btn = QPushButton("设置")
        btn.clicked.connect(self.set_trash_plant_btn_clicked)

        top_layout.addWidget(btn)
        self.trash_plant_list = trash_plant_list = QListWidget()
        trash_plant_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        trash_plant_list.itemPressed.connect(self.trash_plant_list_item_clicked)
        trash_plant_list.itemSelectionChanged.connect(
            self.trash_plant_list_item_selection_changed
        )
        trash_plant_list_panel_layout.addLayout(top_layout)
        trash_plant_list_panel_layout.addWidget(trash_plant_list)
        trash_plant_list_panel.setLayout(trash_plant_list_panel_layout)
        left_panel_layout.addWidget(trash_plant_list_panel, 1, 1)

        left_panel.setLayout(left_panel_layout)
        main_layout.addWidget(left_panel)

        right_panel = QWidget()
        right_panel_layout = QVBoxLayout()
        right_panel_layout.setSpacing(0)
        right_panel_layout.addWidget(QLabel("当前洞口的配置:"))

        self.enable_cave_checkbox = QCheckBox("启用当前洞口")
        self.enable_cave_checkbox.setChecked(False)
        self.enable_cave_checkbox.stateChanged.connect(
            self.enable_cave_checkbox_stateChanged
        )
        right_panel_layout.addWidget(self.enable_cave_checkbox)

        self.current_cave_use_sand = QCheckBox("使用时之沙")
        self.current_cave_use_sand.setChecked(False)
        self.current_cave_use_sand.stateChanged.connect(
            self.current_cave_use_sand_stateChanged
        )
        right_panel_layout.addWidget(self.current_cave_use_sand)

        self.current_cave_difficulty = QComboBox()
        self.current_cave_difficulty.addItems(["简单", "普通", "困难"])
        self.current_cave_difficulty.setCurrentIndex(3)
        self.current_cave_difficulty.currentIndexChanged.connect(
            self.current_cave_difficulty_currentIndexChanged
        )
        right_panel_layout.addWidget(self.current_cave_difficulty)

        space_widget = QWidget()
        space_widget.setFixedHeight(10)
        right_panel_layout.addWidget(space_widget)

        right_panel_layout.addWidget(QLabel("全局挑战设置:"))

        cave_enabled_switch_layout = QHBoxLayout()
        enable_all_cave_btn = QPushButton("启用所有洞口")
        enable_all_cave_btn.clicked.connect(self.enable_all_cave_btn_clicked)
        cave_enabled_switch_layout.addWidget(enable_all_cave_btn)
        disable_all_cave_btn = QPushButton("禁用所有洞口")
        disable_all_cave_btn.clicked.connect(self.disable_all_cave_btn_clicked)
        cave_enabled_switch_layout.addWidget(disable_all_cave_btn)
        right_panel_layout.addLayout(cave_enabled_switch_layout)

        free_max_input_widget = QWidget()
        free_max_input_layout = QHBoxLayout()
        free_max_input_box = QSpinBox()
        free_max_input_box.setMinimum(0)
        free_max_input_box.setMaximum(16)
        free_max_input_box.setValue(self.challenge4Level.free_max)

        def free_max_input_box_value_changed(value):
            self.challenge4Level.free_max = value

        free_max_input_box.valueChanged.connect(free_max_input_box_value_changed)
        free_max_input_layout.addWidget(QLabel("出战植物最大空位数:"))
        free_max_input_layout.addWidget(free_max_input_box)
        free_max_input_widget.setLayout(free_max_input_layout)
        right_panel_layout.addWidget(free_max_input_widget)

        hp_choice_widget = QWidget()
        hp_choice_layout = QHBoxLayout()
        hp_choice_layout.addWidget(QLabel("血瓶选择:"))
        hp_choice_box = QComboBox()
        self.hp_choice_list = ["低级血瓶", "中级血瓶", "高级血瓶"]
        hp_choice_box.addItems(self.hp_choice_list)
        hp_choice_box.setCurrentIndex(
            self.hp_choice_list.index(self.challenge4Level.hp_choice)
        )
        hp_choice_box.currentIndexChanged.connect(
            self.hp_choice_box_currentIndexChanged
        )
        hp_choice_layout.addWidget(hp_choice_box)
        hp_choice_widget.setLayout(hp_choice_layout)
        right_panel_layout.addWidget(hp_choice_widget)

        self.main_plant_recover_checkbox = QCheckBox("主力血量也恢复")
        self.main_plant_recover_checkbox.setChecked(
            self.challenge4Level.main_plant_recover
        )
        self.main_plant_recover_checkbox.stateChanged.connect(
            self.main_plant_recover_checkbox_stateChanged
        )
        right_panel_layout.addWidget(self.main_plant_recover_checkbox)

        main_plant_recover_rate_layout = QHBoxLayout()
        main_plant_recover_rate_layout.addWidget(QLabel("主力恢复百分比阈值:"))
        self.main_plant_recover_rate_spinbox = QSpinBox()
        self.main_plant_recover_rate_spinbox.setMinimum(0)
        self.main_plant_recover_rate_spinbox.setMaximum(100)
        self.main_plant_recover_rate_spinbox.setValue(
            int(self.challenge4Level.main_plant_recover_rate * 100)
        )
        self.main_plant_recover_rate_spinbox.valueChanged.connect(
            self.main_plant_recover_rate_spinbox_valueChanged
        )
        main_plant_recover_rate_layout.addWidget(self.main_plant_recover_rate_spinbox)
        main_plant_recover_rate_layout.addWidget(QLabel("%"))
        right_panel_layout.addLayout(main_plant_recover_rate_layout)

        widget1 = QWidget()
        widget1_layout = QHBoxLayout()
        widget1_layout.addWidget(QLabel("100级后弹出:"))
        self.pop_checkbox = QCheckBox()
        self.pop_checkbox.setChecked(self.challenge4Level.pop_after_100)
        self.pop_checkbox.stateChanged.connect(self.pop_checkbox_stateChanged)
        widget1_layout.addWidget(self.pop_checkbox)
        widget1.setLayout(widget1_layout)
        right_panel_layout.addWidget(widget1)

        skip_no_trash_plant_layout = QHBoxLayout()
        skip_no_trash_plant_layout.addWidget(QLabel("没炮灰停止挑战:"))
        self.skip_no_trash_plant_checkbox = QCheckBox()
        self.skip_no_trash_plant_checkbox.setChecked(
            self.challenge4Level.skip_no_trash_plant
        )
        self.skip_no_trash_plant_checkbox.stateChanged.connect(
            self.skip_no_trash_plant_checkbox_stateChanged
        )
        skip_no_trash_plant_layout.addWidget(self.skip_no_trash_plant_checkbox)
        right_panel_layout.addLayout(skip_no_trash_plant_layout)

        widget2 = QWidget()
        widget2_layout = QHBoxLayout()
        widget2_layout.addWidget(QLabel("自动使用挑战书(优先高挑):"))
        self.auto_use_challenge_book_checkbox = QCheckBox()
        self.auto_use_challenge_book_checkbox.setChecked(
            self.challenge4Level.auto_use_challenge_book
        )
        self.auto_use_challenge_book_checkbox.stateChanged.connect(
            self.auto_use_challenge_book_checkbox_stateChanged
        )
        widget2_layout.addWidget(self.auto_use_challenge_book_checkbox)
        widget2.setLayout(widget2_layout)
        right_panel_layout.addWidget(widget2)

        widget3 = QWidget()
        widget3_layout = QHBoxLayout()
        widget3_layout.addWidget(QLabel("一次使用多少高挑:"))
        self.use_advanced_challenge_book_count_box = QSpinBox()
        self.use_advanced_challenge_book_count_box.setMinimum(1)
        self.use_advanced_challenge_book_count_box.setMaximum(
            5 if self.cfg.server == "官服" else 2250 // 5
        )
        self.use_advanced_challenge_book_count_box.setValue(
            self.challenge4Level.advanced_challenge_book_amount
        )
        self.use_advanced_challenge_book_count_box.valueChanged.connect(
            self.use_advanced_challenge_book_count_box_currentIndexChanged
        )
        widget3_layout.addWidget(self.use_advanced_challenge_book_count_box)
        widget3.setLayout(widget3_layout)
        right_panel_layout.addWidget(widget3)

        widget4 = QWidget()
        widget4_layout = QHBoxLayout()
        widget4_layout.addWidget(QLabel("一次使用多少挑战书:"))
        self.use_normal_challenge_book_count_box = QSpinBox()
        self.use_normal_challenge_book_count_box.setMinimum(1)
        self.use_normal_challenge_book_count_box.setMaximum(
            25 if self.cfg.server == "官服" else 2250
        )
        self.use_normal_challenge_book_count_box.setValue(
            self.challenge4Level.normal_challenge_book_amount
        )
        self.use_normal_challenge_book_count_box.valueChanged.connect(
            self.use_normal_challenge_book_count_box_currentIndexChanged
        )
        widget4_layout.addWidget(self.use_normal_challenge_book_count_box)
        widget4.setLayout(widget4_layout)
        right_panel_layout.addWidget(widget4)

        self.enable_sand = QCheckBox("允许使用时之沙")
        self.enable_sand.setChecked(self.challenge4Level.enable_sand)
        self.enable_sand.stateChanged.connect(self.enable_sand_stateChanged)
        right_panel_layout.addWidget(self.enable_sand)

        self.show_lottery = QCheckBox("是否显示获胜战利品(会变慢)")
        self.show_lottery.setChecked(self.challenge4Level.show_lottery)
        self.show_lottery.stateChanged.connect(self.show_lottery_stateChanged)
        right_panel_layout.addWidget(self.show_lottery)

        self.enable_stone = QCheckBox("允许挑战宝石副本")
        self.enable_stone.setChecked(self.challenge4Level.enable_stone)
        self.enable_stone.stateChanged.connect(self.enable_stone_stateChanged)
        right_panel_layout.addWidget(self.enable_stone)

        if self.cfg.server == "私服":
            self.enable_large_plant_team = QCheckBox("V4使用16格带级")
            self.enable_large_plant_team.setChecked(
                self.challenge4Level.enable_large_plant_team
            )
            self.enable_large_plant_team.stateChanged.connect(
                self.enable_large_plant_team_stateChanged
            )
            right_panel_layout.addWidget(self.enable_large_plant_team)

        right_panel_layout.addWidget(QLabel("--以下功能需认真选取--\n--(因为不恰当使用会有bug)--"))

        self.need_recover_checkbox = QCheckBox("需要恢复植物血量")
        self.need_recover_checkbox.setChecked(self.challenge4Level.need_recover)
        self.need_recover_checkbox.stateChanged.connect(
            self.need_recover_checkbox_stateChanged
        )
        right_panel_layout.addWidget(self.need_recover_checkbox)

        self.disable_cave_info_fetch_checkbox = QCheckBox("刷洞加速")
        self.disable_cave_info_fetch_checkbox.setChecked(
            self.challenge4Level.disable_cave_info_fetch
        )
        self.disable_cave_info_fetch_checkbox.stateChanged.connect(
            self.disable_cave_info_fetch_checkbox_stateChanged
        )
        right_panel_layout.addWidget(self.disable_cave_info_fetch_checkbox)

        self.challenge_sand_cave_only_in_disable_mode_checkbox = QCheckBox(
            "加速时只刷用时之沙的洞"
        )
        self.challenge_sand_cave_only_in_disable_mode_checkbox.setChecked(
            self.challenge4Level.challenge_sand_cave_only_in_disable_mode
        )
        self.challenge_sand_cave_only_in_disable_mode_checkbox.stateChanged.connect(
            self.challenge_sand_cave_only_in_disable_mode_checkbox_stateChanged
        )
        right_panel_layout.addWidget(
            self.challenge_sand_cave_only_in_disable_mode_checkbox
        )

        self.accelerate_repository_in_challenge_cave_checkbox = QCheckBox("跳过仓库来加速")
        self.accelerate_repository_in_challenge_cave_checkbox.setChecked(
            self.challenge4Level.accelerate_repository_in_challenge_cave
        )
        self.accelerate_repository_in_challenge_cave_checkbox.stateChanged.connect(
            self.accelerate_repository_in_challenge_cave_checkbox_stateChanged
        )
        right_panel_layout.addWidget(
            self.accelerate_repository_in_challenge_cave_checkbox
        )

        warning_textbox = QPlainTextEdit()
        warning_textbox.setReadOnly(True)
        warning_textbox.setPlainText(
            "警告：使用上述功能需详细查看此警告\n"
            "注意，加速原理是直接挑战对应洞口\n"
            "因此如果加速不选\"只刷时之沙的洞\"会导致每次循环都会尝试那些没冷却的洞\n"
            "比如你选了10个洞口，只有一个要用时之沙，那么每次都会尝试挑战那9个不用时之沙的洞口\n"
            "会造成很大的性能浪费\n"
            "对于加速跳过仓库，这个选项开启后，原理是不会去获取仓库信息，会预测你的炮灰等级变化，从而加速\n"
            "但是因为跳过了仓库信息获取，因此无法保证植物存在和植物血量\n"
            "选择此选项也会跳过植物回血，请保证以下情况不会发生的时候使用仓库加速:\n"
            "1. 你的植物不会死亡，包括主力和炮灰\n"
            "2. 你的植物不会消失，包括主力和炮灰\n"
        )
        warning_textbox.setFixedHeight(int(self.height() * 0.15))
        right_panel_layout.addWidget(warning_textbox)

        right_panel_layout.addStretch(1)

        right_panel.setLayout(right_panel_layout)
        main_layout.addWidget(right_panel)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def skip_no_trash_plant_checkbox_stateChanged(self):
        self.challenge4Level.skip_no_trash_plant = (
            self.skip_no_trash_plant_checkbox.isChecked()
        )

    def main_plant_recover_checkbox_stateChanged(self):
        self.challenge4Level.main_plant_recover = (
            self.main_plant_recover_checkbox.isChecked()
        )

    def main_plant_recover_rate_spinbox_valueChanged(self, value):
        self.challenge4Level.main_plant_recover_rate = value / 100

    def enable_all_cave_btn_clicked(self):
        for sc in self.challenge4Level.caves:
            sc.enabled = True
        self.selectd_cave_update.emit()

    def disable_all_cave_btn_clicked(self):
        for sc in self.challenge4Level.caves:
            sc.enabled = False
        self.selectd_cave_update.emit()

    def enable_cave_checkbox_stateChanged(self):
        self.selectd_cave.enabled = self.enable_cave_checkbox.isChecked()

    def accelerate_repository_in_challenge_cave_checkbox_stateChanged(self):
        self.challenge4Level.accelerate_repository_in_challenge_cave = (
            self.accelerate_repository_in_challenge_cave_checkbox.isChecked()
        )

    def challenge_sand_cave_only_in_disable_mode_checkbox_stateChanged(self):
        self.challenge4Level.challenge_sand_cave_only_in_disable_mode = (
            self.challenge_sand_cave_only_in_disable_mode_checkbox.isChecked()
        )

    def need_recover_checkbox_stateChanged(self):
        self.challenge4Level.need_recover = self.need_recover_checkbox.isChecked()

    def disable_cave_info_fetch_checkbox_stateChanged(self):
        self.challenge4Level.disable_cave_info_fetch = (
            self.disable_cave_info_fetch_checkbox.isChecked()
        )

    def enable_large_plant_team_stateChanged(self):
        self.challenge4Level.enable_large_plant_team = (
            self.enable_large_plant_team.isChecked()
        )

    def enable_stone_stateChanged(self):
        self.challenge4Level.enable_stone = self.enable_stone.isChecked()

    def current_cave_use_sand_stateChanged(self):
        self.selectd_cave.use_sand = self.current_cave_use_sand.isChecked()

    def current_cave_difficulty_currentIndexChanged(self, index):
        self.selectd_cave.difficulty = index + 1

    def show_lottery_stateChanged(self):
        self.challenge4Level.show_lottery = self.show_lottery.isChecked()

    def enable_sand_stateChanged(self):
        self.challenge4Level.enable_sand = self.enable_sand.isChecked()

    def hp_choice_box_currentIndexChanged(self, index):
        self.challenge4Level.hp_choice = self.hp_choice_list[index]

    def pop_checkbox_stateChanged(self):
        self.challenge4Level.pop_after_100 = self.pop_checkbox.isChecked()

    def use_normal_challenge_book_count_box_currentIndexChanged(self):
        self.challenge4Level.normal_challenge_book_amount = (
            self.use_normal_challenge_book_count_box.value()
        )

    def use_advanced_challenge_book_count_box_currentIndexChanged(self):
        self.challenge4Level.advanced_challenge_book_amount = (
            self.use_advanced_challenge_book_count_box.value()
        )

    def auto_use_challenge_book_checkbox_stateChanged(self):
        self.challenge4Level.auto_use_challenge_book = (
            self.auto_use_challenge_book_checkbox.isChecked()
        )

    def update_selectd_cave(self):
        self.update_friend_list()
        if self.selectd_cave is None:
            self.enable_cave_checkbox.setDisabled(True)
            self.current_cave_use_sand.setDisabled(True)
            self.current_cave_difficulty.setDisabled(True)
            return
        self.enable_cave_checkbox.setChecked(self.selectd_cave.enabled)
        self.current_cave_use_sand.setChecked(self.selectd_cave.use_sand)
        self.current_cave_difficulty.setCurrentIndex(self.selectd_cave.difficulty - 1)
        self.enable_cave_checkbox.setEnabled(True)
        self.current_cave_use_sand.setEnabled(True)
        self.current_cave_difficulty.setEnabled(True)

    def cave_list_item_clicked(self, item):
        self.selectd_cave = item.data(Qt.ItemDataRole.UserRole)
        self.selectd_cave_update.emit()
        self.delete_last_selected_list = self.cave_list

    def friend_list_item_clicked(self, item):
        self.delete_last_selected_list = self.friend_list

    def main_plant_list_item_clicked(self, item):
        self.delete_last_selected_list = self.main_plant_list

    def main_plant_list_item_selection_changed(self):
        self.delete_last_selected_list = self.main_plant_list

    def trash_plant_list_item_selection_changed(self):
        self.delete_last_selected_list = self.trash_plant_list

    def trash_plant_list_item_clicked(self, item):
        self.delete_last_selected_list = self.trash_plant_list

    def update_cave_list(self):
        self.cave_list.clear()
        self.cave_list.setCurrentItem(None)
        self.selectd_cave = None
        self.selectd_cave_update.emit()
        caves = self.challenge4Level.caves
        for sc in caves:
            item = QListWidgetItem(sc.cave.format_name())
            item.setData(Qt.ItemDataRole.UserRole, sc)
            self.cave_list.addItem(item)

    def update_friend_list(self):
        self.friend_list.clear()
        if self.selectd_cave is None:
            return
        for friend_id in self.selectd_cave.friend_id_list:
            friend = self.user.friendMan.id2friend[friend_id]
            item = QListWidgetItem(f"{friend.name} ({friend.grade})")
            item.setData(Qt.ItemDataRole.UserRole, friend)
            self.friend_list.addItem(item)

    def update_main_plant_list(self):
        self.main_plant_list.clear()
        for plant_id in self.challenge4Level.main_plant_list:
            plant = self.repo.get_plant(plant_id)
            if plant is None:
                self.challenge4Level.main_plant_list.remove(plant_id)
                continue
            item = QListWidgetItem(f"{plant.name(self.lib)} ({plant.grade})")
            item.setData(Qt.ItemDataRole.UserRole, plant)
            self.main_plant_list.addItem(item)

    def update_trash_plant_list(self):
        self.trash_plant_list.clear()
        for plant_id in self.challenge4Level.trash_plant_list:
            plant = self.repo.get_plant(plant_id)
            if plant is None:
                self.challenge4Level.trash_plant_list.remove(plant_id)
                continue
            item = QListWidgetItem(f"{plant.name(self.lib)} ({plant.grade})")
            item.setData(Qt.ItemDataRole.UserRole, plant)
            self.trash_plant_list.addItem(item)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            if self.delete_last_selected_list is not None:
                select_items = self.delete_last_selected_list.selectedItems()
                if self.delete_last_selected_list is self.cave_list:
                    for item in select_items:
                        sc = item.data(Qt.ItemDataRole.UserRole)
                        self.challenge4Level.remove_cave(sc.cave, sc.garden_layer)
                    self.update_cave_list()
                elif self.delete_last_selected_list is self.main_plant_list:
                    for item in select_items:
                        plant = item.data(Qt.ItemDataRole.UserRole)
                        self.challenge4Level.main_plant_list.remove(plant.id)
                    self.update_main_plant_list()
                elif self.delete_last_selected_list is self.trash_plant_list:
                    for item in select_items:
                        plant = item.data(Qt.ItemDataRole.UserRole)
                        self.challenge4Level.trash_plant_list.remove(plant.id)
                    self.update_trash_plant_list()
                elif self.delete_last_selected_list is self.friend_list:
                    friend_ids = [
                        item.data(Qt.ItemDataRole.UserRole).id for item in select_items
                    ]
                    self.challenge4Level.remove_cave_friend(
                        self.selectd_cave,
                        friend_ids,
                        self.selectd_cave.garden_layer,
                    )
                    self.update_friend_list()
                else:
                    raise NotImplementedError
        # elif event.key() == Qt.Key.Key_Up or event.key() == Qt.Key.Key_A:
        #     self.close()

    def add_cave_btn_clicked(self):
        self.add_cave_window = AddCaveWindow(
            self.cfg, self.user, self.logger, self.challenge4Level, parent=self
        )
        self.add_cave_window.cave_add_update.connect(self.update_cave_list)
        self.add_cave_window.show()

    def add_main_plant(self, result):
        self.challenge4Level.main_plant_list = (
            self.challenge4Level.main_plant_list + result
        )
        self.update_main_plant_list()

    def set_main_plant_btn_clicked(self):
        # 当set_plant_list_over有链接的槽函数时，将之前的槽函数disconnect
        try:
            self.set_plant_list_over.disconnect()
        except TypeError:
            pass
        self.set_plant_list_over.connect(self.add_main_plant)
        self.set_plant_list_window = SetPlantListWindow(
            self.repo,
            self.lib,
            self.set_plant_list_over,
            origin_plant_id_list=self.challenge4Level.main_plant_list
            + self.challenge4Level.trash_plant_list,
            parent=self,
        )
        self.set_plant_list_window.show()

    def add_trash_plant(self, result):
        self.challenge4Level.trash_plant_list = (
            self.challenge4Level.trash_plant_list + result
        )
        self.update_trash_plant_list()

    def set_trash_plant_btn_clicked(self):
        try:
            self.set_plant_list_over.disconnect()
        except TypeError:
            pass
        self.set_plant_list_over.connect(self.add_trash_plant)
        self.set_plant_list_window = SetPlantListWindow(
            self.repo,
            self.lib,
            self.set_plant_list_over,
            origin_plant_id_list=self.challenge4Level.main_plant_list
            + self.challenge4Level.trash_plant_list,
            parent=self,
        )
        self.set_plant_list_window.show()
