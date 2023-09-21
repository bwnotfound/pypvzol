from xml.etree.ElementTree import Element, fromstring
from queue import Queue
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
        self.tools = [{"id": int(item.get("id")), "amount": int(item.get("amount"))} for item in tools]
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
        plant = self.id2plant.get(id, None)
        return plant
    
    def get_tool(self, id):
        tool = self.id2tool.get(id, None)
        return tool
