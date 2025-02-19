import sys
import argparse
import json
from io import BytesIO
import os
import logging
import concurrent.futures
import threading
import shutil
import warnings
import pickle
import subprocess
import multiprocessing

warnings.filterwarnings("ignore", category=DeprecationWarning)

from PyQt6 import QtGui
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QGridLayout,
    QCheckBox,
    QPlainTextEdit,
    QSpinBox,
    QComboBox,
    QLineEdit,
    QFileDialog,
    QTextEdit,
)
from PyQt6.QtGui import QImage, QPixmap, QTextCursor, QTextCharFormat, QColor
from PyQt6.QtCore import Qt, pyqtSignal
from PIL import Image

from pypvz import WebRequest, Config, User, Repository, Library
from pypvz.ui.message import IOLogger
from pypvz.ui.wrapped import QLabel
from pypvz.ui.windows.common import (
    HeritageWindow,
)
from pypvz.ui.user import UserSettings
from pypvz.ui.windows import (
    EvolutionPanelWindow,
    UpgradeQualityWindow,
    AutoSynthesisWindow,
    AutoCompoundWindow,
    RepositoryRecordWindow,
    FubenSettingWindow,
    GardenChallengeSettingWindow,
    TerritorySettingWindow,
    PipelineSettingWindow,
    ShopAutoBuySetting,
    Challenge4levelSettingWindow,
    DailySettingWindow,
    SimulateWindow,
    AutoUseItemSettingWindow,
    CommandSettingWindow,
    OpenFubenWindow,
    PlantRelativeWindow,
    # GameWindow,
    # run_game_window,
)
from pypvz.ui.windows.common import delete_layout_children
from pypvz.web import proxy_man, test_proxy_alive
from pypvz.proxy import GameWindowProxyServer


class SettingWindow(QMainWindow):
    def __init__(self, usersettings: UserSettings, parent=None):
        super().__init__(parent=parent)
        self.usersettings = usersettings
        self.init_ui()

    def init_ui(self):
        # 将窗口居中显示，宽度为显示器宽度的50%，高度为显示器高度的70%
        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.5), int(screen_size.height() * 0.7))
        self.move(int(screen_size.width() * 0.25), int(screen_size.height() * 0.15))
        self.setWindowTitle("设置")

        main_widget = QWidget()
        main_layout = QHBoxLayout()

        left_panel = QWidget()
        left_panel.setFixedWidth(int(self.width() * 0.2))
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("植物列表"))
        self.plant_list = QListWidget()
        self.plant_list.addItems(
            [
                f"{plant.name(self.usersettings.lib)}({plant.grade})"
                for plant in self.usersettings.repo.plants
            ]
        )
        left_layout.addWidget(self.plant_list)
        left_panel.setLayout(left_layout)

        main_layout.addWidget(left_panel)

        menu_widget = QWidget()
        menu_layout = QGridLayout()
        challenge4level_widget = QWidget()
        challenge4level_layout = QHBoxLayout()
        self.challenge4level_checkbox = challenge4level_checkbox = QCheckBox("刷洞")
        challenge4level_checkbox.setChecked(self.usersettings.challenge4Level_enabled)
        challenge4level_checkbox.stateChanged.connect(
            self.challenge4level_checkbox_stateChanged
        )
        challenge4level_layout.addWidget(challenge4level_checkbox)
        challenge4level_setting_btn = QPushButton("设置")
        challenge4level_setting_btn.clicked.connect(
            self.challenge4level_setting_btn_clicked
        )
        challenge4level_layout.addWidget(challenge4level_setting_btn)
        challenge4level_layout.addStretch(1)
        challenge4level_widget.setLayout(challenge4level_layout)
        menu_layout.addWidget(challenge4level_widget, 0, 0)

        fuben_widget = QWidget()
        fuben_layout = QHBoxLayout()
        self.fuben_checkbox = QCheckBox("副本")
        self.fuben_checkbox.setChecked(self.usersettings.fuben_enabled)
        self.fuben_checkbox.stateChanged.connect(self.fuben_checkbox_stateChanged)
        fuben_layout.addWidget(self.fuben_checkbox)
        fuben_setting_btn = QPushButton("设置")
        fuben_setting_btn.clicked.connect(self.fuben_setting_btn_clicked)
        fuben_layout.addWidget(fuben_setting_btn)
        fuben_layout.addStretch(1)
        fuben_widget.setLayout(fuben_layout)
        menu_layout.addWidget(fuben_widget, 0, 1)

        command_widget = QWidget()
        command_layout = QHBoxLayout()
        self.command_enable_checkbox = QCheckBox("指令")
        self.command_enable_checkbox.setChecked(self.usersettings.command_enabled)
        self.command_enable_checkbox.stateChanged.connect(
            self.command_enable_checkbox_stateChanged
        )
        command_layout.addWidget(self.command_enable_checkbox)
        command_setting_btn = QPushButton("设置")
        command_setting_btn.clicked.connect(self.command_setting_btn_clicked)
        command_layout.addWidget(command_setting_btn)
        command_layout.addStretch(1)
        command_widget.setLayout(command_layout)
        menu_layout.addWidget(command_widget, 0, 2)

        # shop_enable_widget = QWidget()
        # shop_enable_layout = QHBoxLayout()
        # self.shop_enable_checkbox = shop_enable_checkbox = QCheckBox("商店购买")
        # shop_enable_checkbox.setChecked(self.usersettings.shop_enabled)
        # shop_enable_checkbox.stateChanged.connect(
        #     self.shop_enable_checkbox_stateChanged
        # )
        # shop_enable_layout.addWidget(shop_enable_checkbox)
        # shop_auto_buy_setting_btn = QPushButton("设置")
        # shop_auto_buy_setting_btn.clicked.connect(
        #     self.shop_auto_buy_setting_btn_clicked
        # )
        # shop_enable_layout.addWidget(shop_auto_buy_setting_btn)
        # shop_enable_layout.addStretch(1)
        # shop_enable_widget.setLayout(shop_enable_layout)
        # menu_layout.addWidget(shop_enable_widget, 1, 0)

        task_panel = QWidget()
        task_panel_layout = QVBoxLayout()
        self.task_setting_checkbox = QCheckBox("自动领取任务")
        self.task_setting_checkbox.setChecked(self.usersettings.task_enabled)
        self.task_setting_checkbox.stateChanged.connect(
            self.task_setting_checkbox_stateChanged
        )
        task_panel_layout.addWidget(self.task_setting_checkbox)
        task_widget = QWidget()
        task_layout = QHBoxLayout()

        main_task_widget = QWidget()
        main_task_layout = QHBoxLayout()
        self.main_task_checkbox = QCheckBox("主线")
        self.main_task_checkbox.setChecked(self.usersettings.enable_list[0])
        self.main_task_checkbox.stateChanged.connect(
            self.main_task_checkbox_stateChanged
        )
        main_task_layout.addWidget(self.main_task_checkbox)
        main_task_widget.setLayout(main_task_layout)
        task_layout.addWidget(main_task_widget)

        side_task_widget = QWidget()
        side_task_layout = QHBoxLayout()
        self.side_task_checkbox = QCheckBox("支线")
        self.side_task_checkbox.setChecked(self.usersettings.enable_list[1])
        self.side_task_checkbox.stateChanged.connect(
            self.side_task_checkbox_stateChanged
        )
        side_task_layout.addWidget(self.side_task_checkbox)
        side_task_widget.setLayout(side_task_layout)
        task_layout.addWidget(side_task_widget)

        daily_task_widget = QWidget()
        daily_task_layout = QHBoxLayout()
        self.daily_task_checkbox = QCheckBox("日常")
        self.daily_task_checkbox.setChecked(self.usersettings.enable_list[2])
        self.daily_task_checkbox.stateChanged.connect(
            self.daily_task_checkbox_stateChanged
        )
        daily_task_layout.addWidget(self.daily_task_checkbox)
        daily_task_widget.setLayout(daily_task_layout)
        task_layout.addWidget(daily_task_widget)

        active_task_widget = QWidget()
        active_task_layout = QHBoxLayout()
        self.active_task_checkbox = QCheckBox("活动")
        self.active_task_checkbox.setChecked(self.usersettings.enable_list[3])
        self.active_task_checkbox.stateChanged.connect(
            self.active_task_checkbox_stateChanged
        )
        active_task_layout.addWidget(self.active_task_checkbox)
        active_task_widget.setLayout(active_task_layout)
        task_layout.addWidget(active_task_widget)
        task_layout.addStretch(1)
        task_widget.setLayout(task_layout)

        task_panel_layout.addWidget(task_widget)
        task_panel.setLayout(task_panel_layout)

        menu_layout.addWidget(task_panel, 2, 0)

        auto_shop = QWidget()
        auto_shop_layout = QHBoxLayout()
        self.shop_enable_checkbox = QCheckBox("每日商店购买")
        self.shop_enable_checkbox.setChecked(self.usersettings.shop_enabled)
        self.shop_enable_checkbox.stateChanged.connect(
            self.shop_enable_checkbox_stateChanged
        )
        auto_shop_layout.addWidget(self.shop_enable_checkbox)
        shop_auto_buy_setting_btn = QPushButton("设置")
        shop_auto_buy_setting_btn.clicked.connect(
            self.shop_auto_buy_setting_btn_clicked
        )
        auto_shop_layout.addWidget(shop_auto_buy_setting_btn)
        auto_shop_layout.addStretch(1)
        auto_shop.setLayout(auto_shop_layout)
        menu_layout.addWidget(auto_shop, 2, 1)

        arena_widget = QWidget()
        arena_layout = QHBoxLayout()
        self.arena_checkbox = QCheckBox("竞技场")
        self.arena_checkbox.setChecked(self.usersettings.arena_enabled)
        self.arena_checkbox.stateChanged.connect(self.arena_checkbox_stateChanged)
        arena_layout.addWidget(self.arena_checkbox)
        self.arena_challenge_mode_combobox = QComboBox()
        self.arena_challenge_mode_combobox.addItem("指令")
        self.arena_challenge_mode_combobox.addItem("手打")
        self.arena_challenge_mode_combobox.setCurrentIndex(
            self.usersettings.arena_challenge_mode
        )
        self.arena_challenge_mode_combobox.currentIndexChanged.connect(
            self.arena_challenge_mode_combobox_index_changed
        )
        arena_layout.addWidget(self.arena_challenge_mode_combobox)
        arena_layout.addStretch(1)
        arena_widget.setLayout(arena_layout)
        menu_layout.addWidget(arena_widget, 4, 0)

        serverbattle_widget = QWidget()
        serverbattle_layout = QVBoxLayout()
        layout1 = QHBoxLayout()
        self.serverbattle_checkbox = QCheckBox("跨服战")
        self.serverbattle_checkbox.setChecked(self.usersettings.serverbattle_enabled)
        self.serverbattle_checkbox.stateChanged.connect(
            self.serverbattle_checkbox_stateChanged
        )
        layout1.addWidget(self.serverbattle_checkbox)
        serverbattle_layout.addLayout(layout1)
        layout2 = QHBoxLayout()
        layout2.addWidget(QLabel("跨服次数保存数量:"))
        self.serverbattle_rest_num_inputbox = QLineEdit()
        self.serverbattle_rest_num_inputbox.setText(
            str(self.usersettings.serverbattle_man.rest_challenge_num_limit)
        )
        self.serverbattle_rest_num_inputbox.setValidator(QtGui.QIntValidator(0, 9999))
        self.serverbattle_rest_num_inputbox.textChanged.connect(
            self.serverbattle_rest_num_inputbox_textChanged
        )
        layout2.addWidget(self.serverbattle_rest_num_inputbox)
        serverbattle_layout.addLayout(layout2)
        serverbattle_widget.setLayout(serverbattle_layout)
        menu_layout.addWidget(serverbattle_widget, 4, 1)

        daily_widget = QWidget()
        daily_layout = QHBoxLayout()
        self.daily_checkbox = QCheckBox("每日日常")
        self.daily_checkbox.setChecked(self.usersettings.daily_enabled)
        self.daily_checkbox.stateChanged.connect(self.daily_checkbox_stateChanged)
        daily_layout.addWidget(self.daily_checkbox)
        daily_setting_btn = QPushButton("设置")
        daily_setting_btn.clicked.connect(self.daily_setting_btn_clicked)
        daily_layout.addWidget(daily_setting_btn)
        daily_widget.setLayout(daily_layout)
        menu_layout.addWidget(daily_widget, 4, 2)

        territory_widget = QWidget()
        territory_layout = QHBoxLayout()
        self.territory_checkbox = QCheckBox("领地")
        self.territory_checkbox.setChecked(self.usersettings.territory_enabled)
        self.territory_checkbox.stateChanged.connect(
            self.territory_checkbox_stateChanged
        )
        territory_layout.addWidget(self.territory_checkbox)

        self.territory_setting_btn = QPushButton("设置")
        self.territory_setting_btn.clicked.connect(self.territory_setting_btn_clicked)
        territory_layout.addWidget(self.territory_setting_btn)

        territory_layout.addStretch(1)
        territory_widget.setLayout(territory_layout)
        menu_layout.addWidget(territory_widget, 5, 0)

        # self.garden_checkbox = QCheckBox("自动花园boss")
        # self.garden_checkbox.setChecked(self.usersettings.garden_enabled)
        # self.garden_checkbox.stateChanged.connect(self.garden_checkbox_stateChanged)
        # menu_layout.addWidget(self.garden_checkbox, 5, 1)
        garden_widget = QWidget()
        garden_layout = QHBoxLayout()
        self.garden_checkbox = QCheckBox("自动花园boss")
        self.garden_checkbox.setChecked(self.usersettings.garden_enabled)
        self.garden_checkbox.stateChanged.connect(self.garden_checkbox_stateChanged)
        garden_layout.addWidget(self.garden_checkbox)
        setting_btn = QPushButton("设置")
        setting_btn.clicked.connect(self.garden_setting_btn_clicked)
        garden_layout.addWidget(setting_btn)
        garden_layout.addStretch(1)
        garden_widget.setLayout(garden_layout)
        menu_layout.addWidget(garden_widget, 5, 1)

        rest_time_input_widget = QWidget()
        rest_time_input_layout = QHBoxLayout()
        rest_time_input_layout.addWidget(QLabel("休息时间(秒):"))
        rest_time_input_box = QSpinBox()
        rest_time_input_box.setMinimum(0)
        rest_time_input_box.setMaximum(60 * 60)
        rest_time_input_box.setValue(self.usersettings.rest_time)
        rest_time_input_box.valueChanged.connect(self.rest_time_input_box_valueChanged)
        rest_time_input_layout.addWidget(rest_time_input_box)
        rest_time_input_widget.setLayout(rest_time_input_layout)
        menu_layout.addWidget(rest_time_input_widget, 6, 0)

        max_timeout_widget = QWidget()
        max_timeout_layout = QHBoxLayout()
        max_timeout_layout.addWidget(QLabel("请求最大超时时间(秒):"))
        self.max_timeout_input_box = QSpinBox()
        self.max_timeout_input_box.setMinimum(1)
        self.max_timeout_input_box.setMaximum(60)
        self.max_timeout_input_box.setValue(self.usersettings.cfg.timeout)
        self.max_timeout_input_box.valueChanged.connect(
            self.max_timeout_input_box_valueChanged
        )
        max_timeout_layout.addWidget(self.max_timeout_input_box)
        max_timeout_widget.setLayout(max_timeout_layout)
        menu_layout.addWidget(max_timeout_widget, 7, 0)

        millsecond_delay_widget = QWidget()
        millsecond_delay_layout = QHBoxLayout()
        millsecond_delay_layout.addWidget(QLabel("请求间隔(毫秒):"))
        self.millsecond_delay_input_box = QSpinBox()
        self.millsecond_delay_input_box.setMinimum(0)
        self.millsecond_delay_input_box.setMaximum(60 * 1000)
        self.millsecond_delay_input_box.setValue(self.usersettings.cfg.millsecond_delay)
        self.millsecond_delay_input_box.valueChanged.connect(
            self.millsecond_delay_input_box_valueChanged
        )
        millsecond_delay_layout.addWidget(self.millsecond_delay_input_box)
        millsecond_delay_widget.setLayout(millsecond_delay_layout)
        menu_layout.addWidget(millsecond_delay_widget, 8, 0)

        self.close_if_nothing_todo_checkbox = QCheckBox("无事可做时关闭用户")
        self.close_if_nothing_todo_checkbox.setChecked(
            self.usersettings.exit_if_nothing_todo
        )
        self.close_if_nothing_todo_checkbox.stateChanged.connect(
            self.close_if_nothing_todo_checkbox_stateChanged
        )
        menu_layout.addWidget(self.close_if_nothing_todo_checkbox, 9, 0)

        menu_widget.setLayout(menu_layout)
        main_layout.addWidget(menu_widget)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def command_enable_checkbox_stateChanged(self):
        self.usersettings.command_enabled = self.command_enable_checkbox.isChecked()

    def arena_challenge_mode_combobox_index_changed(self):
        self.usersettings.arena_challenge_mode = (
            self.arena_challenge_mode_combobox.currentIndex()
        )

    def close_if_nothing_todo_checkbox_stateChanged(self):
        self.usersettings.exit_if_nothing_todo = (
            self.close_if_nothing_todo_checkbox.isChecked()
        )

    def serverbattle_rest_num_inputbox_textChanged(self):
        self.usersettings.serverbattle_man.rest_challenge_num_limit = int(
            self.serverbattle_rest_num_inputbox.text()
        )

    def command_setting_btn_clicked(self):
        self.command_setting_window = CommandSettingWindow(
            self.usersettings, parent=self
        )
        self.command_setting_window.show()

    def daily_setting_btn_clicked(self):
        self.daily_setting_window = DailySettingWindow(self.usersettings, self)
        self.daily_setting_window.show()

    def territory_setting_btn_clicked(self):
        self.territory_setting_window = TerritorySettingWindow(
            self.usersettings, parent=self
        )
        self.territory_setting_window.show()

    def garden_setting_btn_clicked(self):
        self.garden_setting_window = GardenChallengeSettingWindow(
            self.usersettings, parent=self
        )
        self.garden_setting_window.show()

    def garden_checkbox_stateChanged(self):
        self.usersettings.garden_enabled = self.garden_checkbox.isChecked()

    def daily_checkbox_stateChanged(self):
        self.usersettings.daily_enabled = self.daily_checkbox.isChecked()

    def territory_checkbox_stateChanged(self):
        self.usersettings.territory_enabled = self.territory_checkbox.isChecked()

    def fuben_checkbox_stateChanged(self):
        self.usersettings.fuben_enabled = self.fuben_checkbox.isChecked()

    def serverbattle_checkbox_stateChanged(self):
        self.usersettings.serverbattle_enabled = self.serverbattle_checkbox.isChecked()

    def millsecond_delay_input_box_valueChanged(self):
        self.usersettings.cfg.millsecond_delay = self.millsecond_delay_input_box.value()

    def max_timeout_input_box_valueChanged(self):
        self.usersettings.cfg.timeout = self.max_timeout_input_box.value()

    def task_setting_checkbox_stateChanged(self):
        self.usersettings.task_enabled = self.task_setting_checkbox.isChecked()

    def arena_checkbox_stateChanged(self):
        self.usersettings.arena_enabled = self.arena_checkbox.isChecked()

    def rest_time_input_box_valueChanged(self, value):
        self.usersettings.rest_time = value

    def fuben_setting_btn_clicked(self):
        self.fuben_setting_window = FubenSettingWindow(self.usersettings, parent=self)
        self.fuben_setting_window.show()

    def shop_auto_buy_setting_btn_clicked(self):
        self.shop_auto_buy_setting_window = ShopAutoBuySetting(
            self.usersettings.cfg,
            self.usersettings.lib,
            self.usersettings.logger,
            self.usersettings.shop_man.shop_auto_buy_dict,
            True,
            parent=self,
        )
        self.shop_auto_buy_setting_window.show()

    def shop_enable_checkbox_stateChanged(self):
        self.usersettings.shop_enabled = self.shop_enable_checkbox.isChecked()

    def main_task_checkbox_stateChanged(self):
        self.usersettings.enable_list[0] = self.main_task_checkbox.isChecked()

    def side_task_checkbox_stateChanged(self):
        self.usersettings.enable_list[1] = self.side_task_checkbox.isChecked()

    def daily_task_checkbox_stateChanged(self):
        self.usersettings.enable_list[2] = self.daily_task_checkbox.isChecked()

    def active_task_checkbox_stateChanged(self):
        self.usersettings.enable_list[3] = self.active_task_checkbox.isChecked()

    # def auto_use_item_checkbox_stateChanged(self):
    #     self.usersettings.auto_use_item_enabled = (
    #         self.auto_use_item_checkbox.isChecked()
    #     )

    def challenge4level_checkbox_stateChanged(self):
        self.usersettings.challenge4Level_enabled = (
            self.challenge4level_checkbox.isChecked()
        )

    def challenge4level_setting_btn_clicked(self):
        self.challenge4level_setting_window = Challenge4levelSettingWindow(
            self.usersettings.cfg,
            self.usersettings.lib,
            self.usersettings.repo,
            self.usersettings.user,
            self.usersettings.logger,
            self.usersettings.challenge4Level,
            parent=self,
        )
        self.challenge4level_setting_window.show()

    def closeEvent(self, a0) -> None:
        self.usersettings.save()
        return super().closeEvent(a0)


class FunctionPanelWindow(QMainWindow):
    def __init__(self, usersettings: UserSettings, parent=None):
        super().__init__(parent=parent)
        self.usersettings = usersettings
        self.init_ui()

    def init_ui(self):
        # 将窗口居中显示，宽度为显示器宽度的50%，高度为显示器高度的70%
        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.5), int(screen_size.height() * 0.7))
        self.move(int(screen_size.width() * 0.25), int(screen_size.height() * 0.15))
        self.setWindowTitle("功能面板")

        main_widget = QWidget()
        main_layout = QHBoxLayout()

        left_panel = QWidget()
        left_panel.setFixedWidth(int(self.width() * 0.2))
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("植物列表"))
        self.plant_list = QListWidget()
        self.plant_list.addItems(
            [
                f"{plant.name(self.usersettings.lib)}({plant.grade})"
                for plant in self.usersettings.repo.plants
            ]
        )
        left_layout.addWidget(self.plant_list)
        left_panel.setLayout(left_layout)
        main_layout.addWidget(left_panel)

        menu_widget = QWidget()
        menu_layout = QGridLayout()
        menu_layout.setHorizontalSpacing(150)
        menu_layout.setVerticalSpacing(60)

        self.auto_use_item_setting_btn = QPushButton("道具面板")
        self.auto_use_item_setting_btn.clicked.connect(
            self.auto_use_item_setting_btn_clicked
        )
        menu_layout.addWidget(self.auto_use_item_setting_btn, 0, 0)

        evolution_panel_btn = QPushButton("进化路线面板")
        evolution_panel_btn.clicked.connect(self.evolution_panel_btn_clicked)
        menu_layout.addWidget(evolution_panel_btn, 0, 1)

        upgrade_quality_btn = QPushButton("升品面板")
        upgrade_quality_btn.clicked.connect(self.upgrade_quality_btn_clicked)
        menu_layout.addWidget(upgrade_quality_btn, 1, 1)

        auto_synthesis_btn = QPushButton("自动合成面板")
        auto_synthesis_btn.clicked.connect(self.auto_synthesis_btn_clicked)
        menu_layout.addWidget(auto_synthesis_btn, 2, 1)

        repository_tool_record_btn = QPushButton("仓库物品记录面板")
        repository_tool_record_btn.clicked.connect(
            self.repository_tool_record_btn_clicked
        )
        menu_layout.addWidget(repository_tool_record_btn, 1, 0)

        heritage_btn = QPushButton("传承面板")
        heritage_btn.clicked.connect(self.heritage_btn_clicked)
        menu_layout.addWidget(heritage_btn, 2, 0)

        compound_btn = QPushButton("自动复合面板")
        compound_btn.clicked.connect(self.compound_btn_clicked)
        menu_layout.addWidget(compound_btn, 3, 1)

        auto_pipeline_btn = QPushButton("全自动面板")
        auto_pipeline_btn.clicked.connect(self.auto_pipeline_btn_clicked)
        menu_layout.addWidget(auto_pipeline_btn, 4, 1)

        plant_relative_btn = QPushButton("植物相关面板")
        plant_relative_btn.clicked.connect(self.plant_relative_btn_clicked)
        menu_layout.addWidget(plant_relative_btn, 3, 0)

        simulate_btn = QPushButton("模拟面板")
        simulate_btn.clicked.connect(self.simulate_btn_clicked)
        menu_layout.addWidget(simulate_btn, 4, 0)

        open_fuben_btn = QPushButton("自动开图面板")
        open_fuben_btn.clicked.connect(self.open_fuben_btn_clicked)
        menu_layout.addWidget(open_fuben_btn, 5, 0)

        menu_widget.setLayout(menu_layout)
        main_layout.addWidget(menu_widget)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def open_fuben_btn_clicked(self):
        self.open_fuben_window = OpenFubenWindow(self.usersettings, parent=self)
        self.open_fuben_window.show()

    def auto_use_item_setting_btn_clicked(self):
        self.auto_use_item_setting_window = AutoUseItemSettingWindow(
            self.usersettings, parent=self
        )
        self.auto_use_item_setting_window.show()

    def simulate_btn_clicked(self):
        self.simulate_window = SimulateWindow(parent=self)
        self.simulate_window.show()

    def auto_pipeline_btn_clicked(self):
        self.auto_pipeline_window = PipelineSettingWindow(
            self.usersettings, parent=self
        )
        self.auto_pipeline_window.show()

    def repository_tool_record_btn_clicked(self):
        self.repository_tool_record_window = RepositoryRecordWindow(
            self.usersettings, parent=self
        )
        self.repository_tool_record_window.show()

    def compound_btn_clicked(self):
        self.compound_window = AutoCompoundWindow(
            self.usersettings.cfg,
            self.usersettings.lib,
            self.usersettings.repo,
            self.usersettings.logger,
            self.usersettings.auto_compound_man,
            parent=self,
        )
        self.compound_window.show()

    def plant_relative_btn_clicked(self):
        self.plant_relative_window = PlantRelativeWindow(self.usersettings, parent=self)
        self.plant_relative_window.show()

    def heritage_btn_clicked(self):
        self.heritage_window = HeritageWindow(self.usersettings, parent=self)
        self.heritage_window.show()

    def upgrade_quality_btn_clicked(self):
        self.upgrade_quality_window = UpgradeQualityWindow(
            self.usersettings, parent=self
        )
        self.upgrade_quality_window.show()

    def evolution_panel_btn_clicked(self):
        self.evolution_panel_window = EvolutionPanelWindow(
            self.usersettings.repo,
            self.usersettings.lib,
            self.usersettings.logger,
            self.usersettings.plant_evolution,
            parent=self,
        )
        self.evolution_panel_window.show()

    def auto_synthesis_btn_clicked(self):
        self.auto_synthesis_window = AutoSynthesisWindow(self.usersettings, parent=self)
        self.auto_synthesis_window.show()

    def closeEvent(self, event):
        self.usersettings.save()
        return super().closeEvent(event)


class CustomMainWindow(QMainWindow):
    logger_signal = pyqtSignal()
    close_signal = pyqtSignal()
    finish_signal = pyqtSignal()

    def __init__(self, usersettings: UserSettings, cache_dir):
        super().__init__()
        self.usersettings = usersettings
        self.close_signal.connect(self.close)
        self.finish_signal.connect(self.stop_prcess)

        self.wr_cache = WebRequest(self.usersettings.cfg, cache_dir=cache_dir)
        self.line_cnt = 0
        self.textbox_lock = threading.Lock()
        self.init_ui()
        self.refresh_user_info()

        self.logger_signal.connect(self.update_text_box)
        self.usersettings.io_logger.set_signal(self.logger_signal)

    def init_ui(self):
        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.6), int(screen_size.height() * 0.7))
        self.move(int(screen_size.width() * 0.2), int(screen_size.height() * 0.15))

        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_widget.setLayout(main_layout)

        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)
        left_panel.setFixedWidth(int(screen_size.width() * 0.13))

        user_show_layout = QHBoxLayout()

        img = Image.open(
            BytesIO(
                self.wr_cache.get_retry(
                    self.usersettings.user.face_url,
                    "获取照片",
                    init_header="pvzol" in self.usersettings.cfg.host,
                    url_format=False,
                    use_cache=True,
                    except_retry=True,
                )
            )
        )
        img = img.resize((64, 64))
        user_face_img = QImage(
            img.tobytes(), img.width, img.height, QImage.Format.Format_RGB888
        )
        user_show_layout.addWidget(QLabel().setPixmap(QPixmap.fromImage(user_face_img)))
        self.user_info_1 = QVBoxLayout()
        self.user_info_1.setSpacing(2)
        user_show_layout.addLayout(self.user_info_1)
        left_layout.addLayout(user_show_layout)

        # Left Panel

        self.user_info_2 = QVBoxLayout()
        self.user_info_2.setSpacing(3)
        # self.user_info_2.setSpacing(5)
        left_layout.addLayout(self.user_info_2)

        # Buttons
        button_layout = QHBoxLayout()
        # button_layout.setSpacing(10)
        self.process_button = process_button = QPushButton("开始")
        process_button.clicked.connect(self.process_button_clicked)
        clear_button = QPushButton("设置")
        clear_button.clicked.connect(self.open_setting_panel)
        button_layout.addWidget(process_button)
        button_layout.addWidget(clear_button)
        left_layout.addLayout(button_layout)

        # function button
        function_panel_open_layout = QHBoxLayout()
        function_panel_open_layout.setSpacing(10)
        self.function_panel_open_button = function_panel_open_button = QPushButton(
            "功能面板"
        )
        function_panel_open_button.clicked.connect(
            self.function_panel_open_button_clicked
        )
        function_panel_open_layout.addWidget(function_panel_open_button)
        left_layout.addLayout(function_panel_open_layout)

        refresh_repository_btn = QPushButton("刷新仓库")
        refresh_repository_btn.clicked.connect(self.refresh_repository_btn)
        left_layout.addWidget(refresh_repository_btn)

        refresh_user_info_btn = QPushButton("刷新用户信息")
        refresh_user_info_btn.clicked.connect(self.refresh_user_info_btn_clicked)
        left_layout.addWidget(refresh_user_info_btn)

        refresh_skill_cache_btn = QPushButton("刷新技能缓存")
        refresh_skill_cache_btn.clicked.connect(self.refresh_skill_cache_btn_clicked)
        left_layout.addWidget(refresh_skill_cache_btn)

        if ENABLE_GAME_WINDOW:
            open_game_window_btn = QPushButton("打开游戏窗口")
            open_game_window_btn.clicked.connect(self.open_game_window)
            left_layout.addWidget(open_game_window_btn)

        left_layout.addStretch(1)
        # left_layout.setSpacing(10)

        # Right Panel
        right_panel = QWidget()
        right_layout = QVBoxLayout()

        # Large Text Box
        self.text_box = text_box = QPlainTextEdit()
        text_box.setReadOnly(True)

        right_layout.addWidget(text_box)
        right_panel.setLayout(right_layout)

        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)
        main_widget.setLayout(main_layout)
        # 设置主窗口常驻屏幕
        # self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)

        self.setCentralWidget(main_widget)
        self.setWindowTitle("Custom Window")

    def open_game_window(self):
        # 遍历config.json文件，找出与当前用户名匹配的cookie，并写出索引
        data = {
            "cookie": self.usersettings.cfg.cookie,
            "username": self.usersettings.user.name,
            "start_url": f"http://{self.usersettings.cfg.host}/pvz/index.php/default/main",
            "host": self.usersettings.cfg.host,
            "port": str(GAME_PORT),
        }
        with open(
            os.path.join(game_window_dir, 'start_config.json'), "w", encoding="utf-8"
        ) as f:
            f.write(json.dumps(data, ensure_ascii=False))
        # start_game_window_proxy()
        exe_path = os.path.join(game_window_dir, 'game_window.exe')
        if not os.path.exists(exe_path):
            logging.error(
                f"找不到游戏窗口程序，可能是因为杀毒程序把对应exe删除了: {exe_path}"
            )
        subprocess.Popen(exe_path)

    def refresh_user_info(self, refresh_all=False):
        delete_layout_children(self.user_info_1)
        delete_layout_children(self.user_info_2)

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = []
            futures.append(
                executor.submit(self.usersettings.territory_man.get_rest_num)
            )
            futures.append(
                executor.submit(self.usersettings.arena_man.get_challenge_num)
            )
            futures.append(executor.submit(self.usersettings.user.get_vip_rest_time))
            if refresh_all:
                futures.append(
                    executor.submit(self.usersettings.repo.refresh_repository)
                )
                futures.append(executor.submit(self.usersettings.user.refresh()))
        concurrent.futures.wait(futures, return_when=concurrent.futures.ALL_COMPLETED)

        self.user_info_1.addWidget(QLabel(f"{self.usersettings.user.name}"))
        self.user_info_1.addWidget(QLabel(f"等级: {self.usersettings.user.grade}"))
        self.user_info_1.addWidget(
            QLabel(
                f"经验值: {self.usersettings.user.exp_now}/{self.usersettings.user.exp_max}"
            )
        )
        self.user_info_2.addWidget(
            QLabel(
                f"今日经验: {self.usersettings.user.today_exp} / {self.usersettings.user.today_exp_max}"
            )
        )
        self.user_info_2.addWidget(
            QLabel(
                f"挑战次数: {self.usersettings.user.cave_amount} / {self.usersettings.user.cave_amount_max}"
            )
        )
        self.user_info_2.addWidget(QLabel("领地次数: {}".format(futures[0].result())))
        self.user_info_2.addWidget(QLabel("竞技场次数: {}".format(futures[1].result())))
        self.user_info_2.addWidget(
            QLabel("vip剩余天数: {}".format(futures[2].result()))
        )
        QApplication.processEvents()

    def refresh_skill_cache_btn_clicked(self):
        try:
            wr = WebRequest(self.usersettings.cfg)
            futures = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                futures.append(
                    executor.submit(
                        wr.amf_post_retry,
                        [],
                        "api.apiskill.getAllSkills",
                        "/pvz/amf/",
                        "获取专属技能信息",
                    )
                )
                futures.append(
                    executor.submit(
                        wr.amf_post_retry,
                        [],
                        "api.apiskill.getSpecSkillAll",
                        "/pvz/amf/",
                        "获取专属技能信息",
                    )
                )

            concurrent.futures.wait(
                futures, return_when=concurrent.futures.ALL_COMPLETED
            )

            skills_resp = futures[0].result()
            spec_skills_resp = futures[1].result()
            assert skills_resp.status == 0, f"获取技能信息失败: {skills_resp}"
            assert (
                spec_skills_resp.status == 0
            ), f"获取专属技能信息失败: {spec_skills_resp}"
            skills = skills_resp.body
            spec_skills = spec_skills_resp.body
            with open("data/cache/pvz/skills.json", mode="w", encoding="utf-8") as f:
                json.dump(skills, f, ensure_ascii=False)
            self.usersettings.logger.log("刷新普通技能缓存成功")
            with open("data/cache/pvz/spec_skills.json", mode="w", encoding="utf-8") as f:
                json.dump(spec_skills, f, ensure_ascii=False)
            self.usersettings.logger.log("刷新专属技能缓存成功")
        except Exception as e:
            self.usersettings.logger.log(f"刷新技能缓存失败: {e}")
        else:
            self.usersettings.logger.log(
                "刷新普通技能和专属技能缓存成功，该刷新是全局的，每个用户共享同一缓存，只需要刷新一遍即可"
            )

    def refresh_user_info_btn_clicked(self):
        self.refresh_user_info(refresh_all=True)
        self.usersettings.logger.log("用户信息刷新完成")

    def update_text_box(self):
        if self.textbox_lock.locked():
            return
        self.textbox_lock.acquire()
        result = self.usersettings.io_logger.get_new_infos()
        document = self.text_box.document()
        # 冻结text_box显示，直到document更新完毕后更新
        self.text_box.viewport().setUpdatesEnabled(False)
        cursor = QTextCursor(document)
        for info_item in reversed(result):
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            if isinstance(info_item, str):
                cursor.insertText(info_item + "\n")
                self.line_cnt += 1
                continue
            for msg, color in info_item:
                if color is None:
                    color = (0, 0, 0)
                if len(color) == 3:
                    color = color + (255,)
                if len(color) == 4 and isinstance(color[3], float):
                    color[3] = int(color[3] * 255)
                qcolor = QColor(*color)
                text_format = QTextCharFormat()
                text_format.setForeground(qcolor)
                cursor.insertText(msg, text_format)
            cursor.insertText("\n")
            self.line_cnt += 1
            # self.text_box.insertPlainText(info + "\n")
        while self.line_cnt > self.usersettings.io_logger.max_info_capacity:
            cursor = QTextCursor(document)
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.movePosition(QTextCursor.MoveOperation.Up)
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()
            self.line_cnt -= 1
        self.text_box.viewport().setUpdatesEnabled(True)
        self.text_box.viewport().update()
        self.textbox_lock.release()

    def open_setting_panel(self):
        self.settingWindow = SettingWindow(self.usersettings, parent=self)
        self.settingWindow.show()

    def refresh_repository_btn(self):
        self.usersettings.repo.refresh_repository()
        self.usersettings.logger.log("仓库刷新完成")

    def start_process(self):
        self.process_button.setText("暂停")
        while self.usersettings.stop_channel.qsize() > 0:
            self.usersettings.stop_channel.get()
        self.usersettings.logger.log("开始运行")
        self.usersettings.start(self.close_signal, self.finish_signal)

    def stop_prcess(self):
        self.process_button.setText("开始")
        self.usersettings.stop_channel.put(True)

    def process_button_clicked(self):
        if self.process_button.text() == "开始":
            self.start_process()
        elif self.process_button.text() == "暂停":
            self.stop_prcess()
        else:
            raise ValueError(f"Unknown button text: {self.process_button.text()}")

    def function_panel_open_button_clicked(self):
        self.function_panel_window = FunctionPanelWindow(self.usersettings, parent=self)
        self.function_panel_window.show()

    def closeEvent(self, event):
        self.usersettings.stop_channel.put(True)
        self.usersettings.io_logger.close()
        try:
            logger_list.remove(self.usersettings.io_logger)
        except ValueError:
            pass
        self.usersettings.save()
        try:
            main_window_list.remove(self)
        except ValueError:
            pass
        return super().closeEvent(event)


class ProxyManagerWindow(QMainWindow):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.init_ui()
        self.item_id = None

    def init_ui(self):
        self.setWindowTitle("网络管理面板")

        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.5), int(screen_size.height() * 0.7))
        self.move(int(screen_size.width() * 0.25), int(screen_size.height() * 0.13))

        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("代理列表"))
        self.proxy_list = QListWidget()
        self.proxy_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.proxy_list.itemPressed.connect(self.proxy_list_item_clicked)
        layout.addWidget(self.proxy_list)
        main_layout.addLayout(layout)
        self.refresh_proxy_list()

        layout = QVBoxLayout()
        layout.addStretch(1)
        layout.setSpacing(10)

        self.use_dns_cache = QCheckBox("使用DNS缓存")
        self.use_dns_cache.setChecked(proxy_man.use_dns_cache)
        self.use_dns_cache.stateChanged.connect(self.use_dns_cache_stateChanged)
        layout.addWidget(self.use_dns_cache)

        layout1 = QHBoxLayout()
        layout1.addWidget(QLabel("代理地址:"))
        self.proxy_add_input = QTextEdit()
        layout1.addWidget(self.proxy_add_input)
        layout.addLayout(layout1)

        layout1 = QHBoxLayout()
        layout1.addWidget(QLabel("该代理最高并发量:"))
        self.proxy_max_use_amount = QComboBox()
        self.proxy_max_use_amount.addItems([str(i) for i in range(101)])
        self.proxy_max_use_amount.setCurrentText(str(3))
        self.proxy_max_use_amount.setValidator(QtGui.QIntValidator())
        layout1.addWidget(self.proxy_max_use_amount)
        layout.addLayout(layout1)
        add_proxy_btn = QPushButton("添加代理")
        add_proxy_btn.clicked.connect(self.add_proxy)
        layout.addWidget(add_proxy_btn)

        layout1 = QHBoxLayout()
        layout1.addWidget(QLabel("测试次数(最大10):"))
        self.test_times = QLineEdit()
        self.test_times.setValidator(QtGui.QIntValidator(1, 10))
        self.test_times.setText("5")
        self.test_times.textChanged.connect(self.test_times_textChanged)
        layout1.addWidget(self.test_times)
        remove_proxy_btn = QPushButton("测试已添加代理")
        remove_proxy_btn.clicked.connect(self.test_proxy)
        layout1.addWidget(remove_proxy_btn)
        layout.addLayout(layout1)

        export_proxy_btn = QPushButton("导出已添加代理")
        export_proxy_btn.clicked.connect(self.export_proxy)
        layout.addWidget(export_proxy_btn)

        self.block_when_no_proxy_checkbox = QCheckBox(
            "没有空闲代理时阻塞(不阻塞则本地直连无限制并发)"
        )
        self.block_when_no_proxy_checkbox.setChecked(proxy_man.block_when_no_proxy)
        self.block_when_no_proxy_checkbox.stateChanged.connect(
            self.block_when_no_proxy_checkbox_changed
        )
        layout.addWidget(self.block_when_no_proxy_checkbox)

        reset_btn = QPushButton("重置代理池")
        reset_btn.clicked.connect(self.reset_btn_clicked)
        layout.addWidget(reset_btn)

        self.proxy_max_use_amount_edit = QComboBox()
        self.proxy_max_use_amount_edit.addItems([str(i) for i in range(101)])
        self.proxy_max_use_amount_edit.setDisabled(True)
        layout.addWidget(self.proxy_max_use_amount_edit)

        set_proxy_max_use_amount_btn = QPushButton("设置该代理最大并发量")
        set_proxy_max_use_amount_btn.clicked.connect(
            self.set_proxy_item_max_use_count_btn_cliked
        )
        layout.addWidget(set_proxy_max_use_amount_btn)

        warning_label = QLabel(
            "-----使用须知-----\n"
            "1. 默认状态是本地直连无限制并发\n"
            "2. 打开DNS缓存可能可以解决ReadTimeout和ConnectError问题\n"
            "3. 代理池原理是均分并发\n"
            "4. 代理地址格式为\"ip:port\"，例如127.0.0.1:8080\n"
            "5. 以上设置均为全局设置"
        )
        layout.addWidget(warning_label)

        layout.addStretch(1)
        main_layout.addLayout(layout)

    def save(self):
        proxy_man.save(proxy_man_save_path)

    def use_dns_cache_stateChanged(self):
        proxy_man.use_dns_cache = self.use_dns_cache.isChecked()
        self.save()

    def test_times_textChanged(self):
        text = self.test_times.text()
        if text:
            value = int(text)
            if value < 1 or value > 10:
                self.test_times.setText(str(max(1, min(value, 10))))

    def proxy_list_item_clicked(self):
        selected_item = self.proxy_list.currentItem()
        if selected_item is None:
            logging.warning("未选中代理")
            return
        item_id = selected_item.data(Qt.ItemDataRole.UserRole)
        item = proxy_man.get_item(item_id)
        if item is None:
            logging.error("选中代理解析出错，请考虑重置代理池")
            return
        self.item_id = item_id
        self.proxy_max_use_amount_edit.setCurrentText(str(item.max_use_count))
        self.proxy_max_use_amount_edit.setEnabled(True)

    def block_when_no_proxy_checkbox_changed(self):
        proxy_man.block_when_no_proxy = self.block_when_no_proxy_checkbox.isChecked()
        self.save()

    def refresh_proxy_list(self):
        self.proxy_list.clear()
        for proxy_item in proxy_man.proxy_item_list:
            item = QListWidgetItem()
            item.setText(str(proxy_item))
            item.setData(Qt.ItemDataRole.UserRole, proxy_item.item_id)
            self.proxy_list.addItem(item)

    def reset_btn_clicked(self):
        proxy_man.reset_proxy_list()
        self.save()
        self.refresh_proxy_list()

    def add_tunnel_proxy(self):
        pass

    def test_proxy(self):
        def test_proxy_thread(proxy_item):
            alive = test_proxy_alive(
                proxy_item.proxy, proxy_item.item_id, int(self.test_times.text())
            )
            # logging.info("代理地址：{} {}".format(proxy_item.proxy, alive))

        threads = []
        for proxy_item in proxy_man.proxy_item_list:
            if proxy_item.item_id == -1:  # 本地
                continue

            thread = threading.Thread(target=test_proxy_thread, args=(proxy_item,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        self.save()
        self.refresh_proxy_list()

    def export_proxy(self):
        with open("proxy.txt", "w") as f:
            for proxy_item in proxy_man.proxy_item_list:
                if proxy_item.item_id == -1:  # 本地
                    continue
                f.write(proxy_item.proxy + "\n")

            logging.info("导出完成")

    def add_proxy(self):
        proxy_error_msg = '格式出错，应当是"ip:port"的形式，同时只支持ipv4'
        # 多行
        proxy_text_split = self.proxy_add_input.toPlainText().split("\n")
        for proxy_text in proxy_text_split:
            proxy_text = proxy_text.strip()
            max_use_amount = int(self.proxy_max_use_amount.currentText())
            splited = proxy_text.split(":")
            if len(splited) != 2:
                logging.error(proxy_text + proxy_error_msg)
                continue
            ip, port = splited
            try:
                port = int(port)
                assert port >= 0 and port < 2**16
            except:
                logging.error(proxy_text + proxy_error_msg)
                continue
            splited = ip.split(".")
            if len(splited) != 4:
                logging.error(proxy_text + proxy_error_msg)
                continue
            try:
                for part in splited:
                    int_part = int(part)
                    assert int_part >= 0 and int_part < 2**8
            except:
                logging.error(proxy_text + proxy_error_msg)
                continue
            proxy_man.add_proxy_item(proxy_text, max_use_count=max_use_amount)
        self.save()
        self.refresh_proxy_list()

    def delete_proxy_item(self, item_id):
        proxy_man.delete_proxy_item(item_id)
        self.save()

    def move_up(self, item_id):
        proxy_man.move_up_item(item_id)
        self.save()

    def move_down(self, item_id):
        proxy_man.move_down_item(item_id)
        self.save()

    def set_proxy_item_max_use_count_btn_cliked(self):
        if self.item_id is None:
            logging.warning("未选中代理")
            return
        max_use_amount = int(self.proxy_max_use_amount_edit.currentText())
        proxy_man.set_item_max_use_count(self.item_id, max_use_count=max_use_amount)
        self.save()
        self.refresh_proxy_list()

    def keyPressEvent(self, event):
        if (
            event.key() == Qt.Key.Key_Backspace
            or event.key() == Qt.Key.Key_Delete
            or event.key() == Qt.Key.Key_Up
            or event.key() == Qt.Key.Key_Down
        ):
            selected_item = self.proxy_list.currentItem()
            if selected_item is None:
                logging.warning("未选中代理列表内容")
                return
            item_id = selected_item.data(Qt.ItemDataRole.UserRole)
            if event.key() == Qt.Key.Key_Backspace or event.key() == Qt.Key.Key_Delete:
                self.delete_proxy_item(item_id)
                self.proxy_max_use_amount_edit.setDisabled(True)
                self.item_id = None
            elif event.key() == Qt.Key.Key_Up:
                self.move_up(item_id)
            elif event.key() == Qt.Key.Key_Down:
                self.move_down(item_id)
            self.refresh_proxy_list()


class LoginWindow(QMainWindow):
    get_usersettings_finish_signal = pyqtSignal(tuple)
    get_usersettings_finish_export_signal = pyqtSignal(tuple)
    get_usersettings_finish_import_signal = pyqtSignal(tuple)

    def __init__(self):
        super().__init__()
        self.configs = []
        self.cfg_path = os.path.join(root_dir, "data/config/config.json")
        if os.path.exists(self.cfg_path):
            with open(self.cfg_path, "r", encoding="utf-8") as f:
                self.configs = json.load(f)
        self.init_ui()
        self.refresh_login_user_list()
        self.get_usersettings_finish_signal.connect(self.get_usersettings_finished)
        self.get_usersettings_finish_export_signal.connect(
            self.get_usersettings_finished_export
        )
        self.get_usersettings_finish_import_signal.connect(
            self.get_usersettings_finished_import
        )
        self.export_save_dir = os.path.join(root_dir, "导出的用户数据")
        self.main_window_thread = []
        self.game_queue = None

    def init_ui(self):
        self.setWindowTitle("登录")

        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.3), int(screen_size.height() * 0.8))
        self.move(int(screen_size.width() * 0.35), int(screen_size.height() * 0.075))

        main_widget = QWidget()
        main_layout = QVBoxLayout()

        layout = QHBoxLayout()
        layout.addWidget(QLabel("当前版本: pre32"))
        self.import_data_from_old_version_btn = QPushButton("从旧版本导入数据")
        self.import_data_from_old_version_btn.clicked.connect(
            self.import_data_from_old_version_btn_clicked
        )
        layout.addWidget(self.import_data_from_old_version_btn)
        layout.addStretch(1)
        main_layout.addLayout(layout)

        login_user_widget = QWidget()
        login_user_layout = QVBoxLayout()
        login_user_layout.addWidget(
            QLabel("已登录的用户(双击登录，选中按delete或backspace删除)")
        )
        self.login_user_list = login_user_list = QListWidget()
        login_user_list.itemDoubleClicked.connect(self.login_list_item_double_clicked)
        login_user_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        login_user_layout.addWidget(login_user_list)
        login_user_widget.setLayout(login_user_layout)
        main_layout.addWidget(login_user_widget)

        pack_deal_widget = QWidget()
        pack_deal_layout = QHBoxLayout()
        login_all_btn = QPushButton("登录选中用户")
        login_all_btn.clicked.connect(self.login_all_btn_clicked)
        pack_deal_layout.addWidget(login_all_btn)
        start_all_user_btn = QPushButton("开始所有用户")
        start_all_user_btn.clicked.connect(self.start_all_user_btn_clicked)
        pack_deal_layout.addWidget(start_all_user_btn)
        stop_all_user_btn = QPushButton("停止所有用户")
        stop_all_user_btn.clicked.connect(self.stop_all_user_btn_clicked)
        pack_deal_layout.addWidget(stop_all_user_btn)
        close_all_user_btn = QPushButton("关闭所有用户")
        close_all_user_btn.clicked.connect(self.close_all_user_btn_clicked)
        pack_deal_layout.addWidget(close_all_user_btn)
        # game_start_btn = QPushButton("启动选中用户游戏")
        # game_start_btn.clicked.connect(self.game_start_btn_clicked)
        # pack_deal_layout.addWidget(game_start_btn)
        pack_deal_widget.setLayout(pack_deal_layout)
        main_layout.addWidget(pack_deal_widget)

        layout = QHBoxLayout()
        proxy_manager_window_btn = QPushButton("网络面板")
        proxy_manager_window_btn.clicked.connect(self.proxy_manager_window_btn_clicked)
        layout.addWidget(proxy_manager_window_btn)
        main_layout.addLayout(layout)

        username_widget = QWidget()
        username_layout = QHBoxLayout()
        username_layout.addWidget(QLabel("用户名(这个随便填):"))
        self.username_input = username_input = QLineEdit()
        username_layout.addWidget(username_input)
        username_widget.setLayout(username_layout)
        main_layout.addWidget(username_widget)

        region_widget = QWidget()
        region_layout = QHBoxLayout()
        region_layout.addWidget(QLabel("区服:"))
        self.region_input = region_input = QComboBox()
        # region_input.addItems([f"官服{i}区" for i in range(12, 46 + 1)])
        region_input.addItems([f"私服{i}区" for i in range(1, 10)])
        region_input.addItem("测试服")
        region_layout.addWidget(region_input)
        region_widget.setLayout(region_layout)
        main_layout.addWidget(region_widget)

        layout = QHBoxLayout()
        cookie_widget = QWidget()
        cookie_layout = QHBoxLayout()
        cookie_layout.addWidget(QLabel("Cookie:"))
        self.cookie_input = cookie_input = QLineEdit()
        cookie_layout.addWidget(cookie_input)
        cookie_widget.setLayout(cookie_layout)
        layout.addWidget(cookie_widget)
        self.import_cookie_btn = QPushButton("从文件导入")
        self.import_cookie_btn.clicked.connect(self.import_cookie_btn_clicked)
        layout.addWidget(self.import_cookie_btn)
        main_layout.addLayout(layout)

        login_btn = QPushButton("登录")
        login_btn.clicked.connect(self.login_btn_clicked)
        main_layout.addWidget(login_btn)

        main_layout.addStretch(1)

        server_layout = QVBoxLayout()
        server_layout.setSpacing(1)
        server_layout.addWidget(QLabel("-" * 60))
        server_layout.addWidget(
            QLabel("浏览器访问bwnotfound.com即可配置云端助手一键挂机")
        )
        server_layout.addWidget(
            QLabel(
                '导出的用户配置文件在点击导出后存放在助手文件夹下的"导出的用户数据"中'
            )
        )
        server_layout.addWidget(QLabel("注意：载入用户配置不会覆盖已有用户配置"))

        server_op_btn_layout = QHBoxLayout()
        self.export_usersettings_config_btn = QPushButton("导出选中用户配置")
        self.export_usersettings_config_btn.clicked.connect(
            self.export_usersettings_config_btn_clicked
        )
        server_op_btn_layout.addWidget(self.export_usersettings_config_btn)
        self.import_usersettings_config_btn = QPushButton("载入用户配置")
        self.import_usersettings_config_btn.clicked.connect(
            self.import_usersettings_config_btn_clicked
        )
        server_op_btn_layout.addWidget(self.import_usersettings_config_btn)
        server_op_btn_layout.addStretch(1)
        server_layout.addLayout(server_op_btn_layout)
        main_layout.addLayout(server_layout)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def proxy_manager_window_btn_clicked(self):
        window = ProxyManagerWindow(parent=self)
        window.show()

    def import_cookie_btn_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择cookie文件",
            os.path.join(os.path.expanduser("~"), "Desktop"),
            "All Files (*)",
        )
        if file_path is None or len(file_path) == 0:
            return
        if file_path and os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                cookie = f.read()
            cookie = self.filter_cookie(cookie)
            self.cookie_input.setText(cookie)

    def import_data_from_old_version_btn_clicked(self):
        # 唤起文件浏览器，让用户选中一个文件夹，默认位置为桌面
        import shutil

        root_dir = os.getcwd()
        old_version_data_dir = QFileDialog.getExistingDirectory(
            self,
            "选择旧版本数据文件夹",
            os.path.join(os.path.expanduser("~"), "Desktop"),
        )
        if old_version_data_dir is None or len(old_version_data_dir) == 0:
            return
        file_name_list = os.listdir(old_version_data_dir)
        if "data" in file_name_list:
            old_version_data_dir = os.path.join(old_version_data_dir, "data")
        else:
            if os.path.basename(old_version_data_dir) != "data":
                logging.warning("未找到data文件夹")
                return
        file_name_list = os.listdir(old_version_data_dir)
        if "config" in file_name_list:
            shutil.copytree(
                os.path.join(old_version_data_dir, "config"),
                os.path.join(root_dir, "data/config"),
                dirs_exist_ok=True,
            )
        if "user" in file_name_list:
            shutil.copytree(
                os.path.join(old_version_data_dir, "user"),
                os.path.join(root_dir, "data/user"),
                dirs_exist_ok=True,
            )
        self.cfg_path = os.path.join(root_dir, "data/config/config.json")
        if os.path.exists(self.cfg_path):
            with open(self.cfg_path, "r", encoding="utf-8") as f:
                self.configs = json.load(f)
        self.refresh_login_user_list()

    def export_usersettings_config_btn_clicked(self):
        cfg_indices = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self.login_user_list.selectedItems()
        ]
        if len(cfg_indices) == 0:
            logging.warning("未选中任何用户")
            return
        self.export_usersettings_config_btn.setDisabled(True)
        QApplication.processEvents()
        self.export_rest_count = len(cfg_indices)
        self._export_rest_count_lock = threading.Lock()
        for cfg_index in cfg_indices:
            cfg = Config(self.configs[cfg_index])
            GetUsersettings(
                cfg, root_dir, self.get_usersettings_finish_export_signal
            ).start()

    def get_usersettings_finished_export(self, args):
        usersettings, cache_dir = args
        assert isinstance(usersettings, UserSettings)
        os.makedirs(self.export_save_dir, exist_ok=True)
        save_info = "{}_{}{}区".format(
            usersettings.cfg.username,
            usersettings.cfg.server,
            usersettings.cfg.region,
        )
        save_path = os.path.join(self.export_save_dir, f"{save_info}.bin")
        usersettings.export_data(save_path)
        logging.info(f"导出用户配置: {save_info}")
        with self._export_rest_count_lock:
            self.export_rest_count -= 1
            if self.export_rest_count == 0:
                self.export_rest_count = None
                self._export_rest_count_lock = None
                logging.info("用户配置已导出完毕")
                self.export_usersettings_config_btn.setEnabled(True)
                QApplication.processEvents()

    def import_usersettings_config_btn_clicked(self):
        if not os.path.exists(self.export_save_dir):
            logging.warning('请将需要导入的用户配置文件放在"导出的用户数据"文件夹中')
            return
        file_list = os.listdir(self.export_save_dir)
        if len(file_list) == 0:
            logging.warning('"导出的用户数据"文件夹中没有可导入的用户配置文件')
            return
        self.import_usersettings_config_btn.setDisabled(True)
        QApplication.processEvents()
        self._import_rest_count_lock = threading.Lock()
        self.import_rest_count = len(file_list)
        for file_name in file_list:
            file_path = os.path.join(self.export_save_dir, file_name)
            if not os.path.isfile(file_path):
                continue
            with open(file_path, "rb") as f:
                data_bin = f.read()
            data = pickle.loads(data_bin)
            config, data = data["config"], data["data"]
            cfg = Config(config)
            GetUsersettings(
                cfg, root_dir, self.get_usersettings_finish_import_signal, data
            ).start()

    def get_usersettings_finished_import(self, args):
        usersettings, cache_dir, data = args
        assert isinstance(usersettings, UserSettings)
        usersettings.import_data(data)
        usersettings.save()
        user_info = "{}_{}{}区".format(
            usersettings.cfg.username,
            usersettings.cfg.server,
            usersettings.cfg.region,
        )
        for cfg in self.configs:
            if (
                cfg["username"] == usersettings.cfg.username
                and cfg["host"] == usersettings.cfg.host
                and cfg["region"] == usersettings.cfg.region
                and cfg["server"] == usersettings.cfg.server
            ):
                logging.info(f"已有用户配置，选择跳过: {user_info}")
                break
        else:
            self.configs.append(usersettings.cfg.config)
            logging.info(f"导入用户配置: {user_info}")
        with self._import_rest_count_lock:
            self.import_rest_count -= 1
            if self.import_rest_count == 0:
                self.import_rest_count = None
                self._import_rest_count_lock = None
                logging.info("用户配置已导入完毕")
                self.save_config()
                self.refresh_login_user_list()
                self.import_usersettings_config_btn.setEnabled(True)
                QApplication.processEvents()

    # def start_game_window(self, index):
    #     cfg = Config(self.configs[index])
    #     if self.game_queue is None:
    #         self.game_queue = multiprocessing.Queue(maxsize=16)
    #         multiprocessing.Process(target=run_game_window, args=(self.game_queue,)).start()
    #     self.game_queue.put((cfg.cookie, 1.5))
    #     print(self.game_queue.qsize())

    # def game_start_btn_clicked(self):
    #     selected_index = [
    #         self.login_user_list.indexFromItem(item).row()
    #         for item in self.login_user_list.selectedItems()
    #     ]
    #     for index in selected_index:
    #         self.start_game_window(index)

    def login_all_btn_clicked(self):
        selected_index = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self.login_user_list.selectedItems()
        ]
        for index in selected_index:
            self.login(index)

    def start_all_user_btn_clicked(self):
        for main_window in main_window_list:
            main_window.start_process()

    def stop_all_user_btn_clicked(self):
        for main_window in main_window_list:
            main_window.stop_prcess()

    def close_all_user_btn_clicked(self):
        copy_list = [main_window for main_window in main_window_list]
        for main_window in copy_list:
            main_window.close()

    def filter_cookie(self, cookie):
        if cookie is None or len(cookie) == 0:
            return ""
        if cookie[0] == '"' and cookie[-1] == '"':
            cookie = cookie[1:]
        if cookie[0] == "'" and cookie[-1] == "'":
            cookie = cookie[:-1]
        if len(cookie) < 1000:
            if "pvzol" in cookie:
                cookie = cookie[cookie.find("pvzol") + len("pvzol=") :]
            if "=" in cookie:
                cookie = cookie[cookie.find("=") + 1 :]
            if "<" in cookie:
                cookie = cookie[: cookie.find("<")]
        else:
            cookie = cookie[cookie.find("UserCookies") + len("UserCookies>pvzol=") :]
            cookie = cookie[: cookie.find("<")]
        if len(cookie) == 0:
            return cookie
        cookie = "pvzol=" + cookie
        return cookie

    def login_btn_clicked(self):
        # 取出当前选中的用户
        username = self.username_input.text()
        region_text = self.region_input.currentText()
        cookie = self.cookie_input.text()
        cookie = self.filter_cookie(cookie)
        self.cookie_input.setText(cookie)
        if len(username) == 0:
            logging.warning("请先输入用户名")
            return
        if len(cookie) == 0:
            logging.warning("请输入cookie或从cookie文件导入")
            return
        if region_text == "测试服":
            region = 1
        else:
            region = int(region_text[2:-1])
        if region_text.startswith("官服"):
            host = f"s{region}.youkia.pvz.youkia.com"
            server = "官服"
        elif region_text.startswith("私服"):
            host = "pvzol.org"
            server = "私服"
        elif region_text == "测试服":
            host = "test.pvzol.org"
            server = "私服"
        else:
            raise ValueError(f"Unknown region text: {region_text}")
        cfg = {
            "username": username,
            "host": host,
            "region": region,
            "cookie": cookie,
            "server": server,
        }
        for i, saved_cfg in enumerate(self.configs):
            if (
                saved_cfg["username"] == cfg["username"]
                and saved_cfg["host"] == cfg["host"]
                and saved_cfg["region"] == cfg["region"]
                and saved_cfg["server"] == cfg["server"]
            ):
                self.configs[i]["cookie"] = cfg["cookie"]
                break
        else:
            self.configs.append(cfg)
        self.save_config()
        self.refresh_login_user_list()
        QApplication.processEvents()
        self.create_main_window(Config(cfg))

    def login(self, index):
        self.create_main_window(Config(self.configs[index]))

    def login_list_item_double_clicked(self, item):
        cfg_index = item.data(Qt.ItemDataRole.UserRole)
        self.login(cfg_index)

    def create_main_window(self, cfg: Config):
        thread = GetUsersettings(cfg, root_dir, self.get_usersettings_finish_signal)
        self.main_window_thread.append(thread)
        thread.start()

    def get_usersettings_finished(self, args):
        main_window = CustomMainWindow(*args)
        main_window_list.append(main_window)
        main_window.show()
        QApplication.processEvents()

    def refresh_login_user_list(self):
        self.login_user_list.clear()
        for i, cfg in enumerate(self.configs):
            item = QListWidgetItem(
                "{}_{}_{}".format(cfg["username"], cfg["region"], cfg["host"])
            )
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.login_user_list.addItem(item)

    def save_config(self):
        with open(self.cfg_path, "w", encoding="utf-8") as f:
            json.dump(self.configs, f, indent=4, ensure_ascii=False)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Backspace or event.key() == Qt.Key.Key_Delete:
            if len(self.login_user_list.selectedItems()) == 0:
                logging.warning("未选中任何用户")
                return
            cfg_indices = [
                item.data(Qt.ItemDataRole.UserRole)
                for item in self.login_user_list.selectedItems()
            ]
            new_configs = []
            for i in range(len(self.configs)):
                if i not in cfg_indices:
                    new_configs.append(self.configs[i])
                else:
                    logging.info(f"删除用户: {self.configs[i]['username']}")
                    user_path = os.path.join(
                        root_dir,
                        f"data/user/{self.configs[i]['username']}",
                    )
                    try:
                        shutil.rmtree(
                            os.path.join(user_path, f"{self.configs[i]['region']}")
                        )
                        if len(os.listdir(user_path)) == 0:
                            shutil.rmtree(user_path)
                    except:
                        pass
            self.configs = new_configs
            self.save_config()
            self.refresh_login_user_list()

    def closeEvent(self, event):
        if self.game_queue is not None:
            self.game_queue.put_nowait(None)
        return super().closeEvent(event)


class GetUsersettings(threading.Thread):
    def __init__(self, cfg: Config, root_dir, finish_trigger, *args):
        super().__init__()
        self.cfg = cfg
        self.root_dir = root_dir
        self.finish_trigger = finish_trigger
        self.args = args

    def run(self):
        data_dir = os.path.join(
            self.root_dir,
            f"data/user/{self.cfg.username}/{self.cfg.region}/{self.cfg.host}",
        )
        os.makedirs(data_dir, exist_ok=True)
        cache_dir = os.path.join(data_dir, "cache")
        os.makedirs(cache_dir, exist_ok=True)
        log_dir = os.path.join(data_dir, "log")
        os.makedirs(log_dir, exist_ok=True)
        setting_dir = os.path.join(data_dir, "usersettings")
        os.makedirs(setting_dir, exist_ok=True)

        max_info_capacity = 500
        # TODO: 从配置文件中读取
        logger = IOLogger(log_dir, max_info_capacity=max_info_capacity)
        logger_list.append(logger)
        usersettings = get_usersettings(self.cfg, logger, setting_dir)
        self.finish_trigger.emit((usersettings, cache_dir, *self.args))


def get_usersettings(cfg: Config, logger: IOLogger, setting_dir):
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = []
        futures.append(executor.submit(User, cfg))
        futures.append(executor.submit(Library, cfg))
        futures.append(executor.submit(Repository, cfg))

    concurrent.futures.wait(futures, return_when=concurrent.futures.ALL_COMPLETED)

    user: User = futures[0].result()
    lib: Library = futures[1].result()
    repo: Repository = futures[2].result()

    usersettings = UserSettings(
        cfg,
        repo,
        lib,
        user,
        logger,
        setting_dir,
    )
    if not os.path.exists(setting_dir):
        os.mkdir(setting_dir)
        usersettings.save()
    else:
        usersettings.load()

    return usersettings


if __name__ == "__main__":
    multiprocessing.freeze_support()
    # 解析命令行，获取debug参数
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="debug模式")
    ENABLE_GAME_WINDOW = False
    args = parser.parse_args()
    DEBUG = False
    if args.debug:
        DEBUG = True
    GAME_PORT = 20413
    # 设置logging监听等级为INFO
    logging.basicConfig(
        level=logging.INFO
    )  # 如果不想让控制台输出那么多信息，可以将这一行注释掉
    # 取root_dir为可执行文件的目录
    root_dir = os.getcwd()
    data_dir = os.path.join(root_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(os.path.join(data_dir, "config"), exist_ok=True)
    CACHE_DIR = os.path.join(data_dir, "cache")
    proxy_man_save_path = os.path.join(data_dir, "config", "proxy.bin")
    if ENABLE_GAME_WINDOW:
        GameWindowProxyServer(CACHE_DIR, GAME_PORT).start()
    # start_game_window_proxy()

    if ENABLE_GAME_WINDOW:
        if DEBUG:
            game_window_dir = os.path.join(root_dir, "game_window/build")
        else:
            game_window_dir = os.path.join(root_dir, "game_window/")

    if os.path.exists(proxy_man_save_path):
        try:
            proxy_man.load(proxy_man_save_path)
        except Exception as e:
            logging.warning(f"代理配置文件解析错误，Exception: {str(e)}")

    try:
        app = QApplication(sys.argv)
        logger_list = []
        main_window_list: list[CustomMainWindow] = []
        login_window = LoginWindow()
        login_window.show()
        app_return = app.exec()
    except Exception as e:
        print(str(e))
    for log in logger_list:
        log.close()
    for main_window in main_window_list:
        main_window.usersettings.save()
    os.system("pause")
    sys.exit(app_return)
