import sys
import json
from io import BytesIO
import os
import logging
import concurrent.futures
import threading
import shutil

from PyQt6 import QtGui
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTabWidget,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QGridLayout,
    QCheckBox,
    QPlainTextEdit,
    QSpinBox,
    QComboBox,
    QLineEdit,
)
from PyQt6.QtGui import QImage, QPixmap, QTextCursor
from PyQt6.QtCore import Qt, pyqtSignal
from PIL import Image

from pypvz import WebRequest, Config, User, Repository, Library
from pypvz.ui.message import IOLogger
from pypvz.ui.wrapped import QLabel, normal_font
from pypvz.ui.windows.common import (
    AutoUseItemSettingWindow,
    HeritageWindow,
    PlantRelativeWindow,
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
    # GameWindow,
    # run_game_window,
)


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
        challenge4level_checkbox.setFont(normal_font)
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
        self.fuben_checkbox = fuben_checkbox = QCheckBox("副本")
        fuben_checkbox.setFont(normal_font)
        fuben_checkbox.setChecked(self.usersettings.fuben_enabled)
        fuben_checkbox.stateChanged.connect(self.fuben_checkbox_stateChanged)
        fuben_layout.addWidget(fuben_checkbox)
        fuben_setting_btn = QPushButton("设置")
        fuben_setting_btn.clicked.connect(self.fuben_setting_btn_clicked)
        fuben_layout.addWidget(fuben_setting_btn)
        fuben_layout.addStretch(1)
        fuben_widget.setLayout(fuben_layout)
        menu_layout.addWidget(fuben_widget, 0, 1)

        shop_enable_widget = QWidget()
        shop_enable_layout = QHBoxLayout()
        self.shop_enable_checkbox = shop_enable_checkbox = QCheckBox("商店购买")
        shop_enable_checkbox.setFont(normal_font)
        shop_enable_checkbox.setChecked(self.usersettings.shop_enabled)
        shop_enable_checkbox.stateChanged.connect(
            self.shop_enable_checkbox_stateChanged
        )
        shop_enable_layout.addWidget(shop_enable_checkbox)
        shop_auto_buy_setting_btn = QPushButton("设置")
        shop_auto_buy_setting_btn.clicked.connect(
            self.shop_auto_buy_setting_btn_clicked
        )
        shop_enable_layout.addWidget(shop_auto_buy_setting_btn)
        shop_enable_layout.addStretch(1)
        shop_enable_widget.setLayout(shop_enable_layout)
        menu_layout.addWidget(shop_enable_widget, 1, 0)

        task_panel = QWidget()
        task_panel_layout = QVBoxLayout()
        self.task_setting_checkbox = task_setting_checkbox = QCheckBox("自动领取任务")
        task_setting_checkbox.setFont(normal_font)
        task_setting_checkbox.setChecked(self.usersettings.task_enabled)
        task_setting_checkbox.stateChanged.connect(
            self.task_setting_checkbox_stateChanged
        )
        task_panel_layout.addWidget(task_setting_checkbox)
        task_widget = QWidget()
        task_layout = QHBoxLayout()

        main_task_widget = QWidget()
        main_task_layout = QHBoxLayout()
        self.main_task_checkbox = main_task_checkbox = QCheckBox("主线")
        main_task_checkbox.setFont(normal_font)
        main_task_checkbox.setChecked(self.usersettings.enable_list[0])
        main_task_checkbox.stateChanged.connect(self.main_task_checkbox_stateChanged)
        main_task_layout.addWidget(main_task_checkbox)
        main_task_widget.setLayout(main_task_layout)
        task_layout.addWidget(main_task_widget)

        side_task_widget = QWidget()
        side_task_layout = QHBoxLayout()
        self.side_task_checkbox = side_task_checkbox = QCheckBox("支线")
        side_task_checkbox.setFont(normal_font)
        side_task_checkbox.setChecked(self.usersettings.enable_list[1])
        side_task_checkbox.stateChanged.connect(self.side_task_checkbox_stateChanged)
        side_task_layout.addWidget(side_task_checkbox)
        side_task_widget.setLayout(side_task_layout)
        task_layout.addWidget(side_task_widget)

        daily_task_widget = QWidget()
        daily_task_layout = QHBoxLayout()
        self.daily_task_checkbox = daily_task_checkbox = QCheckBox("日常")
        daily_task_checkbox.setFont(normal_font)
        daily_task_checkbox.setChecked(self.usersettings.enable_list[2])
        daily_task_checkbox.stateChanged.connect(self.daily_task_checkbox_stateChanged)
        daily_task_layout.addWidget(daily_task_checkbox)
        daily_task_widget.setLayout(daily_task_layout)
        task_layout.addWidget(daily_task_widget)

        active_task_widget = QWidget()
        active_task_layout = QHBoxLayout()
        self.active_task_checkbox = active_task_checkbox = QCheckBox("活动")
        active_task_checkbox.setFont(normal_font)
        active_task_checkbox.setChecked(self.usersettings.enable_list[3])
        active_task_checkbox.stateChanged.connect(
            self.active_task_checkbox_stateChanged
        )
        active_task_layout.addWidget(active_task_checkbox)
        active_task_widget.setLayout(active_task_layout)
        task_layout.addWidget(active_task_widget)
        task_layout.addStretch(1)
        task_widget.setLayout(task_layout)

        task_panel_layout.addWidget(task_widget)
        task_panel.setLayout(task_panel_layout)

        menu_layout.addWidget(task_panel, 2, 0)

        auto_use_item_widget = QWidget()
        auto_use_item_layout = QHBoxLayout()
        self.auto_use_item_checkbox = auto_use_item_checkbox = QCheckBox("自动使用道具")
        auto_use_item_checkbox.setFont(normal_font)
        auto_use_item_checkbox.setChecked(self.usersettings.auto_use_item_enabled)
        auto_use_item_checkbox.stateChanged.connect(
            self.auto_use_item_checkbox_stateChanged
        )
        auto_use_item_layout.addWidget(auto_use_item_checkbox)

        self.auto_use_item_setting_btn = auto_use_item_setting_btn = QPushButton("道具面板")
        auto_use_item_setting_btn.clicked.connect(
            self.auto_use_item_setting_btn_clicked
        )
        auto_use_item_layout.addWidget(auto_use_item_setting_btn)
        auto_use_item_layout.addStretch(1)
        auto_use_item_widget.setLayout(auto_use_item_layout)
        menu_layout.addWidget(auto_use_item_widget, 3, 0)

        arena_widget = QWidget()
        arena_layout = QHBoxLayout()
        self.arena_checkbox = arena_checkbox = QCheckBox("竞技场")
        arena_checkbox.setFont(normal_font)
        arena_checkbox.setChecked(self.usersettings.arena_enabled)
        arena_checkbox.stateChanged.connect(self.arena_checkbox_stateChanged)
        arena_layout.addWidget(arena_checkbox)
        arena_widget.setLayout(arena_layout)
        menu_layout.addWidget(arena_widget, 4, 0)

        serverbattle_widget = QWidget()
        serverbattle_layout = QHBoxLayout()
        self.serverbattle_checkbox = serverbattle_checkbox = QCheckBox("跨服战")
        serverbattle_checkbox.setFont(normal_font)
        serverbattle_checkbox.setChecked(self.usersettings.serverbattle_enabled)
        serverbattle_checkbox.stateChanged.connect(
            self.serverbattle_checkbox_stateChanged
        )
        serverbattle_layout.addWidget(serverbattle_checkbox)
        serverbattle_widget.setLayout(serverbattle_layout)
        menu_layout.addWidget(serverbattle_widget, 4, 1)

        daily_widget = QWidget()
        daily_layout = QHBoxLayout()
        self.daily_checkbox = daily_checkbox = QCheckBox("日常签到和vip")
        daily_checkbox.setFont(normal_font)
        daily_checkbox.setChecked(self.usersettings.daily_enabled)
        daily_checkbox.stateChanged.connect(self.daily_checkbox_stateChanged)
        daily_layout.addWidget(daily_checkbox)
        daily_widget.setLayout(daily_layout)
        menu_layout.addWidget(daily_widget, 4, 2)

        territory_widget = QWidget()
        territory_layout = QHBoxLayout()
        self.territory_checkbox = territory_checkbox = QCheckBox("领地")
        territory_checkbox.setFont(normal_font)
        territory_checkbox.setChecked(self.usersettings.territory_enabled)
        territory_checkbox.stateChanged.connect(self.territory_checkbox_stateChanged)
        territory_layout.addWidget(territory_checkbox)

        self.territory_setting_btn = QPushButton("设置")
        self.territory_setting_btn.clicked.connect(self.territory_setting_btn_clicked)
        territory_layout.addWidget(self.territory_setting_btn)

        territory_layout.addStretch(1)
        territory_widget.setLayout(territory_layout)
        menu_layout.addWidget(territory_widget, 5, 0)

        # self.garden_checkbox = QCheckBox("自动花园boss")
        # self.garden_checkbox.setFont(normal_font)
        # self.garden_checkbox.setChecked(self.usersettings.garden_enabled)
        # self.garden_checkbox.stateChanged.connect(self.garden_checkbox_stateChanged)
        # menu_layout.addWidget(self.garden_checkbox, 5, 1)
        garden_widget = QWidget()
        garden_layout = QHBoxLayout()
        self.garden_checkbox = garden_checkbox = QCheckBox("自动花园boss")
        garden_checkbox.setFont(normal_font)
        garden_checkbox.setChecked(self.usersettings.garden_enabled)
        garden_checkbox.stateChanged.connect(self.garden_checkbox_stateChanged)
        garden_layout.addWidget(garden_checkbox)
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
        self.max_timeout_input_box = max_timeout_input_box = QSpinBox()
        max_timeout_input_box.setMinimum(1)
        max_timeout_input_box.setMaximum(60)
        max_timeout_input_box.setValue(self.usersettings.cfg.timeout)
        max_timeout_input_box.valueChanged.connect(
            self.max_timeout_input_box_valueChanged
        )
        max_timeout_layout.addWidget(max_timeout_input_box)
        max_timeout_widget.setLayout(max_timeout_layout)
        menu_layout.addWidget(max_timeout_widget, 7, 0)

        millsecond_delay_widget = QWidget()
        millsecond_delay_layout = QHBoxLayout()
        millsecond_delay_layout.addWidget(QLabel("请求间隔(毫秒):"))
        self.millsecond_delay_input_box = millsecond_delay_input_box = QSpinBox()
        millsecond_delay_input_box.setMinimum(0)
        millsecond_delay_input_box.setMaximum(60 * 1000)
        millsecond_delay_input_box.setValue(self.usersettings.cfg.millsecond_delay)
        millsecond_delay_input_box.valueChanged.connect(
            self.millsecond_delay_input_box_valueChanged
        )
        millsecond_delay_layout.addWidget(millsecond_delay_input_box)
        millsecond_delay_widget.setLayout(millsecond_delay_layout)
        menu_layout.addWidget(millsecond_delay_widget, 8, 0)

        menu_widget.setLayout(menu_layout)
        main_layout.addWidget(menu_widget)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

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
            self.usersettings.lib,
            self.usersettings.shop,
            self.usersettings.logger,
            self.usersettings.shop_auto_buy_dict,
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

    def auto_use_item_checkbox_stateChanged(self):
        self.usersettings.auto_use_item_enabled = (
            self.auto_use_item_checkbox.isChecked()
        )

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

    def auto_use_item_setting_btn_clicked(self):
        self.auto_use_item_setting_window = AutoUseItemSettingWindow(
            self.usersettings, parent=self
        )
        self.auto_use_item_setting_window.show()

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

        evolution_panel_btn = QPushButton("进化路线面板")
        evolution_panel_btn.clicked.connect(self.evolution_panel_btn_clicked)
        menu_layout.addWidget(evolution_panel_btn, 0, 0)

        upgrade_quality_btn = QPushButton("升品面板")
        upgrade_quality_btn.clicked.connect(self.upgrade_quality_btn_clicked)
        menu_layout.addWidget(upgrade_quality_btn, 1, 0)

        auto_synthesis_btn = QPushButton("自动合成面板")
        auto_synthesis_btn.clicked.connect(self.auto_synthesis_btn_clicked)
        menu_layout.addWidget(auto_synthesis_btn, 2, 0)

        heritage_btn = QPushButton("传承面板")
        heritage_btn.clicked.connect(self.heritage_btn_clicked)
        menu_layout.addWidget(heritage_btn, 3, 0)

        compound_btn = QPushButton("自动复合面板")
        compound_btn.clicked.connect(self.compound_btn_clicked)
        menu_layout.addWidget(compound_btn, 4, 0)

        auto_pipeline_btn = QPushButton("全自动面板")
        auto_pipeline_btn.clicked.connect(self.auto_pipeline_btn_clicked)
        menu_layout.addWidget(auto_pipeline_btn, 5, 0)

        plant_relative_btn = QPushButton("植物相关面板")
        plant_relative_btn.clicked.connect(self.plant_relative_btn_clicked)
        menu_layout.addWidget(plant_relative_btn, 6, 0)

        repository_tool_record_btn = QPushButton("仓库物品记录面板")
        repository_tool_record_btn.clicked.connect(
            self.repository_tool_record_btn_clicked
        )
        menu_layout.addWidget(repository_tool_record_btn, 7, 0)

        menu_widget.setLayout(menu_layout)
        main_layout.addWidget(menu_widget)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

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
        self.compound_window = AutoCompoundWindow(self.usersettings, parent=self)
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
            self.usersettings, parent=self
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

    def __init__(self, usersettings: UserSettings, cache_dir):
        super().__init__()
        self.usersettings = usersettings

        if not os.path.exists(cache_dir):
            os.mkdir(cache_dir)
        self.wr_cache = WebRequest(self.usersettings.cfg, cache_dir=cache_dir)

        self.init_ui()

        self.logger_signal.connect(self.update_text_box)
        self.usersettings.io_logger.set_signal(self.logger_signal)

    def init_ui(self):
        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.7), int(screen_size.height() * 0.7))
        self.move(int(screen_size.width() * 0.15), int(screen_size.height() * 0.15))

        self.page_widget = QTabWidget()

        main_widget = QWidget()
        main_layout = QVBoxLayout()
        top_widget = QWidget()
        top_layout = QHBoxLayout()

        user_show_layout = QHBoxLayout()

        img = Image.open(
            BytesIO(
                self.wr_cache.get(
                    self.usersettings.user.face_url,
                    init_header="pvzol" in self.usersettings.cfg.host,
                    url_format=False,
                    use_cache=True,
                )
            )
        )
        img = img.resize((64, 64))
        user_face_img = QImage(
            img.tobytes(), img.width, img.height, QImage.Format.Format_RGB888
        )
        user_show_layout.addWidget(QLabel().setPixmap(QPixmap.fromImage(user_face_img)))

        user_info_layout = QVBoxLayout()
        user_info_layout.addWidget(QLabel(f"{self.usersettings.user.name}"))
        user_info_layout.addWidget(QLabel(f"等级: {self.usersettings.user.grade}"))
        user_info_layout.addWidget(
            QLabel(
                f"经验值: {self.usersettings.user.exp_now}/{self.usersettings.user.exp_max}"
            )
        )
        user_info_layout.addWidget(QLabel(self.usersettings.user.name))
        user_show_layout.addLayout(user_info_layout)

        top_layout.addLayout(user_show_layout)
        top_layout.addStretch(1)

        # 设置top_layout的高度为main_layout的0.2倍
        top_widget.setFixedHeight(int(screen_size.height() * 0.1))
        top_widget.setLayout(top_layout)
        main_layout.addWidget(top_widget)

        # Middle Section
        middle_splitter = QSplitter(Qt.Orientation.Horizontal)
        middle_splitter.setFixedHeight(int(self.height() * 0.7))
        middle_splitter.setHandleWidth(10)
        middle_splitter.setStyleSheet(
            "QSplitter::handle{background: rgb(245, 245, 245);}"
        )

        # Left Panel
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_text_layout = QVBoxLayout()
        left_text_layout.setSpacing(5)
        left_text_layout.addWidget(QLabel(f"金币: {self.usersettings.user.money}"))
        left_text_layout.addWidget(
            QLabel(
                f"今日经验: {self.usersettings.user.today_exp} / {self.usersettings.user.today_exp_max}"
            )
        )
        left_text_layout.addWidget(
            QLabel(
                f"挑战次数: {self.usersettings.user.cave_amount} / {self.usersettings.user.cave_amount_max}"
            )
        )
        left_text_layout.addWidget(
            QLabel(
                f"领地次数: {self.usersettings.user.territory_amount} / {self.usersettings.user.territory_amount_max}"
            )
        )

        left_layout.addLayout(left_text_layout)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
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

        left_layout.addStretch(1)

        left_layout.setSpacing(10)
        left_panel.setLayout(left_layout)

        # Right Panel
        right_panel = QWidget()
        right_layout = QVBoxLayout()

        # Large Text Box
        self.text_box = text_box = QPlainTextEdit()
        text_box.setReadOnly(True)

        right_layout.addWidget(text_box)
        right_panel.setLayout(right_layout)

        left_panel.setFixedWidth(int(screen_size.width() * 0.13))
        middle_splitter.addWidget(left_panel)
        middle_splitter.addWidget(right_panel)
        # 设置left_panel的宽度为screen的0.1倍
        main_layout.addWidget(middle_splitter)

        main_widget.setLayout(main_layout)
        self.page_widget.addTab(main_widget, "Main")
        # 设置主窗口常驻屏幕
        # self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)

        self.setCentralWidget(self.page_widget)
        self.setWindowTitle("Custom Window")

    def update_text_box(self):
        result = self.usersettings.io_logger.get_new_infos()
        document = self.text_box.document()
        # 冻结text_box显示，直到document更新完毕后更新
        self.text_box.viewport().setUpdatesEnabled(False)
        for info in reversed(result):
            cursor = QTextCursor(document)
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.insertText(info + "\n")
            # self.text_box.insertPlainText(info + "\n")
        self.text_box.viewport().setUpdatesEnabled(True)
        self.text_box.viewport().update()

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
        self.usersettings.start()

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


class LoginWindow(QMainWindow):
    get_usersettings_finish_signal = pyqtSignal(tuple)

    def __init__(self):
        super().__init__()
        self.configs = []
        self.cfg_path = os.path.join(root_dir, "data/config/config.json")
        if os.path.exists(self.cfg_path):
            with open(self.cfg_path, "r", encoding="utf-8") as f:
                self.configs = json.load(f)
        self.init_ui()
        self.get_usersettings_finish_signal.connect(self.get_usersettings_finished)
        self.main_window_thread = []
        self.game_queue = None

    def init_ui(self):
        self.setWindowTitle("登录")

        # 将窗口居中显示，宽度为显示器宽度的30%，高度为显示器高度的60%
        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.3), int(screen_size.height() * 0.6))
        self.move(int(screen_size.width() * 0.35), int(screen_size.height() * 0.17))

        main_widget = QWidget()
        main_layout = QVBoxLayout()

        login_user_widget = QWidget()
        login_user_layout = QVBoxLayout()
        login_user_layout.addWidget(QLabel("已登录的用户(双击登录，选中按delete或backspace删除)"))
        self.login_user_list = login_user_list = QListWidget()
        login_user_list.itemDoubleClicked.connect(self.login_list_item_double_clicked)
        login_user_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.refresh_login_user_list()
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
        region_input.addItems([f"官服{i}区" for i in range(12, 46 + 1)])
        region_input.addItems([f"私服{i}区" for i in range(1, 10)])
        region_layout.addWidget(region_input)
        region_widget.setLayout(region_layout)
        main_layout.addWidget(region_widget)

        cookie_widget = QWidget()
        cookie_layout = QHBoxLayout()
        cookie_layout.addWidget(QLabel("Cookie:"))
        self.cookie_input = cookie_input = QLineEdit()
        cookie_layout.addWidget(cookie_input)
        cookie_widget.setLayout(cookie_layout)
        main_layout.addWidget(cookie_widget)

        login_btn = QPushButton("登录")
        login_btn.clicked.connect(self.login_btn_clicked)
        main_layout.addWidget(login_btn)

        main_layout.addStretch(1)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

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
            self.login_user_list.indexFromItem(item).row()
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

    def login_btn_clicked(self):
        # 取出当前选中的用户
        username = self.username_input.text()
        region_text = self.region_input.currentText()
        region = int(region_text[2:-1])
        if region_text.startswith("官服"):
            host = f"s{region}.youkia.pvz.youkia.com"
            server = "官服"
        elif region_text.startswith("私服"):
            host = "pvzol.org"
            server = "私服"
        else:
            raise ValueError(f"Unknown region text: {region_text}")
        cookie = self.cookie_input.text()
        if (cookie[0] == '"' and cookie[-1] == '"') or (
            cookie[0] == "'" and cookie[-1] == "'"
        ):
            cookie = cookie[1:-1]
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
        # 强制重新渲染login窗口元素
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
                    shutil.rmtree(
                        os.path.join(
                            root_dir,
                            f"data/user/{self.configs[i]['username']}/{self.configs[i]['region']}",
                        )
                    )
                    if (
                        len(
                            os.listdir(
                                os.path.join(
                                    root_dir,
                                    f"data/user/{self.configs[i]['username']}",
                                )
                            )
                        )
                        == 0
                    ):
                        shutil.rmtree(
                            os.path.join(
                                root_dir,
                                f"data/user/{self.configs[i]['username']}",
                            )
                        )
            self.configs = new_configs
            self.save_config()
            self.refresh_login_user_list()

    def closeEvent(self, event):
        if self.game_queue is not None:
            self.game_queue.put_nowait(None)
        return super().closeEvent(event)


class GetUsersettings(threading.Thread):
    def __init__(self, cfg: Config, root_dir, finish_trigger):
        super().__init__()
        self.cfg = cfg
        self.root_dir = root_dir
        self.finish_trigger = finish_trigger

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

        max_info_capacity = 10
        # TODO: 从配置文件中读取
        logger = IOLogger(log_dir, max_info_capacity=max_info_capacity)
        logger_list.append(logger)
        usersettings = get_usersettings(self.cfg, logger, setting_dir)
        self.finish_trigger.emit((usersettings, cache_dir))


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
    # 设置logging监听等级为INFO
    logging.basicConfig(level=logging.INFO)  # 如果不想让控制台输出那么多信息，可以将这一行注释掉
    # 取root_dir为可执行文件的目录
    root_dir = os.getcwd()
    data_dir = os.path.join(root_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(os.path.join(data_dir, "config"), exist_ok=True)

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
