from xml.etree.ElementTree import Element, fromstring

from pyamf import remoting, AMF0

from .config import Config
from .web import WebRequest
from .library import Plant, Library


class Plant:
    def __init__(self, root: Element) -> None:
        self.id = int(root.get("id"))
        self.pid = int(root.get("pid"))
        self.attack = root.get("at")
        self.armor = root.get("mi")
        self.speed = root.get("sp")
        self.hp_now = int(root.get("hp"))
        self.hp_max = int(root.get("hm"))
        self.grade = int(root.get("gr"))
        self.growth = root.get("im")
        self.piercing = root.get("pr")
        self.precision = root.get("new_precision")
        self.miss = root.get("new_miss")
        self.quality_str = root.get("qu")
        self.fight = int(root.get("fight"))

        # self.library_plant = lib.get_plant_by_id(self.pid)

    def width(self, lib: Library):
        assert hasattr(self, "_width") or lib is not None
        if hasattr(self, "_width"):
            return self.plant_width
        self.plant_width = lib.get_plant_by_id(self.pid).width
        return self.plant_width

    def name(self, lib: Library):
        assert hasattr(self, "_name") or lib is not None
        if hasattr(self, "_name"):
            return self.plant_name
        self.plant_name = lib.get_plant_by_id(self.pid).name
        return self.plant_name


class Repository:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.wr = WebRequest(cfg)
        self.refresh_repository()

    def refresh_repository(self):
        url = "http://s{}.youkia.pvz.youkia.com/pvz/index.php/Warehouse/index/sig/0"
        resp = self.wr.get(url)
        root = fromstring(resp.decode("utf-8"))
        warehouse = root.find("warehouse")
        tools = warehouse.find("tools")
        organisms = warehouse.find("organisms")
        self.tools = [
            {"id": int(item.get("id")), "amount": int(item.get("amount"))}
            for item in tools
        ]
        self.plants = [Plant(item) for item in organisms if item.tag == 'item']
        self.tools.sort(key=lambda x: x['id'])
        self.plants.sort(key=lambda x: (x.grade, x.fight), reverse=True)
        self.id2plant = {plant.id: plant for plant in self.plants}
        self.id2tool = {tool['id']: tool for tool in self.tools}

    def hp_below(self, high, id_only=False):
        result = []
        if isinstance(high, float):
            for plant in self.plants:
                if plant.hp_now / plant.hp_max <= high:
                    if id_only:
                        result.append(plant.id)
                    else:
                        result.append(plant)
        elif isinstance(high, int):
            for plant in self.plants:
                if plant.hp_now <= high:
                    if id_only:
                        result.append(plant.id)
                    else:
                        result.append(plant)
        else:
            raise TypeError("high must be float or int")
        return result

    def get_plant(self, id):
        if isinstance(id, str):
            id = int(id)
        plant = self.id2plant.get(id, None)
        return plant

    def get_tool(self, id):
        if isinstance(id, str):
            id = int(id)
        tool = self.id2tool.get(id, None)
        return tool

    def _use_tool(self, tool_id, amount):
        body = [float(tool_id), float(amount)]
        req = remoting.Request(target='api.reward.openbox', body=body)
        ev = remoting.Envelope(AMF0)
        ev['/1'] = req
        bin_msg = remoting.encode(ev, strict=True)
        resp = self.wr.post(
            "http://s{}.youkia.pvz.youkia.com/pvz/amf/", data=bin_msg.getvalue()
        )
        resp_ev = remoting.decode(resp)
        response = resp_ev["/1"]
        return response

    def use_item(self, tool_id, amount, lib: Library):
        if isinstance(tool_id, str):
            tool_id = int(tool_id)
        if isinstance(amount, str):
            amount = int(amount)
        response = self._use_tool(tool_id, amount)
        if response.status == 0:
            pass
        elif response.status == 1:
            raise NotImplementedError
        else:
            raise NotImplementedError
        return {
            "success": True,
            "result": "使用了{}个{}".format(amount, lib.get_tool_by_id(tool_id).name),
        }

    def open_box(self, tool_id, amount, lib: Library):
        if isinstance(tool_id, str):
            tool_id = int(tool_id)
        if isinstance(amount, str):
            amount = int(amount)
        amount = max(amount, 10)
        response = self._use_tool(tool_id, amount)
        if response.status == 0:
            pass
        elif response.status == 1:
            raise NotImplementedError
        else:
            raise NotImplementedError
        body = response.body
        open_amount = int(body['openAmount'])
        result = "打开了{}个{}，获得了:".format(open_amount, lib.get_tool_by_id(tool_id).name)
        result = result + ",".join(
            [
                "{}({})".format(reward['amount'], lib.get_tool_by_id(reward['id']).name)
                for reward in body['tools']
            ]
        )
        return {
            "success": True,
            "result": result,
        }
