from xml.etree.ElementTree import Element, fromstring
import logging
import time
from threading import Lock

from .config import Config
from .web import WebRequest
from .library import Plant, Library
from .upgrade import quality_name_list
from .utils.common import format_number


class Plant:
    def __init__(self, root: Element) -> None:
        self.id = int(root.get("id"))
        self.pid = int(root.get("pid"))
        self.attack = int(root.get("at"))
        self.armor = int(root.get("mi"))
        self.speed = int(root.get("sp"))
        self.hp_now = int(root.get("hp"))
        self.hp_max = int(root.get("hm"))
        self.grade = int(root.get("gr"))
        self.growth = root.get("im")
        self.piercing = int(root.get("pr"))
        self.precision = int(root.get("new_precision"))
        self.miss = int(root.get("new_miss"))
        self.quality_str = root.get("qu")
        self.fight = int(root.get("fight"))
        try:
            self.quality_index = quality_name_list.index(self.quality_str)
        except:
            self.quality_index = -1
            logging.warning(f"未知的品质{self.quality_str}")
        self.skills = []
        for item in root.find("sk").findall("item"):
            self.skills.append(
                {
                    "id": int(item.get("id")),
                    "name": item.get("na"),
                }
            )
        self.special_skill = None
        item = root.find("ssk").find("item")
        if item is not None:
            self.special_skill = {
                "id": int(item.get("id")),
                "name": item.get("name"),
            }

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

    def info(self, lib: Library = None, quality=True):
        if lib is None:
            raise ValueError("lib can't be None")
        result = "{}({})".format(self.name(lib), self.grade)
        if quality:
            result += "[{}]".format(self.quality_str)
        return result


class Repository:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.wr = WebRequest(cfg)
        self._lock = Lock()
        self.refresh_repository()
        
    def refresh_repository(self, logger=None):
        try:
            self._lock.acquire()
            self._refresh_repository(logger=logger)
        finally:
            self._lock.release()
    
    def _refresh_repository(self, logger=None):
        url = "/pvz/index.php/Warehouse/index/sig/0"
        cnt, max_retry = 0, 20
        while cnt < max_retry:
            cnt += 1
            try:
                resp = self.wr.get(url)
                resp_text = resp.decode("utf-8")
                if "服务器更新" in resp_text:
                    logging.info("服务器更新，选择等待5秒后重试。最多再等待{}次".format(max_retry - cnt))
                    time.sleep(5)
                    continue
                elif "请求过于频繁" in resp_text:
                    logging.info("请求过于频繁，选择等待3秒后重试。最多再等待{}次".format(max_retry - cnt))
                    time.sleep(3)
                    continue
                try:
                    root = fromstring(resp_text)
                    break
                except:
                    if resp_text.startswith("<html"):
                        logging.info(f"{resp_text}\n刷新仓库出现问题。大概率是Cookie或者区服选择有误。上面是响应")
                        raise RuntimeError("刷新仓库出现问题")
                    msg = "刷新仓库失败，选择等待3秒后重试。最多再等待{}次".format(max_retry - cnt)
                    if logger is not None:
                        logger.log(msg)
                    else:
                        logging.info(msg)
                    time.sleep(3)
            except RuntimeError as e:
                raise e
            except Exception as e:
                msg = "刷新仓库出现异常，异常类型：{}。选择等待3秒后重试。最多再等待{}次".format(
                    type(e).__name__, max_retry - cnt
                )
                if logger is not None:
                    logger.log(msg)
                else:
                    logging.info(msg)
                time.sleep(3)
        warehouse = root.find("warehouse")
        tools = warehouse.find("tools")
        organisms = warehouse.find("organisms")
        self.tools = [
            {"id": int(item.get("id")), "amount": int(item.get("amount"))}
            for item in tools
        ]
        self.plants = [Plant(item) for item in organisms if item.tag == 'item']
        self.tools.sort(key=lambda x: x['id'])
        self.plants.sort(key=lambda x: (-x.grade, x.pid, -x.quality_index, -x.fight))
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
    
    def remove_plant(self, id):
        if isinstance(id, str):
            id = int(id)
        plant = self.id2plant.get(id, None)
        if plant is None:
            return False
        self.plants.remove(plant)
        self.id2plant.pop(id)
        return True

    def remove_tool(self, id):
        if isinstance(id, str):
            id = int(id)
        tool = self.id2tool.get(id, None)
        if tool is None:
            return False
        self.tools.remove(tool)
        self.id2tool.pop(id)
        return True

    def use_item(self, tool_id, amount, lib: Library):
        body = [float(tool_id), float(amount)]
        response = self.wr.amf_post(body, "api.tool.useOf", "/pvz/amf/", "使用物品")
        if response.status == 0:
            return {
                "success": True,
                "result": "使用了{}个{}".format(amount, lib.get_tool_by_id(tool_id).name),
            }
        elif response.status == 1:
            return {
                "success": False,
                "result": response.body.description,
            }
        else:
            raise NotImplementedError

    def sell_item(self, tool_id, amount, lib: Library):
        body = [float(1), float(tool_id), float(amount)]
        response = self.wr.amf_post(body, "api.shop.sell", "/pvz/amf/", "出售物品")
        if response.status == 0:
            return {
                "success": True,
                "result": "出售了{}个{}，获得{}金币".format(
                    amount,
                    lib.get_tool_by_id(tool_id).name,
                    format_number(response.body),
                ),
            }
        elif response.status == 1:
            return {
                "success": False,
                "result": response.body.description,
            }
        else:
            raise NotImplementedError

    def sell_plant(self, plant_id, plant_info):
        body = [float(2), float(plant_id), float(1)]
        response = self.wr.amf_post(body, "api.shop.sell", "/pvz/amf/", "出售植物")
        if response.status == 0:
            return {
                "success": True,
                "result": "出售了{}，获得{}金币".format(plant_info, response.body),
            }
        elif response.status == 1:
            return {
                "success": False,
                "result": "出售植物{}时出现异常。原因：{}".format(
                    plant_info,
                    response.body.description,
                ),
            }
        else:
            raise NotImplementedError

    def open_box(self, tool_id, amount, lib: Library):
        # 单次请求最大为99999
        if isinstance(amount, str):
            amount = int(amount)
        amount = min(amount, 99999)
        body = [float(tool_id), float(amount)]
        response = self.wr.amf_post(body, "api.reward.openbox", "/pvz/amf/", "打开宝箱")
        if response.status == 1:
            description = response.body.description
            if "道具异常" in description:
                return {
                    "success": False,
                    "result": "所打开物品不存在",
                }
            return {
                "success": False,
                "result": description,
            }
        open_amount = int(response.body['openAmount'])
        result = "打开了{}个{}，获得了: ".format(open_amount, lib.get_tool_by_id(tool_id).name)
        reward_str_list = []
        for reward in response.body['tools']:
            tool = lib.get_tool_by_id(reward['id'])
            if tool is None:
                logging.warning("未知的奖励物品id:{}".format(reward['id']))
                continue
            reward_str_list.append("{}({})".format(tool.name, reward['amount']))
        result = result + ",".join(reward_str_list)
        return {
            "success": True,
            "result": result,
            "open_amount": open_amount,
        }
