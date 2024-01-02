import logging

from . import Config, WebRequest


class Good:
    def __init__(self, root, shop_type):
        self.id = int(root['id'])
        self.p_id = int(root['p_id'])
        self.type = root['type']  # tool or organisms
        self.num = int(root['num'])
        self.price = int(root['price'])
        self.shop_type = shop_type

    @property
    def is_plant(self):
        return self.type == 'organisms'


class PurchaseItem:
    def __init__(self, good: Good, amount: int):
        self.good = good
        self.amount = amount


class Shop:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.wr = WebRequest(cfg)
        self.type_list = [1, 2, 5, 3, 6]
        self.shop_name_list = ["普通商店", "礼券商店", "荣誉商店", "金券商城", "VIP商城"]

    def _refresh_shop(self, shop_type: int):
        body = [float(shop_type)]
        resp = self.wr.amf_post_retry(
            body, "api.shop.getMerchandises", "/pvz/amf/", "获取商店信息", except_retry=True
        )
        return resp

    def refresh_shop(self):
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for t in self.type_list:
                futures.append(executor.submit(self._refresh_shop, t))
        concurrent.futures.wait(futures, return_when=concurrent.futures.ALL_COMPLETED)

        self.good_id2good: dict[int, Good] = {}
        self.shop_goods_list = []
        self.tool_id2good: dict[int, Good] = {}
        for shop_type, future in zip(self.type_list, futures):
            try:
                response = future.result()
            except Exception as e:
                logging.error(e)
                continue
            if response.status == 0:
                pass
            else:
                logging.error("获取商店信息失败")
                raise NotImplementedError
            goods = response.body
            self.shop_goods_list.append([Good(good, shop_type) for good in goods])
            self.good_id2good.update(
                {int(good.id): Good(good, shop_type) for good in goods}
            )
            self.tool_id2good.update(
                {
                    int(good.p_id): Good(good, shop_type)
                    for good in goods
                    if good['type'] == 'tool'
                }
            )

    def buy(self, item_id: int, amount: int):
        body = [float(item_id), float(amount)]
        response = self.wr.amf_post_retry(body, "api.shop.buy", "/pvz/amf/", "购买物品")
        if response.status == 0:
            if response.body['status'] == 'success':
                return {
                    "success": True,
                    "amount": int(response.body['tool']['amount']),
                    "tool_id": int(response.body['tool']['id']),
                }
            return {"success": False, "result": response.body['status']}
        else:
            return {"success": False, "result": response.body.description}
