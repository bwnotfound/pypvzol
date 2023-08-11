from xml.etree.ElementTree import Element, fromstring
import bisect

from .web import WebRequest
from .config import Config


class Library:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.wr = WebRequest(cfg)
        self.refresh_library()

    def refresh_library(self):
        results, exceptions = self.wr.get_async_gather(
            [
                ["http://s{}.youkia.pvz.youkia.com/pvz/php_xml/tool.xml"],
                ["http://s{}.youkia.pvz.youkia.com/pvz/php_xml/organism.xml"],
            ]
        )
        tem_list = []
        for e in exceptions:
            if isinstance(e, Exception):
                tem_list.append(e)
        if len(tem_list) > 0:
            raise Exception(tem_list)
        resp = results[0]
        tools = fromstring(resp.decode("utf-8")).find("tools")
        self.tools = [Tool(item) for item in tools]

        resp = results[1]
        plants = fromstring(resp.decode("utf-8")).find("organisms")
        self.plants = [Plant(item) for item in plants]

        self.tools.sort(key=lambda x: x.id)
        self.plants.sort(key=lambda x: x.id)

    def get_plant_by_id(self, pid):
        index = bisect.bisect_left(self.plants, pid, key=lambda x: x.id)
        result = self.plants[index]
        assert result.id == pid
        return result

    def get_tool_by_id(self, id):
        index = bisect.bisect_left(self.tools, id, key=lambda x: x.id)
        result = self.tools[index]
        assert result.id == id
        return result

    def get_evolutions(self, id):
        src_plant = self.get_plant_by_id(id)
        return src_plant.evolutions


class Tool:
    def __init__(self, root: Element):
        self.id = int(root.get("id"))
        self.name = root.get("name")
        self.type_name = root.get("type_name")
        self.sell_price = root.get("sell_price")
        self.use_result = root.get("use_result")
        self.describe = root.get("describe")
        self.rare = root.get("rare")


class Plant:
    def __init__(self, root: Element):
        self.id = int(root.get("id"))
        self.area = int(root.get("width"))
        self.name = root.get("name")
        self.attribute = root.get("attribute")
        self.explanation = root.get("expl")
        self.img_id = root.get("img_id")
        self.width = int(root.get("width"))
        self.evolutions = []
        for item in root.find("evolutions"):
            self.evolutions.append(
                {
                    "id": int(item.get("id")),
                    "grade": int(item.get("grade")),
                    "target_id": int(item.get("target")),
                    "tool_id": int(item.get("tool_id")),
                    "money": item.get("money"),
                }
            )
