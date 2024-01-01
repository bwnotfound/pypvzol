from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLineEdit,
    QComboBox,
    QCheckBox,
)
from PyQt6 import QtGui

from ...wrapped import QLabel
from ....upgrade import quality_name_list
from ...user.auto_pipeline import UpgradeQuality, OpenBox


class OpenBoxWidget(QWidget):
    def __init__(self, pipeline: OpenBox, parent=None):
        super().__init__(parent=parent)
        self.pipeline = pipeline
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout()

        self.main_layout.addWidget(QLabel("设置一次开魔神箱的数量"))
        self.inputbox = QLineEdit()
        self.inputbox.setText(str(self.pipeline.amount))
        self.inputbox.setValidator(QtGui.QIntValidator(1, 99999))
        self.inputbox.textChanged.connect(self.inputbox_text_changed)
        self.main_layout.addWidget(self.inputbox)

        self.setLayout(self.main_layout)

    def inputbox_text_changed(self):
        text = self.inputbox.text()
        amount = int(text) if text != "" else 0
        self.pipeline.amount = amount


class UpgradeQualityWidget(QWidget):
    def __init__(self, pipeline: UpgradeQuality, parent=None):
        super().__init__(parent=parent)
        self.pipeline = pipeline
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout()

        self.target_quality_combobox = QComboBox()
        for quality_name in quality_name_list:
            self.target_quality_combobox.addItem(quality_name)
        self.target_quality_combobox.setCurrentIndex(self.pipeline.target_quality_index)
        self.target_quality_combobox.currentIndexChanged.connect(
            self.target_quality_combobox_index_changed
        )
        self.main_layout.addWidget(self.target_quality_combobox)

        self.main_layout.addWidget(QLabel("需要刷多少植物的品:"))
        self.upgrade_plant_amount = QLineEdit()
        self.upgrade_plant_amount.setText(str(self.pipeline.upgrade_plant_amount))
        self.upgrade_plant_amount.setValidator(QtGui.QIntValidator(1, 99999))
        self.upgrade_plant_amount.textChanged.connect(
            self.upgrade_plant_amount_text_changed
        )
        self.main_layout.addWidget(self.upgrade_plant_amount)

        self.main_layout.addWidget(QLabel("并发数:"))
        self.pool_size_combobox = QComboBox()
        self.pool_size_combobox.addItems([str(i) for i in range(1, 21)])
        self.pool_size_combobox.setCurrentIndex(self.pipeline.pool_size - 1)
        self.pool_size_combobox.currentIndexChanged.connect(
            self.pool_size_combobox_current_index_changed
        )
        self.main_layout.addWidget(self.pool_size_combobox)

        self.need_show_all_info_checkbox = QCheckBox("显示所有信息")
        self.need_show_all_info_checkbox.setChecked(self.pipeline.need_show_all_info)
        self.need_show_all_info_checkbox.stateChanged.connect(
            self.need_show_all_info_checkbox_state_changed
        )
        self.main_layout.addWidget(self.need_show_all_info_checkbox)

        self.setLayout(self.main_layout)

    def target_quality_combobox_index_changed(self, index):
        self.pipeline.target_quality_index = index

    def upgrade_plant_amount_text_changed(self):
        text = self.upgrade_plant_amount.text()
        amount = int(text) if text != "" else 0
        self.pipeline.upgrade_plant_amount = amount

    def pool_size_combobox_current_index_changed(self, index):
        self.pipeline.pool_size = index + 1

    def need_show_all_info_checkbox_state_changed(self):
        self.pipeline.need_show_all_info = self.need_show_all_info_checkbox.isChecked()
