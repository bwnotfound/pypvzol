from os import path
import os
from typing import Literal
from xml.etree.ElementTree import fromstring
import pickle

from ..config import Config
from ..web import WebRequest
from ..library import EvolutionLibPath, Library, Plant
from ..repository import Repository


class EvolutionPathItem:
    def __init__(self, start_pid, lib: Library):
        self.lib = lib
        self.start_plant = self.lib.get_plant_by_id(start_pid)
        self.next_plant = None

    def link(self, choice: Literal[1, 2]):
        assert choice in [1, 2]
        next_plant_path = self.start_plant.evolution_path.evolutions[choice - 1]
        try:
            next_plant = self.lib.get_plant_by_id(next_plant_path["target_id"])
        except Exception:
            return {
                "success": False,
                "result": "加入进化路线失败，没有这样的路线： {}->{}".format(
                    self.start_plant.name, next_plant.name
                ),
            }
        self.next_plant = next_plant
        self.evolution_path = next_plant_path
        self.choice = choice
        return {
            "success": True,
            "result": "加入进化路线成功： {}->{}".format(self.start_plant.name, next_plant.name),
            "target_pid": self.evolution_path["target_id"],
        }


class PlantEvolution:
    def __init__(self, cfg: Config, repo: Repository, lib: Library):
        self.cfg = cfg
        self.repo = repo
        self.lib = lib
        self.wr = WebRequest(cfg)

        self.saved_evolution_paths: list[list[EvolutionPathItem]] = []

    def evolution(self, id, pathItem: EvolutionPathItem):
        url = (
            "http://s{}.youkia.pvz.youkia.com/pvz/index.php/organism/evolution/id/"
            + f"{id}/route/{pathItem.evolution_path['id']}/shortcut/2/sig/0"
        )  # TODO: 这里的2不知道是什么意思
        xml_text = self.wr.get(url).decode("utf-8")
        root = fromstring(xml_text)
        if not root.find("response").find("status").text == "success":
            return {
                "success": False,
                "result": "Evolution failed. Error information: " + xml_text,
            }
        return {
            "success": True,
            "result": "进化成功。{}->{}".format(
                pathItem.start_plant.name,
                pathItem.next_plant.name,
            ),
        }

    def create_new_path(self, start_pid):
        self.saved_evolution_paths.append([EvolutionPathItem(start_pid, self.lib)])

    def remove_path(self, index):
        self.saved_evolution_paths.pop(index)

    def add_evolution(self, index, choice: Literal[1, 2]):
        assert (
            choice in [1, 2]
            and isinstance(index, int)
            and index < len(self.saved_evolution_paths)
            and index >= 0
        )
        saved_path = self.saved_evolution_paths[index]
        assert len(saved_path) > 0
        result = saved_path[-1].link(choice)
        if not result["success"]:
            result["result"] = (
                f"向第{index+1}条路线加入进化元素时失败。原因：" + result["result"]
            )  # 理论上不会用到，因为检查了是否从上一个节点出发
            return result
        target_pid = result["target_pid"]
        saved_path.append(EvolutionPathItem(target_pid, self.lib))
        return result

    def remove_evolution(self, index, pid):
        assert (
            isinstance(index, int)
            and index < len(self.saved_evolution_paths)
            and index >= 0
        )
        saved_path = self.saved_evolution_paths[index]
        assert len(saved_path) > 0
        if len(saved_path) == 1:
            self.remove_path(index)
        for i, evolution_path_item in enumerate(saved_path):
            if evolution_path_item.start_plant.id == pid:
                self.saved_evolution_paths[index] = saved_path[:i]
                break
        else:
            return {
                "success": False,
                "result": f"在第{index+1}条路线中没有找到{pid}这个植物",
            }
        if i == 0:
            self.remove_path(index)
        return {
            "success": True,
            "result": "删除了",
        }

    def evolution_info(self, pid):
        pass

    def plant_evolution_all(self, path_index, id):
        assert (
            path_index < len(self.saved_evolution_paths)
            and path_index >= 0
            and isinstance(id, int)
            and isinstance(path_index, int)
        )
        plant = self.repo.get_plant(id)
        saved_path = self.saved_evolution_paths[path_index]
        assert len(saved_path) > 0
        for i, path in enumerate(saved_path):
            if path.start_plant.id == plant.pid:
                break
        else:
            return {
                "success": False,
                "result": f"在第{path_index+1}条路线中没有找到植物：{plant.name(self.lib)}",
            }
        for j in range(i, len(saved_path) - 1):
            result = self.evolution(id, saved_path[j])
            if not result["success"]:
                return result
        return {
            "success": True,
            "result": f"在第{path_index+1}条路线中成功将{plant.name(self.lib)}进化为{saved_path[-1].start_plant.name}",
        }
    
    def load(self, save_dir):
        save_path = os.path.join(save_dir, "evolution")
        if not path.exists(save_path):
            return
        with open(save_path, "rb") as f:
            self.saved_evolution_paths = pickle.load(f)
        for saved_path in self.saved_evolution_paths:
            for item in saved_path:
                item.lib = self.lib
    
    def save(self, save_dir):
        save_path = os.path.join(save_dir, "evolution")
        with open(save_path, "wb") as f:
            f.write(pickle.dumps(self.saved_evolution_paths))