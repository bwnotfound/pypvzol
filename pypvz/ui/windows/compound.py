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
from ...utils.common import format_number
from ...repository import Plant
from .common import ImageWindow, require_permission
from ... import Config, Repository, Library
from ..message import Logger
from ..user.compound import AutoCompoundMan, CompoundScheme
from ...upgrade import quality_name_list


class AutoCompoundWindow(QMainWindow):
    compound_finish_signal = pyqtSignal()
    refresh_all_signal = pyqtSignal(Event)
    compound_stoped_signal = pyqtSignal()

    def __init__(
        self,
        cfg: Config,
        lib: Library,
        repo: Repository,
        logger: Logger,
        auto_compound_man: AutoCompoundMan,
        parent=None,
    ):
        super().__init__(parent=parent)
        self.cfg = cfg
        self.lib = lib
        self.repo = repo
        self.logger = logger
        self.auto_compound_man = auto_compound_man
        self.interrupt_event = Event()
        self.rest_event = Event()
        self.rest_event.set()
        self.run_thread = None
        self.refresh_all_signal.connect(self.refresh_all)
        self.compound_finish_signal.connect(self.compound_finish)
        self.compound_stoped_signal.connect(self.compound_stoped)
        self.chosen_attribute = "HP特"
        self.scheme_widget = CompoundSchemeWidget(
            self.repo,
            self.format_plant_info,
            self.set_chosen_attribute,
            self.refresh_all_signal,
            self.logger,
            self,
        )
        self.init_ui()
        self.scheme_widget.plant_list_widget = self.plant_list
        self.refresh_all()
        self.refresh_scheme_list()

    def init_ui(self):
        self.setWindowTitle("自动复合")

        # 将窗口居中显示，宽度为显示器宽度的80%，高度为显示器高度的80%
        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.95), int(screen_size.height() * 0.8))
        self.move(int(screen_size.width() * 0.025), int(screen_size.height() * 0.1))

        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_layout.setSpacing(0)

        widget1 = QWidget()
        widget1.setFixedWidth(int(self.width() * 0.11))
        widget1_layout = QVBoxLayout()
        widget1_layout.addWidget(QLabel("物品列表"))
        self.tool_list = QListWidget()
        self.tool_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        widget1_layout.addWidget(self.tool_list)
        widget1.setLayout(widget1_layout)
        main_layout.addWidget(widget1)

        widget2 = QWidget()
        widget2.setMinimumWidth(int(self.width() * 0.21))
        widget2_layout = QVBoxLayout()
        widget2_layout.addWidget(QLabel("植物列表"))
        self.plant_list = QListWidget()
        self.plant_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        widget2_layout.addWidget(self.plant_list)
        widget2.setLayout(widget2_layout)
        main_layout.addWidget(widget2)

        widget3 = QWidget()
        widget3.setFixedWidth(int(self.width() * 0.11))
        widget3_layout = QVBoxLayout()
        widget3_layout.addStretch(1)

        plant_import_btn = QPushButton("导入复合池")
        plant_import_btn.clicked.connect(self.plant_import_btn_clicked)
        widget3_layout.addWidget(plant_import_btn)

        set_liezhi_plant_btn = QPushButton("设置劣质双格")
        set_liezhi_plant_btn.clicked.connect(self.set_liezhi_plant_btn_clicked)
        widget3_layout.addWidget(set_liezhi_plant_btn)

        remove_liezhi_plant_btn = QPushButton("移除劣质双格")
        remove_liezhi_plant_btn.clicked.connect(self.remove_liezhi_plant_btn_clicked)
        widget3_layout.addWidget(remove_liezhi_plant_btn)

        set_receiver_plant_btn = QPushButton("设置主力")
        set_receiver_plant_btn.clicked.connect(self.set_receiver_plant_btn_clicked)
        widget3_layout.addWidget(set_receiver_plant_btn)

        remove_receiver_plant_btn = QPushButton("移除主力")
        remove_receiver_plant_btn.clicked.connect(
            self.remove_receiver_plant_btn_clicked
        )
        widget3_layout.addWidget(remove_receiver_plant_btn)

        allow_inherite2target_layout = QHBoxLayout()
        allow_inherite2target_layout.addWidget(QLabel("劣质传承到主力上"))
        self.allow_inherite2target_checkbox = QCheckBox()
        self.allow_inherite2target_checkbox.setChecked(
            self.auto_compound_man.allow_inherite2target
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
        widget4.setMinimumWidth(int(self.width() * 0.2))
        widget4_layout = QVBoxLayout()
        widget4_layout.addWidget(QLabel("复合池"))
        self.plant_pool_list = QListWidget()
        self.plant_pool_list.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection
        )
        widget4_layout.addWidget(self.plant_pool_list)
        widget4.setLayout(widget4_layout)
        main_layout.addWidget(widget4)

        widget5 = QWidget()
        widget5.setFixedWidth(int(self.width() * 0.11))
        widget5_layout = QVBoxLayout()

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
        widget6.setFixedWidth(int(self.width() * 0.11))
        widget6_layout = QVBoxLayout()

        widget6_layout.addWidget(QLabel("复合方案"))
        self.scheme_list = QListWidget()
        self.scheme_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.scheme_list.itemClicked.connect(self.scheme_list_item_clicked)
        widget6_layout.addWidget(self.scheme_list)
        self.scheme_name_inputbox = QLineEdit()
        widget6_layout.addWidget(self.scheme_name_inputbox)
        add_scheme_btn = QPushButton("新建方案")
        add_scheme_btn.clicked.connect(self.add_scheme_btn_clicked)
        widget6_layout.addWidget(add_scheme_btn)
        remove_scheme_btn = QPushButton("删除方案")
        remove_scheme_btn.clicked.connect(self.remove_scheme_btn_clicked)
        widget6_layout.addWidget(remove_scheme_btn)
        rename_scheme_btn = QPushButton("重命名方案")
        rename_scheme_btn.clicked.connect(self.rename_scheme_btn_clicked)
        widget6_layout.addWidget(rename_scheme_btn)
        enable_scheme_btn = QPushButton("启用方案")
        enable_scheme_btn.clicked.connect(self.enable_scheme_btn_clicked)
        widget6_layout.addWidget(enable_scheme_btn)
        disable_scheme_btn = QPushButton("禁用方案")
        disable_scheme_btn.clicked.connect(self.disable_scheme_btn_clicked)
        widget6_layout.addWidget(disable_scheme_btn)
        widget6_layout.addWidget(QLabel("\n"))
        self.auto_compound_btn = auto_compound_btn = QPushButton("全部复合")
        auto_compound_btn.clicked.connect(self.auto_compound_btn_clicked)
        widget6_layout.addWidget(auto_compound_btn)
        self.auto_set_plant_btn = QPushButton("自动上底座")
        self.auto_set_plant_btn.clicked.connect(self.auto_set_plant_btn_clicked)
        widget6_layout.addWidget(self.auto_set_plant_btn)
        # self.auto_compound_single_btn = auto_compound_single_btn = QPushButton("复合一批")
        # auto_compound_single_btn.clicked.connect(self.auto_compound_single_btn_clicked)
        # widget6_layout.addWidget(auto_compound_single_btn)

        widget6_layout.addWidget(QLabel("\n"))
        illustration_btn = QPushButton("查看原理")
        illustration_btn.clicked.connect(self.illustration_btn_clicked)
        widget6_layout.addWidget(illustration_btn)
        parameter_recommend_btn = QPushButton("参数推荐")
        parameter_recommend_btn.clicked.connect(self.parameter_recommend_btn_clicked)
        widget6_layout.addWidget(parameter_recommend_btn)

        widget6_layout.addWidget(QLabel("以下是部分合成信息"))
        self.information_text_box = QPlainTextEdit()
        self.information_text_box.setReadOnly(True)
        self.information_text_box.setMinimumHeight(int(self.height() * 0.1))
        widget6_layout.addWidget(self.information_text_box)

        widget6_layout.addStretch(1)
        widget6.setLayout(widget6_layout)
        main_layout.addWidget(widget6)

        self.scheme_widget.setFixedWidth(int(self.width() * 0.14))
        main_layout.addWidget(self.scheme_widget)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def parameter_recommend_btn_clicked(self):
        ImageWindow("data/image/参数推荐.png", self).show()

    def set_chosen_attribute(self, chosen_attribute):
        self.chosen_attribute = chosen_attribute

    def scheme_list_item_clicked(self, item: QListWidgetItem):
        scheme = item.data(Qt.ItemDataRole.UserRole)
        self.scheme_name_inputbox.setText(scheme.name)
        self.scheme_widget.switch_scheme(scheme)

    def add_scheme_btn_clicked(self):
        self.auto_compound_man.new_scheme()
        self.refresh_scheme_list()

    def remove_scheme_btn_clicked(self):
        selected_items = self.scheme_list.selectedItems()
        if len(selected_items) == 0:
            self.logger.log("请先选择一个方案再删除")
            return
        selected_scheme = [
            item.data(Qt.ItemDataRole.UserRole) for item in selected_items
        ]
        for scheme in selected_scheme:
            self.auto_compound_man.remove_scheme(scheme)
        self.scheme_widget.switch_scheme(None)
        self.refresh_scheme_list()

    def rename_scheme_btn_clicked(self):
        selected_items = self.scheme_list.selectedItems()
        if len(selected_items) == 0:
            self.logger.log("请先选择一个方案再重命名")
            return
        selected_scheme = [
            item.data(Qt.ItemDataRole.UserRole) for item in selected_items
        ]
        if len(selected_scheme) > 1:
            self.logger.log("一次只能选择一个方案")
            return
        scheme = selected_scheme[0]
        scheme.name = self.scheme_name_inputbox.text()
        self.refresh_scheme_list()

    def enable_scheme_btn_clicked(self):
        selected_items = self.scheme_list.selectedItems()
        if len(selected_items) == 0:
            self.logger.log("请先选择一个方案再启用")
            return
        selected_scheme = [
            item.data(Qt.ItemDataRole.UserRole) for item in selected_items
        ]
        for scheme in selected_scheme:
            scheme.enabled = True
        self.refresh_scheme_list()

    def disable_scheme_btn_clicked(self):
        selected_items = self.scheme_list.selectedItems()
        if len(selected_items) == 0:
            self.logger.log("请先选择一个方案再禁用")
            return
        selected_scheme = [
            item.data(Qt.ItemDataRole.UserRole) for item in selected_items
        ]
        for scheme in selected_scheme:
            scheme.enabled = False
        self.refresh_scheme_list()

    def auto_set_plant_btn_clicked(self):
        self.auto_compound_man.auto_set_source_plant()
        self.refresh_all()

    def refresh_scheme_list(self):
        self.scheme_list.clear()
        for scheme in self.auto_compound_man.scheme_list:
            item = QListWidgetItem(
                "({}){}".format("启用" if scheme.enabled else "禁用", scheme.name)
            )
            item.setData(Qt.ItemDataRole.UserRole, scheme)
            self.scheme_list.addItem(item)

    def allow_inherite2target_checkbox_value_changed(self):
        self.auto_compound_man.allow_inherite2target = (
            self.allow_inherite2target_checkbox.isChecked()
        )

    def illustration_btn_clicked(self):
        ImageWindow("data/image/复合通用方案.png", self).show()

    def format_plant_info(self, plant, chosen_attribute=None):
        if isinstance(plant, str):
            plant = int(plant)
        if isinstance(plant, int):
            plant = self.repo.get_plant(plant)
        assert isinstance(plant, Plant), type(plant).__name__
        if chosen_attribute is not None:
            return "{}({})[{}]-{}:{}".format(
                plant.name(self.lib),
                plant.grade,
                plant.quality_str,
                chosen_attribute.replace("特", ""),
                format_number(
                    getattr(
                        plant,
                        self.auto_compound_man.attribute2plant_attribute[
                            chosen_attribute
                        ],
                    )
                ),
            )
        else:
            message = "{}({})[{}]\n".format(
                plant.name(self.lib),
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
                            self.auto_compound_man.attribute2plant_attribute[attr_name],
                        )
                    ),
                )
            return message

    def _check_plant(self, plant, chosen_attr_name=None, alert=True):
        result = None
        if (
            chosen_attr_name is not None
            and chosen_attr_name in self.auto_compound_man.attribute2plant_attribute
        ):
            chosen_attr_name = self.auto_compound_man.attribute2plant_attribute[
                chosen_attr_name
            ]
        for attr_dict_name in self.auto_compound_man.attribute2plant_attribute.keys():
            attr_name = self.auto_compound_man.attribute2plant_attribute[attr_dict_name]
            if chosen_attr_name is not None and attr_name == chosen_attr_name:
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
                    "植物{}部分数据超过设定，请确认是否继续：".format(self.format_plant_info(plant))
                )
            else:
                need_continue = True
            return need_continue
        else:
            return result

    def check_data(self):
        for scheme in self.auto_compound_man.scheme_list:
            if not scheme.enabled:
                continue
            source_plant = self.repo.get_plant(scheme.source_plant_id)
            if source_plant is not None:
                if not self._check_plant(source_plant, scheme.chosen_attribute):
                    self.logger.log("合成数据检查出异常，停止合成")
                    return False
        for deputy_plant_id in list(self.auto_compound_man.auto_compound_pool_id):
            deputy_plant = self.repo.get_plant(deputy_plant_id)
            if deputy_plant is not None:
                if not self._check_plant(deputy_plant):
                    self.logger.log("合成数据检查出异常，停止合成")
                    return False
        return True

    def remove_abnormal_plant_btn_clicked(self):
        cnt = 0
        for deputy_plant_id in list(self.auto_compound_man.auto_compound_pool_id):
            deputy_plant = self.repo.get_plant(deputy_plant_id)
            if deputy_plant is None or not self._check_plant(deputy_plant, alert=False):
                if not self._check_plant(deputy_plant, alert=False):
                    self.auto_compound_man.auto_compound_pool_id.remove(deputy_plant_id)
                    cnt += 1
        self.logger.log("移除了{}个异常植物".format(cnt))
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
            tool = self.repo.get_tool(self.lib.name2tool[tool_name].id)
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
        used_plant_id_set = set()
        used_plant_id_set.add(self.auto_compound_man.liezhi_plant_id)
        used_plant_id_set.add(self.auto_compound_man.receiver_plant_id)
        for plant_id in self.auto_compound_man.auto_compound_pool_id:
            used_plant_id_set.add(plant_id)
        for scheme in self.auto_compound_man.scheme_list:
            if not scheme.enabled:
                continue
            used_plant_id_set.add(scheme.source_plant_id)
            for plant_id in scheme.auto_compound_pool_id:
                used_plant_id_set.add(plant_id)
            for plant_id in scheme.auto_synthesis_man.auto_synthesis_pool_id:
                used_plant_id_set.add(plant_id)
        for plant in self.repo.plants:
            if plant.id in used_plant_id_set:
                continue
            item = QListWidgetItem(
                self.format_plant_info(plant, chosen_attribute=self.chosen_attribute)
            )
            item.setData(Qt.ItemDataRole.UserRole, plant.id)
            self.plant_list.addItem(item)

    def refresh_plant_pool_list(self):
        self.plant_pool_list.clear()
        for plant_id in self.auto_compound_man.auto_compound_pool_id:
            plant = self.repo.get_plant(plant_id)
            if plant is None:
                continue
            item = QListWidgetItem(
                self.format_plant_info(plant, chosen_attribute=self.chosen_attribute)
            )
            item.setData(Qt.ItemDataRole.UserRole, plant_id)
            self.plant_pool_list.addItem(item)

    def refresh_liezhi_plant_textbox(self):
        if self.auto_compound_man.liezhi_plant_id is None:
            self.liezhi_plant_textbox.setPlainText("")
            return
        plant = self.repo.get_plant(self.auto_compound_man.liezhi_plant_id)
        if plant is None:
            self.liezhi_plant_textbox.setPlainText("")
            return
        self.liezhi_plant_textbox.setPlainText(self.format_plant_info(plant))

    def refresh_receiver_plant_textbox(self):
        if self.auto_compound_man.receiver_plant_id is None:
            self.receiver_plant_textbox.setPlainText("")
            return
        plant = self.repo.get_plant(self.auto_compound_man.receiver_plant_id)
        if plant is None:
            self.receiver_plant_textbox.setPlainText("")
            return
        self.receiver_plant_textbox.setPlainText(self.format_plant_info(plant))

    def refresh_information_text_box(self):
        message = []
        message.append(
            "复合池植物总数量：{}个".format(len(self.auto_compound_man.auto_compound_pool_id))
        )
        plant_quality_dict = {k: 0 for k in quality_name_list}
        for plant_id in self.auto_compound_man.auto_compound_pool_id:
            plant = self.repo.get_plant(plant_id)
            if plant is None:
                continue
            plant_quality_dict[plant.quality_str] += 1
        for quality_name in reversed(quality_name_list):
            amount = plant_quality_dict[quality_name]
            if amount == 0:
                continue
            message.append("{}植物数量：{}个".format(quality_name, amount))
        self.information_text_box.setPlainText("\n".join(message))

    def refresh_all(self, event: Event = None):
        self.refresh_tool_list()
        self.refresh_plant_list()
        self.refresh_plant_pool_list()
        self.refresh_liezhi_plant_textbox()
        self.refresh_receiver_plant_textbox()
        self.refresh_information_text_box()
        self.scheme_widget.refresh_all()
        if event is not None:
            event.set()

    def plant_import_btn_clicked(self):
        selected_plant_id = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self.plant_list.selectedItems()
        ]
        if len(selected_plant_id) == 0:
            self.logger.log("请先选择一个植物再导入合成池")
            return
        for plant_id in selected_plant_id:
            self.auto_compound_man.auto_compound_pool_id.add(plant_id)
        self.auto_compound_man.check_data()
        self.refresh_plant_list()
        self.refresh_plant_pool_list()
        self.refresh_information_text_box()

    def set_liezhi_plant_btn_clicked(self):
        selected_plant_id = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self.plant_list.selectedItems()
        ]
        if len(selected_plant_id) == 0:
            self.logger.log("请先选择一个植物再设置主植物(底座)")
            return
        if len(selected_plant_id) > 1:
            self.logger.log("一次只能设置一个主植物(底座)")
            return
        plant_id = selected_plant_id[0]
        self.auto_compound_man.liezhi_plant_id = plant_id
        self.refresh_liezhi_plant_textbox()
        self.refresh_plant_list()

    def remove_liezhi_plant_btn_clicked(self):
        self.auto_compound_man.liezhi_plant_id = None
        self.refresh_liezhi_plant_textbox()
        self.refresh_plant_list()

    def set_receiver_plant_btn_clicked(self):
        selected_plant_id = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self.plant_list.selectedItems()
        ]
        if len(selected_plant_id) == 0:
            self.logger.log("请先选择一个植物再设置主植物(底座)")
            return
        if len(selected_plant_id) > 1:
            self.logger.log("一次只能设置一个主植物(底座)")
            return
        plant_id = selected_plant_id[0]
        self.auto_compound_man.receiver_plant_id = plant_id
        self.refresh_receiver_plant_textbox()
        self.refresh_plant_list()

    def remove_receiver_plant_btn_clicked(self):
        self.auto_compound_man.receiver_plant_id = None
        self.refresh_receiver_plant_textbox()
        self.refresh_plant_list()

    # def auto_compound_single_btn_clicked(self):
    #     try:
    #         self.auto_compound_single_btn.setDisabled(True)
    #         QApplication.processEvents()
    #         if not self.check_data():
    #             return
    #         self.auto_compound_man.compound_one_cycle(self.refresh_all_signal)
    #         self.auto_compound_man.check_data()
    #         self.refresh_all()
    #     except Exception as e:
    #         self.logger.log("合成异常。异常种类：{}".format(type(e).__name__))
    #     finally:
    #         self.auto_compound_single_btn.setEnabled(True)

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
                    self.auto_compound_man,
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
        self.auto_compound_man.check_data()
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
                self.logger.log("请先在合成池选择一个植物再删除")
                return
            for plant_id in selected_items_id:
                try:
                    self.auto_compound_man.auto_compound_pool_id.remove(plant_id)
                except KeyError:
                    plant = self.repo.get_plant(plant_id)
                    if plant is None:
                        self.logger.log("仓库里没有id为{}的植物，可能已被删除".format(plant_id))
                    self.logger.log(
                        "合成池里没有植物{}".format(
                            self.format_plant_info(
                                plant, chosen_attribute=self.chosen_attribute
                            )
                        )
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
        reach_target_event: Event = None,
    ):
        super().__init__()
        self.auto_compound_man = auto_compound_man
        self.compound_finish_signal = compound_finish_signal
        self.interrupt_event = interrupt_event
        self.refresh_all_signal = refresh_all_signal
        self.rest_event = rest_event
        self.reach_target_event = reach_target_event

    def run(self):
        try:
            self.auto_compound_man.compound_loop(
                self.interrupt_event,
                self.refresh_all_signal,
                reach_target_event=self.reach_target_event,
            )
        finally:
            if self.compound_finish_signal is not None:
                self.compound_finish_signal.emit()
            self.rest_event.set()


class CompoundSchemeWidget(QWidget):
    def __init__(
        self,
        repo: Repository,
        format_plant_info,
        set_chosen_attribute,
        refresh_all_signal,
        logger: Logger,
        parent=None,
    ):
        super().__init__(parent=parent)
        self.repo = repo
        self.set_chosen_attribute = set_chosen_attribute
        self.format_plant_info = format_plant_info
        self.scheme = None
        self.plant_list_widget = None
        self.logger = logger
        self.refresh_all_signal = refresh_all_signal
        self.main_layout = QHBoxLayout()
        self.setLayout(self.main_layout)

    def switch_scheme(self, scheme: CompoundScheme):
        self.scheme = scheme
        from .common import delete_layout_children

        delete_layout_children(self.main_layout)
        if self.scheme is not None:
            self.init_ui()
            self.set_chosen_attribute(self.scheme.chosen_attribute)
            self.refresh_all_signal.emit(Event())
            self.refresh_all()

    def init_ui(self):
        setting_panel = QWidget()
        setting_panel_layout = QVBoxLayout()

        setting_panel_layout.addWidget(QLabel("当前底座"))
        self.source_plant_textbox = QPlainTextEdit()
        self.source_plant_textbox.setReadOnly(True)
        setting_panel_layout.addWidget(self.source_plant_textbox)

        setting_panel_layout.addWidget(QLabel("选择复合属性"))
        self.auto_compound_attribute_choice = QComboBox()
        for name in self.scheme.attribute_list:
            self.auto_compound_attribute_choice.addItem(name)
        self.auto_compound_attribute_choice.setCurrentIndex(
            self.scheme.attribute_list.index(self.scheme.chosen_attribute)
        )
        self.auto_compound_attribute_choice.currentIndexChanged.connect(
            self.auto_compound_attribute_choice_changed
        )
        setting_panel_layout.addWidget(self.auto_compound_attribute_choice)

        layout1 = QHBoxLayout()
        layout1.addWidget(QLabel("k值:"))
        self.k_choice = QComboBox()
        for i in range(11):
            self.k_choice.addItem(str(i))
        self.k_choice.setCurrentIndex(self.scheme.k)
        self.k_choice.currentIndexChanged.connect(self.k_choice_changed)
        layout1.addWidget(self.k_choice)
        setting_panel_layout.addLayout(layout1)

        layout2 = QHBoxLayout()
        layout2.addWidget(QLabel("n1值:"))
        self.n1_choice = QComboBox()
        for i in range(11):
            self.n1_choice.addItem(str(i))
        self.n1_choice.setCurrentIndex(self.scheme.n1)
        self.n1_choice.currentIndexChanged.connect(self.n1_choice_changed)
        layout2.addWidget(self.n1_choice)
        setting_panel_layout.addLayout(layout2)

        layout3 = QHBoxLayout()
        layout3.addWidget(QLabel("n2值:"))
        self.n2_choice = QComboBox()
        for i in range(31):
            self.n2_choice.addItem(str(i))
        self.n2_choice.setCurrentIndex(self.scheme.n2)
        self.n2_choice.currentIndexChanged.connect(self.n2_choice_changed)
        layout3.addWidget(self.n2_choice)
        setting_panel_layout.addLayout(layout3)

        layout4 = QHBoxLayout()
        layout4.addWidget(QLabel("m值:"))
        self.m_choice = QComboBox()
        for i in range(16):
            self.m_choice.addItem(str(i))
        self.m_choice.setCurrentIndex(self.scheme.m)
        self.m_choice.currentIndexChanged.connect(self.m_choice_changed)
        layout4.addWidget(self.m_choice)
        setting_panel_layout.addLayout(layout4)

        set_source_plant_btn = QPushButton("设置底座")
        set_source_plant_btn.clicked.connect(self.set_source_plant_btn_clicked)
        setting_panel_layout.addWidget(set_source_plant_btn)

        remove_source_plant_btn = QPushButton("移除底座")
        remove_source_plant_btn.clicked.connect(self.remove_source_plant_btn_clicked)
        setting_panel_layout.addWidget(remove_source_plant_btn)

        setting_panel_layout.addWidget(QLabel("复合数值终点"))
        widget6_1_1_layout = QHBoxLayout()
        self.mantissa_line_edit = QLineEdit()
        self.mantissa_line_edit.setValidator(QtGui.QDoubleValidator())
        self.mantissa_line_edit.setText(str(self.scheme.end_mantissa))
        self.mantissa_line_edit.textChanged.connect(
            self.mantissa_line_edit_value_changed
        )
        widget6_1_1_layout.addWidget(self.mantissa_line_edit)
        widget6_1_1_layout.addWidget(QLabel("x10的"))
        self.exponent_line_edit = QLineEdit()
        self.exponent_line_edit.setValidator(QtGui.QIntValidator())
        self.exponent_line_edit.setText(str(self.scheme.end_exponent))
        self.exponent_line_edit.textChanged.connect(
            self.exponent_line_edit_value_changed
        )
        widget6_1_1_layout.addWidget(self.exponent_line_edit)
        widget6_1_1_layout.addWidget(QLabel("次方亿"))
        setting_panel_layout.addLayout(widget6_1_1_layout)

        setting_panel_layout.addWidget(QLabel("所需要的植物品质"))
        self.quality_choice = QComboBox()
        for quality_name in quality_name_list:
            self.quality_choice.addItem(quality_name)
        self.quality_choice.setCurrentIndex(self.scheme.need_quality_index)
        self.quality_choice.currentIndexChanged.connect(self.quality_choice_changed)
        setting_panel_layout.addWidget(self.quality_choice)

        setting_panel_layout.addWidget(QLabel("以下是部分合成信息"))
        self.information_text_box = QPlainTextEdit()
        self.information_text_box.setReadOnly(True)
        self.information_text_box.setMinimumHeight(int(self.height() * 0.1))
        setting_panel_layout.addWidget(self.information_text_box)

        setting_panel_layout.addStretch(1)
        setting_panel.setLayout(setting_panel_layout)
        self.main_layout.addWidget(setting_panel)

    def quality_choice_changed(self):
        self.scheme.need_quality_index = self.quality_choice.currentIndex()

    def mantissa_line_edit_value_changed(self):
        try:
            float(self.mantissa_line_edit.text())
        except ValueError:
            self.mantissa_line_edit.setText("1.0")
        mantissa = float(self.mantissa_line_edit.text())
        self.scheme.end_mantissa = mantissa

    def exponent_line_edit_value_changed(self):
        try:
            int(self.exponent_line_edit.text())
        except ValueError:
            self.exponent_line_edit.setText("0")
        exponent = int(self.exponent_line_edit.text())
        self.scheme.end_exponent = exponent

    def auto_compound_attribute_choice_changed(self):
        self.scheme.set_chosen_attribute(
            self.auto_compound_attribute_choice.currentText()
        )
        self.set_chosen_attribute(self.scheme.chosen_attribute)
        self.refresh_all_signal.emit(Event())

    def k_choice_changed(self):
        self.scheme.k = int(self.k_choice.currentText())

    def n1_choice_changed(self):
        self.scheme.n1 = int(self.n1_choice.currentText())

    def n2_choice_changed(self):
        self.scheme.n2 = int(self.n2_choice.currentText())

    def m_choice_changed(self):
        self.scheme.m = int(self.m_choice.currentText())

    def set_source_plant_btn_clicked(self):
        selected_plant_id = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self.plant_list_widget.selectedItems()
        ]
        if len(selected_plant_id) == 0:
            self.logger.log("请先选择一个植物再设置主植物(底座)")
            return
        if len(selected_plant_id) > 1:
            self.logger.log("一次只能设置一个主植物(底座)")
            return
        plant_id = selected_plant_id[0]
        self.scheme.source_plant_id = plant_id
        self.refresh_all_signal.emit(Event())

    def remove_source_plant_btn_clicked(self):
        self.scheme.source_plant_id = None
        self.refresh_all_signal.emit(Event())

    def refresh_information_text_box(self):
        if self.scheme is None:
            return
        message = []
        message.append(
            '方案"{}"中复合池植物数量：{}个'.format(
                self.scheme.name, len(self.scheme.auto_compound_pool_id)
            )
        )
        message.append(
            '方案"{}"中内置合成池植物数量：{}个'.format(
                self.scheme.name,
                len(self.scheme.auto_synthesis_man.auto_synthesis_pool_id),
            )
        )
        self.information_text_box.setPlainText("\n".join(message))

    def refresh_source_plant_textbox(self):
        if self.scheme is None:
            return
        if self.scheme.source_plant_id is None:
            self.source_plant_textbox.setPlainText("")
            return
        plant = self.repo.get_plant(self.scheme.source_plant_id)
        if plant is None:
            self.source_plant_textbox.setPlainText("")
            return
        self.source_plant_textbox.setPlainText(self.format_plant_info(plant))

    def refresh_all(self):
        self.refresh_source_plant_textbox()
        self.refresh_information_text_box()
