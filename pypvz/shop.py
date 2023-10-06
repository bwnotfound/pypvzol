from pyamf import remoting, AMF0

from . import Config, WebRequest


class Good:
    def __init__(self, root):
        self.id = int(root['id'])
        self.p_id = int(root['p_id'])
        self.type = root['type']
        self.num = int(root['num'])
        self.price = int(root['price'])
        self.buy_type = int(root['buy_type'])
        self.exchange_tool_id = root['exchange_tool_id']
        self.discount = int(root['discount'])
        self.seq = int(root['seq'])


class Shop:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.wr = WebRequest(cfg)
        self.default_buy_list = [1006, 1018, 1015, 1014, 1013]
        self.gift_shop_goods = {}
        self.normal_shop_goods = {}

    def _refresh_shop(self, shop_type: int):
        body = [float(shop_type)]
        req = remoting.Request(target='api.shop.getMerchandises', body=body)
        ev = remoting.Envelope(AMF0)
        ev['/1'] = req
        bin_msg = remoting.encode(ev, strict=True)
        resp = self.wr.post(
            "http://s{}.youkia.pvz.youkia.com/pvz/amf/", data=bin_msg.getvalue()
        )
        return resp

    def refresh_shop(self):
        resp = self._refresh_shop(2)
        resp_ev = remoting.decode(resp)
        response = resp_ev["/1"]
        if response.status == 0:
            pass
        elif response.status == 1:
            raise NotImplementedError
        else:
            raise NotImplementedError
        goods = response.body
        self.gift_shop_goods = {int(good.id): Good(good) for good in goods}
        
        resp = self._refresh_shop(1)
        resp_ev = remoting.decode(resp)
        response = resp_ev["/1"]
        if response.status == 0:
            pass
        elif response.status == 1:
            raise NotImplementedError
        else:
            raise NotImplementedError
        goods = response.body
        self.normal_shop_goods = {int(good.id): Good(good) for good in goods}

    def buy_default(self):
        self.refresh_shop()
        result_info = []
        for item_id in self.default_buy_list:
            good = self.gift_shop_goods.get(item_id, None)
            if good is None or good.num == 0:
                continue
            self.buy(item_id, max(good.num, good.num))
            result_info.append((good.p_id, good.num))
        return result_info

    def buy(self, item_id: int, amount: int):
        body = [float(item_id), float(amount)]
        req = remoting.Request(target='api.shop.buy', body=body)
        ev = remoting.Envelope(AMF0)
        ev['/1'] = req
        bin_msg = remoting.encode(ev, strict=True)
        resp = self.wr.post(
            "http://s{}.youkia.pvz.youkia.com/pvz/amf/", data=bin_msg.getvalue()
        )
        resp_ev = remoting.decode(resp)
        response = resp_ev["/1"]
        if response.status == 0:
            return {"success": True, "result": response.body.status}
        elif response.status == 1:
            raise NotImplementedError
        else:
            raise NotImplementedError
        
    def buy_list(self, item_list: list, shop_type: int):
        self.refresh_shop()
        result_info = []
        for item_id in item_list:
            if shop_type == 1:
                good = self.normal_shop_goods.get(item_id, None)
            elif shop_type == 2:
                good = self.gift_shop_goods.get(item_id, None)
            if good is None or good.num == 0:
                continue
            self.buy(item_id, good.num)
            result_info.append((good.p_id, good.num))
        return result_info
