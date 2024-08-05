from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QPushButton,
    QMainWindow,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
)
from PyQt6 import QtGui
from PyQt6.QtCore import Qt

from ...wrapped import QLabel
from ....upgrade import quality_name_list
from ...user.auto_pipeline import (
    UpgradeQuality,
    OpenBox,
    AutoUpgradeQuality,
    CustomProcessChain,
    AutoStone,
    AutoEvolution,
    AutoSynthesis,
    Pipeline,
)
from ..common import delete_layout_children
from ....library import talent_name_list, stone_name_list
from ....utils.common import format_plant_info


class SinglePipelineSettingWidget(QWidget):
    def __init__(
        self,
        pipeline: Pipeline,
        parent=None,
    ):
        super().__init__(parent=parent)
        self.parent_widget = parent
        self.pipeline = pipeline
        self.init_ui()

    def init_ui(self):
        pipeline_layout = QVBoxLayout()
        pipeline_layout.addStretch(1)
        self.setLayout(pipeline_layout)

        layout1 = QHBoxLayout()
        pipeline_layout.addLayout(layout1)

        info_label = QLabel(self.pipeline.name)
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout1.addWidget(info_label)

        self.pipeline1_setting_btn = QPushButton("设置")
        self.pipeline1_setting_btn.setFixedHeight(30)
        self.pipeline1_setting_btn.setFixedWidth(100)
        self.pipeline1_setting_btn.clicked.connect(self.pipeline_setting_btn_clicked)
        layout1.addWidget(self.pipeline1_setting_btn)

        self.pipeline_setting_widget_layout = QHBoxLayout()
        pipeline_layout.addLayout(self.pipeline_setting_widget_layout)
        pipeline_layout.addStretch(1)

        if self.pipeline.has_setting_widget():
            setting_widget = self.pipeline.setting_widget(parent=self.parent_widget)
            self.pipeline_setting_widget_layout.addWidget(setting_widget)
        if self.pipeline.has_setting_window():
            self.pipeline1_setting_btn.setEnabled(True)
        else:
            self.pipeline1_setting_btn.setDisabled(True)

    def pipeline_setting_btn_clicked(self):
        if self.pipeline.has_setting_window():
            self.setting_window = self.pipeline.setting_window(
                parent=self.parent_widget
            )
            self.setting_window.show()


class OpenBoxWidget(QWidget):
    def __init__(self, pipeline: OpenBox, parent=None):
        super().__init__(parent=parent)
        self.pipeline = pipeline
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout()

        self.main_layout.addWidget(QLabel("设置一次开箱的数量"))
        self.inputbox = QLineEdit()
        self.inputbox.setText(str(self.pipeline.amount))
        self.inputbox.setValidator(QtGui.QIntValidator(1, 99999))
        self.inputbox.textChanged.connect(self.inputbox_text_changed)
        self.main_layout.addWidget(self.inputbox)
        self.box_type_combobox = QComboBox()
        self.box_type_combobox.addItems(self.pipeline.box_type_str_list)
        self.box_type_combobox.setCurrentIndex(self.pipeline.current_box_type_index)
        self.box_type_combobox.currentIndexChanged.connect(
            self.box_type_combobox_current_index_changed
        )
        self.main_layout.addWidget(self.box_type_combobox)
        auto_set_amount = QPushButton("自动设置数量")
        auto_set_amount.clicked.connect(self.auto_set_amount_btn_clicked)
        self.main_layout.addWidget(auto_set_amount)

        self.setLayout(self.main_layout)

    def auto_set_amount_btn_clicked(self):
        self.pipeline.auto_set_amount()
        self.inputbox.setText(str(self.pipeline.amount))

    def inputbox_text_changed(self):
        text = self.inputbox.text()
        amount = int(text) if text != "" else 0
        self.pipeline.amount = amount

    def box_type_combobox_current_index_changed(self, index):
        self.pipeline.current_box_type_index = index


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


class AutoUpgradeQualityWidget(QWidget):
    def __init__(self, pipeline: AutoUpgradeQuality, parent=None):
        super().__init__(parent=parent)
        self.pipeline = pipeline
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout()

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

    def pool_size_combobox_current_index_changed(self, index):
        self.pipeline.pool_size = index + 1

    def need_show_all_info_checkbox_state_changed(self):
        self.pipeline.need_show_all_info = self.need_show_all_info_checkbox.isChecked()


class EvolutionWidget(QWidget):
    def __init__(self, pipeline: AutoEvolution, parent=None):
        super().__init__(parent=parent)
        self.pipeline = pipeline
        self.init_ui()

    def init_ui(self):
        self.main_layout = QHBoxLayout()
        self.setLayout(self.main_layout)

        self.main_layout.addWidget(QLabel("并发数:"))
        self.pool_size_combobox = QComboBox()
        self.pool_size_combobox.addItems([str(i) for i in range(1, 41)])
        self.pool_size_combobox.setCurrentIndex(self.pipeline.pool_size - 1)
        self.pool_size_combobox.currentIndexChanged.connect(
            self.pool_size_combobox_current_index_changed
        )
        self.main_layout.addWidget(self.pool_size_combobox)

    def pool_size_combobox_current_index_changed(self):
        self.pipeline.pool_size = self.pool_size_combobox.currentIndex() + 1

class StoneWidget(QWidget):
    def __init__(self, pipeline: AutoStone, parent=None):
        super().__init__(parent=parent)
        self.pipeline = pipeline
        self.init_ui()

    def init_ui(self):
        self.main_layout = QHBoxLayout()
        self.setLayout(self.main_layout)

        self.main_layout.addWidget(QLabel("并发数:"))
        self.pool_size_combobox = QComboBox()
        self.pool_size_combobox.addItems([str(i) for i in range(1, 41)])
        self.pool_size_combobox.setCurrentIndex(self.pipeline.pool_size - 1)
        self.pool_size_combobox.currentIndexChanged.connect(
            self.pool_size_combobox_current_index_changed
        )
        self.main_layout.addWidget(self.pool_size_combobox)

    def pool_size_combobox_current_index_changed(self):
        self.pipeline.pool_size = self.pool_size_combobox.currentIndex() + 1


class StoneSettingWindow(QMainWindow):
    def __init__(self, pipeline: AutoStone, parent=None):
        super().__init__(parent=parent)
        self.pipeline = pipeline
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("升宝石设置")

        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.4), int(screen_size.height() * 0.4))
        self.move(int(screen_size.width() * 0.3), int(screen_size.height() * 0.3))

        self.main_widget = QWidget()
        self.main_layout = QHBoxLayout()
        self.main_layout.setSpacing(10)
        self.main_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.main_widget)
        self.main_layout.addStretch(1)

        for i in range(9):
            widget = QWidget()
            layout = QVBoxLayout()
            widget.setLayout(layout)
            self.main_layout.addWidget(widget)

            layout.addWidget(
                QLabel("{}({})".format(talent_name_list[i], stone_name_list[i]))
            )
            combo = QComboBox()
            combo.addItems([str(j) for j in range(1 + 10)])
            combo.setCurrentIndex(self.pipeline.target_stone_level[i])

            def clicked(index, j=i):
                self.pipeline.target_stone_level[j] = index

            combo.currentIndexChanged.connect(clicked)
            layout.addWidget(combo)
        self.main_layout.addStretch(1)


class AutoSynthesisSettingWindow(QMainWindow):
    def __init__(self, pipeline: AutoSynthesis, parent=None):
        super().__init__(parent=parent)
        self.pipeline = pipeline
        self.init_ui()
        self.refresh()

    def init_ui(self):
        self.setWindowTitle("自动吃速度设置")

        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.4), int(screen_size.height() * 0.6))
        self.move(int(screen_size.width() * 0.3), int(screen_size.height() * 0.2))

        self.main_widget = QWidget()
        self.main_layout = QHBoxLayout()
        self.main_layout.setSpacing(10)
        self.main_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.main_widget)

        plant_show_panel = QWidget()
        plant_show_panel_layout = QVBoxLayout()
        plant_show_panel.setLayout(plant_show_panel_layout)
        self.main_layout.addWidget(plant_show_panel)
        plant_show_panel_layout.addWidget(QLabel("植物列表"))

        self.plant_list = QListWidget()
        plant_show_panel_layout.addWidget(self.plant_list)
        self.plant_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)

        set_main_plant_btn = QPushButton("设为主力植物")
        set_main_plant_btn.clicked.connect(self.set_main_plant_btn_clicked)
        plant_show_panel_layout.addWidget(set_main_plant_btn)

        main_plant_show_panel = QWidget()
        main_plant_show_panel_layout = QVBoxLayout()
        main_plant_show_panel.setLayout(main_plant_show_panel_layout)
        self.main_layout.addWidget(main_plant_show_panel)
        main_plant_show_panel_layout.addWidget(QLabel("主力植物"))

        self.main_plant_info_panel = QPlainTextEdit()
        main_plant_show_panel_layout.addWidget(self.main_plant_info_panel)
        self.main_plant_info_panel.setReadOnly(True)

        rest_panel = QWidget()
        rest_panel_layout = QVBoxLayout()
        rest_panel.setLayout(rest_panel_layout)
        self.main_layout.addWidget(rest_panel)

        layout = QHBoxLayout()
        layout.addWidget(QLabel("增强卷轴数量: "))
        reinforce_number_combo = QComboBox()
        reinforce_number_combo.addItems([str(i) for i in range(1 + 10)])
        reinforce_number_combo.setCurrentIndex(self.pipeline.reinforce_number)
        reinforce_number_combo.currentIndexChanged.connect(
            self.reinforce_number_combo_current_index_changed
        )
        layout.addWidget(reinforce_number_combo)
        rest_panel_layout.addLayout(layout)

        layout = QHBoxLayout()
        layout.addWidget(QLabel("并发数: "))
        pool_size_combo = QComboBox()
        pool_size_combo.addItems([str(i) for i in range(1, 41)])
        pool_size_combo.setCurrentIndex(self.pipeline.pool_size - 1)
        pool_size_combo.currentIndexChanged.connect(
            self.pool_size_combo_current_index_changed
        )
        layout.addWidget(pool_size_combo)
        rest_panel_layout.addLayout(layout)

    def reinforce_number_combo_current_index_changed(self, index):
        self.pipeline.reinforce_number = index

    def pool_size_combo_current_index_changed(self, index):
        self.pipeline.pool_size = index + 1

    def refresh(self):
        self.plant_list.clear()
        for plant in self.pipeline.repo.plants:
            if plant.id == self.pipeline.main_plant_id:
                continue
            item = QListWidgetItem(
                format_plant_info(
                    plant,
                    self.pipeline.lib,
                    chosen_attribute="速度",
                )
            )
            item.setData(Qt.ItemDataRole.UserRole, plant.id)
            self.plant_list.addItem(item)
        if self.pipeline.main_plant_id is not None:
            self.main_plant_info_panel.setPlainText(
                format_plant_info(
                    self.pipeline.repo.get_plant(self.pipeline.main_plant_id),
                    self.pipeline.lib,
                    show_normal_attribute=True,
                )
            )
        else:
            self.main_plant_info_panel.setPlainText("")
    
    def set_main_plant_btn_clicked(self):
        selected_items = self.plant_list.selectedItems()
        if len(selected_items) == 0:
            return
        plant_id = selected_items[0].data(Qt.ItemDataRole.UserRole)
        self.pipeline.main_plant_id = plant_id
        self.refresh()


class CustomProcessWidget(QMainWindow):
    def __init__(self, base_pipeline: CustomProcessChain, parent=None):
        super().__init__(parent=parent)
        self.base_pipeline = base_pipeline
        self.init_ui()
        self.refresh()

    def init_ui(self):
        self.setWindowTitle("全自动流水线设置")

        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.6), int(screen_size.height() * 0.6))
        self.move(int(screen_size.width() * 0.2), int(screen_size.height() * 0.2))

        self.main_widget = QWidget()
        self.main_layout = QHBoxLayout()
        # self.main_layout.setSpacing(10)
        self.main_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.main_widget)

        widget = QWidget()
        pipeline_list_layout = QVBoxLayout()
        widget.setLayout(pipeline_list_layout)
        widget.setFixedWidth(int(self.width() * 0.2))
        widget.setFixedHeight(self.height())
        self.main_layout.addWidget(widget)
        self.main_layout.addStretch(1)

        pipeline_list_layout.addWidget(QLabel("处理列表，处理顺序从上到下"))
        self.pipeline_list = QListWidget()
        self.pipeline_list.setFixedHeight(int(self.height() * 0.7))
        self.pipeline_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        pipeline_list_layout.addWidget(self.pipeline_list)
        self.availabel_pipeline_combobox = QComboBox()
        self.availabel_pipeline_combobox.addItems(
            self.base_pipeline.available_pipeline_names
        )
        self.availabel_pipeline_combobox.setCurrentIndex(0)
        pipeline_list_layout.addWidget(self.availabel_pipeline_combobox)

        self.add_pipeline_btn = QPushButton("添加处理")
        self.add_pipeline_btn.clicked.connect(self.add_pipeline_btn_clicked)
        pipeline_list_layout.addWidget(self.add_pipeline_btn)
        pipeline_list_layout.addStretch(1)

        self.show_widget = QWidget()
        self.pipeline_show_layout = QHBoxLayout()
        self.pipeline_show_layout.setSpacing(20)
        self.show_widget.setLayout(self.pipeline_show_layout)
        self.show_widget.setFixedWidth(int(self.width() * 0.75))
        self.show_widget.setFixedHeight(self.height())
        self.main_layout.addWidget(self.show_widget)

    def refresh(self):
        self.pipeline_list.clear()
        delete_layout_children(self.pipeline_show_layout)
        self.pipeline_show_layout.addStretch(1)
        for i, pipeline in enumerate(self.base_pipeline.chosen_pipelines):
            if i > 0:
                self.pipeline_show_layout.addWidget(QLabel("-->"))
            item = QListWidgetItem(pipeline.name)
            item.setData(Qt.ItemDataRole.UserRole, pipeline)
            self.pipeline_list.addItem(item)

            widget = SinglePipelineSettingWidget(pipeline, self)
            self.pipeline_show_layout.addWidget(widget)

        self.pipeline_show_layout.addStretch(1)

    def add_pipeline_btn_clicked(self):
        pipeline_name = self.availabel_pipeline_combobox.currentText()
        self.base_pipeline.add_pipeline(pipeline_name)
        self.refresh()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            selected_items = self.pipeline_list.selectedItems()
            for item in selected_items:
                self.base_pipeline.remove_pipeline(item.data(Qt.ItemDataRole.UserRole))
            self.refresh()
