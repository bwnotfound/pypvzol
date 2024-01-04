from xml.etree.ElementTree import Element, fromstring
import json

from .web import WebRequest
from .config import Config


attribute_list = ["HP特", "攻击特", "命中", "闪避", "穿透", "护甲", "HP", "攻击"]
attribute2plant_attribute = {
    "HP": "hp_max",
    "攻击": "attack",
    "命中": "precision",
    "闪避": "miss",
    "穿透": "piercing",
    "护甲": "armor",
    "HP特": "hp_max",
    "攻击特": "attack",
    "战力": "fight",
}


class Tool:
    def __init__(self, root: Element):
        self.id = int(root.get("id"))
        self.name = root.get("name")
        self.type = int(root.get("type"))
        self.type_name = root.get("type_name")
        self.sell_price = root.get("sell_price")
        self.use_result = root.get("use_result")
        self.describe = root.get("describe")
        self.rare = root.get("rare")
        self.lottery_name = root.get("lottery_name")


class Library:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.wr = WebRequest(cfg)
        self.refresh_library()

    def refresh_library(self):
        results = self.wr.get_async_gather(
            self.wr.get_async("/pvz/php_xml/tool.xml", "获取道具图鉴", except_retry=True),
            self.wr.get_async("/pvz/php_xml/organism.xml", "获取植物图鉴", except_retry=True),
        )
        resp = results[0]
        tools = fromstring(resp.decode("utf-8")).find("tools")
        self.tools = [Tool(item) for item in tools]

        resp = results[1]
        plants = fromstring(resp.decode("utf-8")).find("organisms")
        self.plants = [Plant(item) for item in plants]

        self.tools = {tool.id: tool for tool in self.tools}
        self.plants = {plant.id: plant for plant in self.plants}

        self.name2tool = {tool.name: tool for tool in self.tools.values()}

        with open("./data/cache/pvz/skills.json", "r", encoding="utf-8") as f:
            self.skills = json.load(f)
        with open("./data/cache/pvz/spec_skills.json", "r", encoding="utf-8") as f:
            self.spec_skills = json.load(f)

    def get_plant_by_id(self, pid):
        if isinstance(pid, str):
            pid = int(pid)
        result = self.plants.get(pid, None)
        return result

    def get_tool_by_id(self, id):
        if isinstance(id, str):
            id = int(id)
        result = self.tools.get(id, None)
        return result

    def get_skill(self, skill_id: int):
        for item in self.skills:
            if int(item['id']) == skill_id:
                return item
        return None

    def get_spec_skill(self, skill_id: int):
        for item in self.spec_skills:
            if int(item['id']) == skill_id:
                return item
        return None


class EvolutionLibPath:
    def __init__(self, root: Element):
        self.src_pid = int(root.get("id"))
        self.evolutions = []
        for item in root.find("evolutions"):
            self.evolutions.append(
                {
                    "id": int(item.get("id")),  # evolution_path uid
                    "grade": int(item.get("grade")),
                    "target_id": int(item.get("target")),  # target_plant_pid
                    "tool_id": int(item.get("tool_id")),
                    "money": item.get("money"),
                }
            )


class Plant:
    def __init__(self, root: Element):
        self.id = int(root.get("id"))
        self.area = int(root.get("width"))
        self.name = root.get("name")
        self.attribute = root.get("attribute")
        self.explanation = root.get("expl")
        self.img_id = root.get("img_id")
        self.width = int(root.get("width"))
        self.use_condition = root.get("use_condition")
        self.evolution_path = EvolutionLibPath(root)
