from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QCheckBox,
)
from PyQt6 import QtGui

from ..user import UserSettings


class DailySettingWindow(QMainWindow):
    def __init__(self, usersettings: UserSettings, parent=None):
        super().__init__(parent=parent)
        self.usersettings = usersettings
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("日常设置")

        # 将窗口居中显示，宽度为显示器宽度的40%，高度为显示器高度的50%
        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.40), int(screen_size.height() * 0.5))
        self.move(int(screen_size.width() * 0.30), int(screen_size.height() * 0.25))

        main_widget = QWidget()
        main_layout = QVBoxLayout()

        daily_sign_checkbox = QCheckBox("日常签到")
        daily_sign_checkbox.setChecked(self.usersettings.daily_settings[0])
        daily_sign_checkbox.stateChanged.connect(self.daily_sign_checkbox_changed)
        main_layout.addWidget(daily_sign_checkbox)

        vip_reward_acquire_checkbox = QCheckBox("vip奖励领取")
        vip_reward_acquire_checkbox.setChecked(self.usersettings.daily_settings[1])
        vip_reward_acquire_checkbox.stateChanged.connect(
            self.vip_reward_acquire_checkbox_changed
        )
        main_layout.addWidget(vip_reward_acquire_checkbox)

        daily_accumulated_reward_acquire_checkbox = QCheckBox("累计签到奖励领取")
        daily_accumulated_reward_acquire_checkbox.setChecked(
            self.usersettings.daily_settings[2]
        )
        daily_accumulated_reward_acquire_checkbox.stateChanged.connect(
            self.daily_accumulated_reward_acquire_checkbox_changed
        )
        main_layout.addWidget(daily_accumulated_reward_acquire_checkbox)

        arena_rand_reward_acquire_checkbox = QCheckBox("竞技场排名奖励领取")
        arena_rand_reward_acquire_checkbox.setChecked(
            self.usersettings.daily_settings[3]
        )
        arena_rand_reward_acquire_checkbox.stateChanged.connect(
            self.arena_rand_reward_acquire_checkbox_changed
        )
        main_layout.addWidget(arena_rand_reward_acquire_checkbox)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def daily_sign_checkbox_changed(self, state):
        self.usersettings.daily_settings[0] = state

    def vip_reward_acquire_checkbox_changed(self, state):
        self.usersettings.daily_settings[1] = state

    def daily_accumulated_reward_acquire_checkbox_changed(self, state):
        self.usersettings.daily_settings[2] = state

    def arena_rand_reward_acquire_checkbox_changed(self, state):
        self.usersettings.daily_settings[3] = state
