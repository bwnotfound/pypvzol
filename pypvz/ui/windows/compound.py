from threading import Event, Thread
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QComboBox,
    QCheckBox,
    QApplication,
    QLineEdit,
)
from PyQt6 import QtGui
from PyQt6.QtCore import Qt, pyqtSignal

from ..wrapped import QLabel, WaitEventThread
from ..user import UserSettings
from ...utils.common import format_number
from ...repository import Plant
from .common import ImageWindow, require_permission


class AutoCompoundWindow(QMainWindow):
    compound_finish_signal = pyqtSignal()
    refresh_all_signal = pyqtSignal(Event)
    compound_stoped_signal = pyqtSignal()

    def __init__(self, usersettings: UserSettings, parent=None):
        super().__init__(parent=parent)
        self.usersettings = usersettings
        self.interrupt_event = Event()
        self.rest_event = Event()
        self.rest_event.set()
        self.run_thread = None
        self.refresh_all_signal.connect(self.refresh_all)
        self.compound_finish_signal.connect(self.compound_finish)
        self.compound_stoped_signal.connect(self.compound_stoped)
        self.init_ui()
        self.refresh_all()

    def init_ui(self):
        self.setWindowTitle("自动合成")

        # 将窗口居中显示，宽度为显示器宽度的70%，高度为显示器高度的50%
        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.75), int(screen_size.height() * 0.7))
        self.move(int(screen_size.width() * 0.125), int(screen_size.height() * 0.15))

        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_layout.setSpacing(0)

        widget1 = QWidget()
        widget1.setFixedWidth(int(self.width() * 0.12))
        widget1_layout = QVBoxLayout()
        widget1_layout.addWidget(QLabel("物品列表"))
        self.tool_list = QListWidget()
        self.tool_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        widget1_layout.addWidget(self.tool_list)
        widget1.setLayout(widget1_layout)
        main_layout.addWidget(widget1)

        widget2 = QWidget()
        widget2.setMinimumWidth(int(self.width() * 0.25))
        widget2_layout = QVBoxLayout()
        widget2_layout.addWidget(QLabel("植物列表"))
        self.plant_list = QListWidget()
        self.plant_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        widget2_layout.addWidget(self.plant_list)
        widget2.setLayout(widget2_layout)
        main_layout.addWidget(widget2)

        widget3 = QWidget()
        widget3.setFixedWidth(int(self.width() * 0.13))
        widget3_layout = QVBoxLayout()
        widget3_layout.addStretch(1)
        widget3_1 = QWidget()
        widget3_1_layout = QVBoxLayout()
        widget3_1_layout.addWidget(QLabel("选择复合属性"))
        self.auto_compound_attribute_choice = QComboBox()
        for name in self.usersettings.auto_compound_man.attribute_list:
            self.auto_compound_attribute_choice.addItem(name)
        self.auto_compound_attribute_choice.setCurrentIndex(
            self.usersettings.auto_compound_man.attribute_list.index(
                self.usersettings.auto_compound_man.chosen_attribute
            )
        )
        self.auto_compound_attribute_choice.currentIndexChanged.connect(
            self.auto_compound_attribute_choice_changed
        )
        widget3_1_layout.addWidget(self.auto_compound_attribute_choice)
        widget3_1.setLayout(widget3_1_layout)
        widget3_layout.addWidget(widget3_1)

        widget3_2_layout = QHBoxLayout()
        widget3_2_layout.addWidget(QLabel("k值:"))
        self.k_choice = QComboBox()
        for i in range(11):
            self.k_choice.addItem(str(i))
        self.k_choice.setCurrentIndex(self.usersettings.auto_compound_man.k)
        self.k_choice.currentIndexChanged.connect(self.k_choice_changed)
        widget3_2_layout.addWidget(self.k_choice)
        widget3_layout.addLayout(widget3_2_layout)

        widget3_3_layout = QHBoxLayout()
        widget3_3_layout.addWidget(QLabel("n1值:"))
        self.n1_choice = QComboBox()
        for i in range(11):
            self.n1_choice.addItem(str(i))
        self.n1_choice.setCurrentIndex(self.usersettings.auto_compound_man.n1)
        self.n1_choice.currentIndexChanged.connect(self.n1_choice_changed)
        widget3_3_layout.addWidget(self.n1_choice)
        widget3_layout.addLayout(widget3_3_layout)

        widget3_4_layout = QHBoxLayout()
        widget3_4_layout.addWidget(QLabel("n2值:"))
        self.n2_choice = QComboBox()
        for i in range(31):
            self.n2_choice.addItem(str(i))
        self.n2_choice.setCurrentIndex(self.usersettings.auto_compound_man.n2)
        self.n2_choice.currentIndexChanged.connect(self.n2_choice_changed)
        widget3_4_layout.addWidget(self.n2_choice)
        widget3_layout.addLayout(widget3_4_layout)

        widget3_3_layout = QHBoxLayout()
        widget3_3_layout.addWidget(QLabel("m值:"))
        self.m_choice = QComboBox()
        for i in range(16):
            self.m_choice.addItem(str(i))
        self.m_choice.setCurrentIndex(self.usersettings.auto_compound_man.m)
        self.m_choice.currentIndexChanged.connect(self.m_choice_changed)
        widget3_3_layout.addWidget(self.m_choice)
        widget3_layout.addLayout(widget3_3_layout)

        plant_import_btn = QPushButton("导入合成池")
        plant_import_btn.clicked.connect(self.plant_import_btn_clicked)
        widget3_layout.addWidget(plant_import_btn)

        set_liezhi_plant_btn = QPushButton("设置劣质双格")
        set_liezhi_plant_btn.clicked.connect(self.set_liezhi_plant_btn_clicked)
        widget3_layout.addWidget(set_liezhi_plant_btn)

        remove_liezhi_plant_btn = QPushButton("移除劣质双格")
        remove_liezhi_plant_btn.clicked.connect(self.remove_liezhi_plant_btn_clicked)
        widget3_layout.addWidget(remove_liezhi_plant_btn)

        set_source_plant_btn = QPushButton("设置底座")
        set_source_plant_btn.clicked.connect(self.set_source_plant_btn_clicked)
        widget3_layout.addWidget(set_source_plant_btn)

        remove_source_plant_btn = QPushButton("移除底座")
        remove_source_plant_btn.clicked.connect(self.remove_source_plant_btn_clicked)
        widget3_layout.addWidget(remove_source_plant_btn)

        set_receiver_plant_btn = QPushButton("设置主力")
        set_receiver_plant_btn.clicked.connect(self.set_receiver_plant_btn_clicked)
        widget3_layout.addWidget(set_receiver_plant_btn)

        remove_receiver_plant_btn = QPushButton("移除主力")
        remove_receiver_plant_btn.clicked.connect(
            self.remove_receiver_plant_btn_clicked
        )
        widget3_layout.addWidget(remove_receiver_plant_btn)

        use_all_exchange_layout = QHBoxLayout()
        use_all_exchange_layout.addWidget(QLabel("劣质使用全传"))
        self.use_all_exchange_checkbox = QCheckBox()
        self.use_all_exchange_checkbox.setChecked(
            self.usersettings.auto_compound_man.use_all_exchange
        )
        self.use_all_exchange_checkbox.stateChanged.connect(
            self.use_all_exchange_checkbox_value_changed
        )
        use_all_exchange_layout.addWidget(self.use_all_exchange_checkbox)
        widget3_layout.addLayout(use_all_exchange_layout)

        allow_inherite2target_layout = QHBoxLayout()
        allow_inherite2target_layout.addWidget(QLabel("劣质传承到主力上"))
        self.allow_inherite2target_checkbox = QCheckBox()
        self.allow_inherite2target_checkbox.setChecked(
            self.usersettings.auto_compound_man.allow_inherite2target
        )
        self.allow_inherite2target_checkbox.stateChanged.connect(
            self.allow_inherite2target_checkbox_value_changed
        )
        allow_inherite2target_layout.addWidget(self.allow_inherite2target_checkbox)
        widget3_layout.addLayout(allow_inherite2target_layout)

        self.remove_abnormal_plant_btn = QPushButton("移除池中异常植物")
        self.remove_abnormal_plant_btn.clicked.connect(
            self.remove_abnormal_plant_btn_clicked
        )
        widget3_layout.addWidget(self.remove_abnormal_plant_btn)

        widget3_layout.addStretch(1)
        widget3.setLayout(widget3_layout)
        main_layout.addWidget(widget3)

        widget4 = QWidget()
        widget4.setMinimumWidth(int(self.width() * 0.25))
        widget4_layout = QVBoxLayout()
        widget4_layout.addWidget(QLabel("合成池"))
        self.plant_pool_list = QListWidget()
        self.plant_pool_list.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection
        )
        widget4_layout.addWidget(self.plant_pool_list)
        widget4.setLayout(widget4_layout)
        main_layout.addWidget(widget4)

        widget5 = QWidget()
        widget5.setFixedWidth(int(self.width() * 0.15))
        widget5_layout = QVBoxLayout()

        widget5_layout.addWidget(QLabel("当前底座"))
        self.source_plant_textbox = QPlainTextEdit()
        self.source_plant_textbox.setReadOnly(True)
        widget5_layout.addWidget(self.source_plant_textbox)

        widget5_layout.addWidget(QLabel("当前主力"))
        self.receiver_plant_textbox = QPlainTextEdit()
        self.receiver_plant_textbox.setReadOnly(True)
        widget5_layout.addWidget(self.receiver_plant_textbox)

        widget5_layout.addWidget(QLabel("当前劣质双格"))
        self.liezhi_plant_textbox = QPlainTextEdit()
        self.liezhi_plant_textbox.setReadOnly(True)
        widget5_layout.addWidget(self.liezhi_plant_textbox)

        widget5.setLayout(widget5_layout)
        main_layout.addWidget(widget5)

        widget6 = QWidget()
        widget6.setFixedWidth(int(self.width() * 0.15))
        widget6_layout = QVBoxLayout()
        widget6_layout.addStretch(1)

        widget6_1_layout = QVBoxLayout()
        widget6_1_layout.addWidget(QLabel("复合数值终点"))
        widget6_1_1_layout = QHBoxLayout()
        self.mantissa_line_edit = QLineEdit()
        self.mantissa_line_edit.setValidator(QtGui.QDoubleValidator())
        self.mantissa_line_edit.setText(
            str(self.usersettings.auto_compound_man.end_mantissa)
        )
        self.mantissa_line_edit.textChanged.connect(
            self.mantissa_line_edit_value_changed
        )
        widget6_1_1_layout.addWidget(self.mantissa_line_edit)
        widget6_1_1_layout.addWidget(QLabel("x10的"))
        self.exponent_line_edit = QLineEdit()
        self.exponent_line_edit.setValidator(QtGui.QIntValidator())
        self.exponent_line_edit.setText(
            str(self.usersettings.auto_compound_man.end_exponent)
        )
        self.exponent_line_edit.textChanged.connect(
            self.exponent_line_edit_value_changed
        )
        widget6_1_1_layout.addWidget(self.exponent_line_edit)
        widget6_1_1_layout.addWidget(QLabel("次方亿"))
        widget6_1_layout.addLayout(widget6_1_1_layout)
        widget6_layout.addLayout(widget6_1_layout)

        self.auto_compound_btn = auto_compound_btn = QPushButton("全部复合")
        auto_compound_btn.clicked.connect(self.auto_compound_btn_clicked)
        widget6_layout.addWidget(auto_compound_btn)
        self.auto_compound_single_btn = auto_compound_single_btn = QPushButton("复合一批")
        auto_compound_single_btn.clicked.connect(self.auto_compound_single_btn_clicked)
        widget6_layout.addWidget(auto_compound_single_btn)

        widget6_2_layout = QHBoxLayout()
        widget6_2_layout.addWidget(QLabel("异常后继续复合："))
        self.force_compound_checkbox = QCheckBox()
        self.force_compound_checkbox.setChecked(
            self.usersettings.auto_compound_man.force_compound
        )
        self.force_compound_checkbox.stateChanged.connect(
            self.force_compound_checkbox_value_changed
        )
        widget6_2_layout.addWidget(self.force_compound_checkbox)
        widget6_layout.addLayout(widget6_2_layout)

        widget6_layout.addWidget(QLabel("使用前请一定点击下方按钮\n查看原理"))
        illustration_btn = QPushButton("查看原理")
        illustration_btn.clicked.connect(self.illustration_btn_clicked)
        widget6_layout.addWidget(illustration_btn)

        widget6_layout.addWidget(QLabel("以下是部分合成信息"))
        self.information_text_box = QPlainTextEdit()
        self.information_text_box.setReadOnly(True)
        self.information_text_box.setMinimumHeight(int(self.height() * 0.1))
        widget6_layout.addWidget(self.information_text_box)

        widget6_layout.addStretch(1)

        widget6.setLayout(widget6_layout)
        main_layout.addWidget(widget6)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def allow_inherite2target_checkbox_value_changed(self):
        self.usersettings.auto_compound_man.allow_inherite2target = (
            self.allow_inherite2target_checkbox.isChecked()
        )

    def illustration_btn_clicked(self):
        ImageWindow("data/复合通用方案.png", self).show()

    def force_compound_checkbox_value_changed(self):
        self.usersettings.auto_compound_man.set_force_compound(
            self.force_compound_checkbox.isChecked()
        )

    def use_all_exchange_checkbox_value_changed(self):
        self.usersettings.auto_compound_man.use_all_exchange = (
            self.use_all_exchange_checkbox.isChecked()
        )

    def mantissa_line_edit_value_changed(self):
        try:
            float(self.mantissa_line_edit.text())
        except ValueError:
            self.mantissa_line_edit.setText("1.0")
        mantissa = float(self.mantissa_line_edit.text())
        self.usersettings.auto_compound_man.end_mantissa = mantissa

    def exponent_line_edit_value_changed(self):
        try:
            int(self.exponent_line_edit.text())
        except ValueError:
            self.exponent_line_edit.setText("0")
        exponent = int(self.exponent_line_edit.text())
        self.usersettings.auto_compound_man.end_exponent = exponent

    def format_plant_info(self, plant, full_msg=False):
        if isinstance(plant, str):
            plant = int(plant)
        if isinstance(plant, int):
            plant = self.usersettings.repo.get_plant(plant)
        assert isinstance(plant, Plant), type(plant).__name__
        if not full_msg:
            return "{}({})[{}]-{}:{}".format(
                plant.name(self.usersettings.lib),
                plant.grade,
                plant.quality_str,
                self.usersettings.auto_compound_man.chosen_attribute.replace("特", ""),
                format_number(
                    getattr(
                        plant,
                        self.usersettings.auto_compound_man.attribute2plant_attribute[
                            self.usersettings.auto_compound_man.chosen_attribute
                        ],
                    )
                ),
            )
        else:
            message = "{}({})[{}]\n".format(
                plant.name(self.usersettings.lib),
                plant.grade,
                plant.quality_str,
            )
            for attr_name in [
                "HP",
                "攻击",
                "命中",
                "闪避",
                "穿透",
                "护甲",
            ]:
                message += "{}:{}\n".format(
                    attr_name,
                    format_number(
                        getattr(
                            plant,
                            self.usersettings.auto_compound_man.attribute2plant_attribute[
                                attr_name
                            ],
                        )
                    ),
                )
            return message

    def _check_plant(self, plant, full_check=False, alert=True):
        result = None
        chosen_attr_name = (
            self.usersettings.auto_compound_man.attribute2plant_attribute[
                self.usersettings.auto_compound_man.chosen_attribute
            ]
        )
        for (
            attr_dict_name
        ) in self.usersettings.auto_compound_man.attribute2plant_attribute.keys():
            attr_name = self.usersettings.auto_compound_man.attribute2plant_attribute[
                attr_dict_name
            ]
            if attr_name == chosen_attr_name and not full_check:
                continue
            attr = getattr(plant, attr_name)
            if attr > 500000000:
                result = False
                break
        else:
            result = True
        if alert:
            need_continue = None
            if not result:
                need_continue = require_permission(
                    "植物{}部分数据超过设定，请确认是否继续：".format(
                        self.format_plant_info(plant, full_msg=True)
                    )
                )
            else:
                need_continue = True
            return need_continue
        else:
            return result

    def check_data(self):
        source_plant = self.usersettings.repo.get_plant(
            self.usersettings.auto_compound_man.source_plant_id
        )
        if source_plant is not None:
            if not self._check_plant(source_plant):
                self.usersettings.logger.log("合成数据检查出异常，停止合成")
                return False
        for deputy_plant_id in list(
            self.usersettings.auto_compound_man.auto_synthesis_pool_id
        ):
            deputy_plant = self.usersettings.repo.get_plant(deputy_plant_id)
            if deputy_plant is not None:
                if not self._check_plant(deputy_plant, full_check=True):
                    self.usersettings.logger.log("合成数据检查出异常，停止合成")
                    return False
        return True

    def remove_abnormal_plant_btn_clicked(self):
        cnt = 0
        for deputy_plant_id in list(
            self.usersettings.auto_compound_man.auto_synthesis_pool_id
        ):
            deputy_plant = self.usersettings.repo.get_plant(deputy_plant_id)
            if deputy_plant is None or not self._check_plant(
                deputy_plant, full_check=True, alert=False
            ):
                if not self._check_plant(deputy_plant, full_check=True, alert=False):
                    self.usersettings.auto_compound_man.auto_synthesis_pool_id.remove(
                        deputy_plant_id
                    )
                    cnt += 1
        self.usersettings.logger.log("移除了{}个异常植物".format(cnt))
        if cnt > 0:
            self.refresh_all()

    def refresh_tool_list(self):
        self.tool_list.clear()
        for tool_name in [
            "传承增强卷轴",
            "增强卷轴",
            "全属性传承书",
            "HP传承书",
            "特效HP合成书",
            "HP合成书",
            "攻击传承书",
            "特级攻击合成书",
            "攻击合成书",
            "命中传承书",
            "命中合成书",
            "闪避传承书",
            "闪避合成书",
            "穿透传承书",
            "穿透合成书",
            "护甲传承书",
            "护甲合成书",
        ]:
            tool = self.usersettings.repo.get_tool(
                self.usersettings.lib.name2tool[tool_name].id
            )
            if tool is None:
                item = QListWidgetItem(
                    "{}({})".format(
                        tool_name,
                        0,
                    )
                )
            else:
                item = QListWidgetItem(
                    "{}({})".format(
                        tool_name,
                        tool['amount'],
                    )
                )
            self.tool_list.addItem(item)

    def refresh_plant_list(self):
        self.plant_list.clear()
        for plant in self.usersettings.repo.plants:
            if (
                plant.id in self.usersettings.auto_compound_man.auto_synthesis_pool_id
                or plant.id == self.usersettings.auto_compound_man.source_plant_id
                or plant.id == self.usersettings.auto_compound_man.liezhi_plant_id
                or plant.id == self.usersettings.auto_compound_man.receiver_plant_id
            ):
                continue
            item = QListWidgetItem(self.format_plant_info(plant))
            item.setData(Qt.ItemDataRole.UserRole, plant.id)
            self.plant_list.addItem(item)

    def refresh_plant_pool_list(self):
        self.plant_pool_list.clear()
        for plant_id in self.usersettings.auto_compound_man.auto_synthesis_pool_id:
            plant = self.usersettings.repo.get_plant(plant_id)
            if plant is None:
                continue
            item = QListWidgetItem(self.format_plant_info(plant))
            item.setData(Qt.ItemDataRole.UserRole, plant_id)
            self.plant_pool_list.addItem(item)

    def refresh_information_text_box(self):
        message = []
        message.append(
            "复合池植物数量：{}个".format(
                len(self.usersettings.auto_compound_man.auto_synthesis_pool_id)
            )
        )
        message.append(
            "内置合成池植物数量：{}个".format(
                len(
                    self.usersettings.auto_compound_man.auto_synthesis_man.auto_synthesis_pool_id
                )
            )
        )
        self.information_text_box.setPlainText("\n".join(message))

    def auto_compound_attribute_choice_changed(self):
        self.usersettings.auto_compound_man.set_chosen_attribute(
            self.auto_compound_attribute_choice.currentText()
        )
        self.refresh_all()

    def k_choice_changed(self):
        self.usersettings.auto_compound_man.k = int(self.k_choice.currentText())

    def n1_choice_changed(self):
        self.usersettings.auto_compound_man.n1 = int(self.n1_choice.currentText())

    def n2_choice_changed(self):
        self.usersettings.auto_compound_man.n2 = int(self.n2_choice.currentText())

    def m_choice_changed(self):
        self.usersettings.auto_compound_man.m = int(self.m_choice.currentText())

    def refresh_liezhi_plant_textbox(self):
        if self.usersettings.auto_compound_man.liezhi_plant_id is None:
            self.liezhi_plant_textbox.setPlainText("")
            return
        plant = self.usersettings.repo.get_plant(
            self.usersettings.auto_compound_man.liezhi_plant_id
        )
        if plant is None:
            self.liezhi_plant_textbox.setPlainText("")
            return
        self.liezhi_plant_textbox.setPlainText(
            self.format_plant_info(plant, full_msg=True)
        )

    def refresh_receiver_plant_textbox(self):
        if self.usersettings.auto_compound_man.receiver_plant_id is None:
            self.receiver_plant_textbox.setPlainText("")
            return
        plant = self.usersettings.repo.get_plant(
            self.usersettings.auto_compound_man.receiver_plant_id
        )
        if plant is None:
            self.receiver_plant_textbox.setPlainText("")
            return
        self.receiver_plant_textbox.setPlainText(
            self.format_plant_info(plant, full_msg=True)
        )

    def refresh_source_plant_textbox(self):
        if self.usersettings.auto_compound_man.source_plant_id is None:
            self.source_plant_textbox.setPlainText("")
            return
        plant = self.usersettings.repo.get_plant(
            self.usersettings.auto_compound_man.source_plant_id
        )
        if plant is None:
            self.source_plant_textbox.setPlainText("")
            return
        self.source_plant_textbox.setPlainText(
            self.format_plant_info(plant, full_msg=True)
        )

    def refresh_all(self, event: Event = None):
        self.refresh_tool_list()
        self.refresh_plant_list()
        self.refresh_plant_pool_list()
        self.refresh_liezhi_plant_textbox()
        self.refresh_receiver_plant_textbox()
        self.refresh_source_plant_textbox()
        self.refresh_information_text_box()
        if event is not None:
            event.set()

    def plant_import_btn_clicked(self):
        selected_plant_id = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self.plant_list.selectedItems()
        ]
        if len(selected_plant_id) == 0:
            self.usersettings.logger.log("请先选择一个植物再导入合成池")
            return
        for plant_id in selected_plant_id:
            self.usersettings.auto_compound_man.auto_synthesis_pool_id.add(plant_id)
        self.usersettings.auto_compound_man.check_data()
        self.refresh_plant_list()
        self.refresh_plant_pool_list()
        self.refresh_information_text_box()

    def set_liezhi_plant_btn_clicked(self):
        selected_plant_id = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self.plant_list.selectedItems()
        ]
        if len(selected_plant_id) == 0:
            self.usersettings.logger.log("请先选择一个植物再设置主植物(底座)")
            return
        if len(selected_plant_id) > 1:
            self.usersettings.logger.log("一次只能设置一个主植物(底座)")
            return
        plant_id = selected_plant_id[0]
        self.usersettings.auto_compound_man.liezhi_plant_id = plant_id
        self.refresh_liezhi_plant_textbox()
        self.refresh_plant_list()

    def remove_liezhi_plant_btn_clicked(self):
        self.usersettings.auto_compound_man.liezhi_plant_id = None
        self.refresh_liezhi_plant_textbox()
        self.refresh_plant_list()

    def set_receiver_plant_btn_clicked(self):
        selected_plant_id = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self.plant_list.selectedItems()
        ]
        if len(selected_plant_id) == 0:
            self.usersettings.logger.log("请先选择一个植物再设置主植物(底座)")
            return
        if len(selected_plant_id) > 1:
            self.usersettings.logger.log("一次只能设置一个主植物(底座)")
            return
        plant_id = selected_plant_id[0]
        self.usersettings.auto_compound_man.receiver_plant_id = plant_id
        self.refresh_receiver_plant_textbox()
        self.refresh_plant_list()

    def remove_receiver_plant_btn_clicked(self):
        self.usersettings.auto_compound_man.receiver_plant_id = None
        self.refresh_receiver_plant_textbox()
        self.refresh_plant_list()

    def set_source_plant_btn_clicked(self):
        selected_plant_id = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self.plant_list.selectedItems()
        ]
        if len(selected_plant_id) == 0:
            self.usersettings.logger.log("请先选择一个植物再设置主植物(底座)")
            return
        if len(selected_plant_id) > 1:
            self.usersettings.logger.log("一次只能设置一个主植物(底座)")
            return
        plant_id = selected_plant_id[0]
        self.usersettings.auto_compound_man.source_plant_id = plant_id
        self.refresh_source_plant_textbox()
        self.refresh_plant_list()

    def remove_source_plant_btn_clicked(self):
        self.usersettings.auto_compound_man.source_plant_id = None
        self.refresh_source_plant_textbox()
        self.refresh_plant_list()

    def auto_compound_single_btn_clicked(self):
        try:
            self.auto_compound_single_btn.setDisabled(True)
            QApplication.processEvents()
            if not self.check_data():
                return
            self.usersettings.auto_compound_man.compound_one_cycle(
                self.refresh_all_signal
            )
            self.usersettings.auto_compound_man.check_data()
            self.refresh_all()
        except Exception as e:
            self.usersettings.logger.log("合成异常。异常种类：{}".format(type(e).__name__))
        finally:
            self.auto_compound_single_btn.setEnabled(True)

    def compound_stoped(self):
        self.auto_compound_btn.setText("全部复合")
        self.auto_compound_btn.setEnabled(True)

    def auto_compound_btn_clicked(self):
        self.auto_compound_btn.setDisabled(True)
        QApplication.processEvents()
        if self.auto_compound_btn.text() == "全部复合":
            try:
                if not self.check_data():
                    return
                self.auto_compound_btn.setText("停止复合")
                self.run_thread = CompoundThread(
                    self.usersettings.auto_compound_man,
                    self.compound_finish_signal,
                    self.interrupt_event,
                    self.refresh_all_signal,
                    self.rest_event,
                )
                self.rest_event.clear()
                self.run_thread.start()
            finally:
                self.auto_compound_btn.setEnabled(True)
        elif self.auto_compound_btn.text() == "停止复合":
            self.interrupt_event.set()
            WaitEventThread(self.rest_event, self.compound_stoped_signal).start()
        else:
            self.auto_compound_btn.setEnabled(True)
            raise NotImplementedError(
                "全部复合按钮文本：{} 未知".format(self.auto_compound_btn.text())
            )

    def compound_finish(self):
        self.usersettings.auto_compound_man.check_data()
        self.refresh_all()
        self.auto_compound_btn.setText("全部复合")
        self.run_thread = None
        self.interrupt_event.clear()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            selected_items = self.plant_pool_list.selectedItems()
            selected_items_id = [
                item.data(Qt.ItemDataRole.UserRole) for item in selected_items
            ]
            if len(selected_items_id) == 0:
                self.usersettings.logger.log("请先在合成池选择一个植物再删除")
                return
            for plant_id in selected_items_id:
                try:
                    self.usersettings.auto_compound_man.auto_synthesis_pool_id.remove(
                        plant_id
                    )
                except KeyError:
                    plant = self.usersettings.repo.get_plant(plant_id)
                    if plant is None:
                        self.usersettings.logger.log(
                            "仓库里没有id为{}的植物，可能已被删除".format(plant_id)
                        )
                    self.usersettings.logger.log(
                        "合成池里没有植物{}".format(self.format_plant_info(plant))
                    )
            self.refresh_plant_list()
            self.refresh_plant_pool_list()
            self.refresh_information_text_box()

    def closeEvent(self, event):
        if self.run_thread is not None:
            self.interrupt_event.set()
            # self.rest_event.wait()
        super().closeEvent(event)


class CompoundThread(Thread):
    def __init__(
        self,
        auto_compound_man,
        compound_finish_signal,
        interrupt_event: Event,
        refresh_all_signal,
        rest_event: Event,
    ):
        super().__init__()
        self.auto_compound_man = auto_compound_man
        self.compound_finish_signal = compound_finish_signal
        self.interrupt_event = interrupt_event
        self.refresh_all_signal = refresh_all_signal
        self.rest_event = rest_event

    def run(self):
        try:
            self.auto_compound_man.compound_loop(
                self.interrupt_event, self.refresh_all_signal
            )
        finally:
            self.compound_finish_signal.emit()
            self.rest_event.set()
