import logging
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QTabWidget,
    QLineEdit,
)
from PyQt6 import QtGui
from PyQt6.QtCore import Qt

from ..wrapped import QLabel
from ..message import Logger
from ...shop import PurchaseItem
from ... import Config, Library, Shop


class ShopAutoBuySetting(QMainWindow):
    def __init__(
        self,
        cfg: Config,
        lib: Library,
        logger: Logger,
        shop_auto_buy_dict: dict[int, PurchaseItem],
        target_mode,
        parent=None,
    ):
        super().__init__(parent=parent)
        self.lib = lib
        self.shop = Shop(cfg)
        self.logger = logger
        self.shop_auto_buy_dict = shop_auto_buy_dict
        self.target_mode = target_mode
        self.shop.refresh_shop()
        self.init_ui()
        self.refresh_auto_buy_list()
        self.refresh_shop_list()

    def init_ui(self):
        self.setWindowTitle("商店自动购买设置")

        # 将窗口居中显示，宽度为显示器宽度的60%，高度为显示器高度的50%
        screen_size = QtGui.QGuiApplication.primaryScreen().size()
        self.resize(int(screen_size.width() * 0.8), int(screen_size.height() * 0.6))
        self.move(int(screen_size.width() * 0.1), int(screen_size.height() * 0.2))

        main_widget = QWidget()
        main_layout = QHBoxLayout()

        shop_list_widget = QWidget()
        shop_list_widget.setFixedWidth(int(self.width() * 0.4))
        shop_list_layout = QVBoxLayout()
        shop_list_layout.addWidget(QLabel("商店列表"))
        self.shop_list_tab = QTabWidget()
        shop_list_layout.addWidget(self.shop_list_tab)
        for name in self.shop.shop_name_list:
            shop_list = QListWidget()
            shop_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
            self.shop_list_tab.addTab(shop_list, name)
        # 设置shop_list_tab的tab名称宽度一定
        # self.shop_list_tab.setStyleSheet("QTabBar::tab { max-width: 100px; }")
        self.shop_list_tab.setCurrentIndex(0)
        self.shop_list_tab.currentChanged.connect(self.refresh_shop_list)
        shop_list_widget.setLayout(shop_list_layout)
        main_layout.addWidget(shop_list_widget)

        btn_panel_widget = QWidget()
        btn_panel_layout = QVBoxLayout()

        layout1 = QHBoxLayout()
        self.set_auto_buy_amount_inputbox = QLineEdit()
        if not self.target_mode:
            layout1.addWidget(QLabel("设置购买数量:"))
            self.set_auto_buy_amount_inputbox.setText("1")
            self.set_auto_buy_amount_inputbox.setValidator(
                QtGui.QIntValidator(1, 99999)
            )
        else:
            layout1.addWidget(QLabel("设置购买到多少为止:"))
            self.set_auto_buy_amount_inputbox.setText("0")
            self.set_auto_buy_amount_inputbox.setValidator(
                QtGui.QIntValidator(0, 99999)
            )
        layout1.addWidget(self.set_auto_buy_amount_inputbox)
        btn_panel_layout.addLayout(layout1)

        set_auto_buy_btn = QPushButton("设为自动购买")
        set_auto_buy_btn.clicked.connect(self.set_auto_buy_btn_clicked)
        btn_panel_layout.addWidget(set_auto_buy_btn)
        self.change_auto_buy_amount_layout = QHBoxLayout()
        self.auto_buy_amount_inputbox = QLineEdit()
        self.auto_buy_amount_inputbox.setText("")
        self.auto_buy_amount_inputbox.setDisabled(True)
        if not self.target_mode:
            self.change_auto_buy_amount_layout.addWidget(QLabel("修改购买数量:"))
            self.auto_buy_amount_inputbox.setValidator(QtGui.QIntValidator(1, 99999))
        else:
            self.change_auto_buy_amount_layout.addWidget(QLabel("修改购买到多少为止:"))
            self.auto_buy_amount_inputbox.setValidator(QtGui.QIntValidator(0, 99999))
        self.change_auto_buy_amount_layout.addWidget(self.auto_buy_amount_inputbox)
        self.auto_buy_amount_btn = QPushButton("修改")
        self.auto_buy_amount_btn.clicked.connect(self.set_auto_buy_amount_btn_clicked)
        self.auto_buy_amount_btn.setDisabled(True)
        self.change_auto_buy_amount_layout.addWidget(self.auto_buy_amount_btn)
        btn_panel_layout.addLayout(self.change_auto_buy_amount_layout)

        btn_panel_widget.setLayout(btn_panel_layout)
        main_layout.addWidget(btn_panel_widget)

        auto_buy_list_widget = QWidget()
        auto_buy_list_widget.setFixedWidth(int(self.width() * 0.25))
        auto_buy_list_layout = QVBoxLayout()
        if not self.target_mode:
            auto_buy_list_layout.addWidget(QLabel("自动购买列表"))
        else:
            auto_buy_list_layout.addWidget(
                QLabel("自动购买列表,括号内是要购买到剩多少的数量")
            )
        self.auto_buy_list = QListWidget()
        self.auto_buy_list.itemPressed.connect(self.auto_buy_list_item_pressed)
        self.auto_buy_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        auto_buy_list_layout.addWidget(self.auto_buy_list)
        auto_buy_list_widget.setLayout(auto_buy_list_layout)
        main_layout.addWidget(auto_buy_list_widget)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def refresh_shop_list(self):
        shop_index = self.shop_list_tab.currentIndex()
        shop_list = self.shop_list_tab.currentWidget()
        shop_list.clear()
        for shop_item in self.shop.shop_goods_list[shop_index]:
            if shop_item.type == "tool":
                tool = self.lib.get_tool_by_id(shop_item.p_id)
                item = QListWidgetItem(f"{tool.name}({shop_item.num})")
                item.setData(Qt.ItemDataRole.UserRole, shop_item)
                shop_list.addItem(item)
            elif shop_item.type == "organisms":
                plant = self.lib.get_plant_by_id(shop_item.p_id)
                item = QListWidgetItem(f"{plant.name}({shop_item.num})")
                item.setData(Qt.ItemDataRole.UserRole, shop_item)
                shop_list.addItem(item)
            else:
                self.logger.log(f"未知的商店商品类型:{shop_item.type}")
                raise NotImplementedError(f"未知的商店商品类型:{shop_item.type}")

    def auto_buy_list_item_pressed(self, item: QListWidgetItem):
        purchase_item = item.data(Qt.ItemDataRole.UserRole)
        if not self.target_mode:
            self.auto_buy_amount_inputbox.setText(str(purchase_item.amount))
        else:
            self.auto_buy_amount_inputbox.setText(str(purchase_item.target_amount))
        self.auto_buy_amount_inputbox.setEnabled(True)
        self.auto_buy_amount_btn.setEnabled(True)

    def set_auto_buy_amount_btn_clicked(self):
        selected_items = self.auto_buy_list.selectedItems()
        selected_items = [
            item.data(Qt.ItemDataRole.UserRole) for item in selected_items
        ]
        if len(selected_items) != 1:
            self.logger.log("请只选择一个商品", True)
            return
        purchase_item = selected_items[0]
        amount = self.auto_buy_amount_inputbox.text()
        amount = int(amount) if amount != "" else 1
        if not self.target_mode:
            self.shop_auto_buy_dict[purchase_item.good.id].amount = amount
        else:
            self.shop_auto_buy_dict[purchase_item.good.id].target_amount = amount
        self.refresh_auto_buy_list()
        self.auto_buy_amount_inputbox.setText("")
        self.auto_buy_amount_inputbox.setDisabled(True)
        self.auto_buy_amount_btn.setDisabled(True)

    # def buy_item_btn_clicked(self):
    #     shop_list = self.shop_list_tab.currentWidget()
    #     selected_items = shop_list.selectedItems()
    #     selected_goods = [
    #         item.data(Qt.ItemDataRole.UserRole) for item in selected_items
    #     ]
    #     if len(selected_goods) == 0:
    #         logging.info("请先选择一个商品")
    #         self.logger.log("请先选择一个商品")
    #         return
    #     result = self.shop.buy_list(selected_goods)
    #     for good_p_id, amount in result:
    #         self.logger.log(
    #             "购买了{}个{}".format(amount, self.lib.get_tool_by_id(good_p_id).name),
    #             True,
    #         )
    #     self.logger.log("购买完成", True)
    #     self.shop.refresh_shop()
    #     self.refresh_shop_list()

    def set_auto_buy_btn_clicked(self):
        shop_list = self.shop_list_tab.currentWidget()
        selected_items = shop_list.selectedItems()
        selected_goods = [
            item.data(Qt.ItemDataRole.UserRole) for item in selected_items
        ]
        if len(selected_goods) == 0:
            self.logger.log("请先选择一个商品", True)
            return
        amount = self.set_auto_buy_amount_inputbox.text()
        amount = int(amount) if amount != "" else 1
        for good in selected_goods:
            if not self.target_mode:
                self.shop_auto_buy_dict[good.id] = PurchaseItem(good, amount=amount)
            else:
                self.shop_auto_buy_dict[good.id] = PurchaseItem(good, target_amount=amount)
        self.refresh_auto_buy_list()

    def refresh_auto_buy_list(self):
        self.auto_buy_list.clear()
        for purchase_item in self.shop_auto_buy_dict.values():
            good = purchase_item.good
            if good.type == "tool":
                tool = self.lib.get_tool_by_id(good.p_id)
                if not self.target_mode:
                    item = QListWidgetItem(f"{tool.name}({purchase_item.amount})")
                else:
                    item = QListWidgetItem(f"{tool.name}({purchase_item.target_amount})")
                item.setData(Qt.ItemDataRole.UserRole, purchase_item)
                self.auto_buy_list.addItem(item)
            elif good.type == "organisms":
                plant = self.lib.get_plant_by_id(good.p_id)
                if not self.target_mode:
                    item = QListWidgetItem(f"{plant.name}({purchase_item.amount})")
                else:
                    item = QListWidgetItem(f"{plant.name}({purchase_item.target_amount})")
                item.setData(Qt.ItemDataRole.UserRole, purchase_item)
                self.auto_buy_list.addItem(item)
            else:
                self.logger.log(f"未知的商店商品类型:{good.type}")
                logging.info(f"未知的商店商品类型:{good.type}")
                raise NotImplementedError(f"未知的商店商品类型:{good.type}")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            selected_items = self.auto_buy_list.selectedItems()
            selected_goods = [
                item.data(Qt.ItemDataRole.UserRole) for item in selected_items
            ]
            if len(selected_goods) == 0:
                self.logger.log("请先选择一个商品", True)
                return
            for purchase_good in selected_goods:
                if purchase_good.good.id in self.shop_auto_buy_dict:
                    self.shop_auto_buy_dict.pop(purchase_good.good.id)
            self.refresh_auto_buy_list()
            self.auto_buy_amount_btn.setDisabled(True)
            self.auto_buy_amount_inputbox.setDisabled(True)
