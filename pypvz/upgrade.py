from pyamf import AMF0, remoting
import os
import pickle

from . import Config, WebRequest, Library

quality_name_list = [
    "劣质",
    "普通",
    "优秀",
    "精良",
    "极品",
    "史诗",
    "传说",
    "神器",
    "魔王",
    "战神",
    "至尊",
    "魔神",
    "耀世",
    "不朽",
    "永恒",
    "太上",
    "混沌",
    "无极",
]


class UpgradeMan:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.wr = WebRequest(cfg)
        self.quality_name = quality_name_list

    def upgrade_quality(self, plant_id):
        body = [float(plant_id)]
        response = self.wr.amf_post(
            body, 'api.apiorganism.qualityUp', "/pvz/amf/", "升级品质"
        )
        result = {
            "success": False,
        }
        if response.status != 0:
            reason = response.body.description
            if response.body.description == "Error:t0004":  # 达到(可能是魔神)上限
                reason = "升品失败。错误原因：植物品质达到上限"
                result["error_type"] = 1
            elif response.body.description == "该生物不存在":
                reason = "升品失败。错误原因：该植物不存在"
                result["error_type"] = 2
            elif response.body.description == "道具异常":  # 没有刷新书了
                reason = "升品失败。错误原因：品质刷新书不足"
                result["error_type"] = 3
            elif "频繁" in response.body.description:
                result["error_type"] = 6
            else:
                reason = f"升品失败。错误原因：{response.body.description}"
                result["error_type"] = 4
            result["result"] = reason
        else:
            try:
                result['success'] = True
                quality_name = response.body['quality_name']
                result['result'] = "升品成功。当前品质为{}".format(quality_name)
                result['quality_name'] = quality_name
            except:
                result["error_type"] = 5
                result['result'] = "解析升品结果失败"
                pass
        return result


class SynthesisMan:
    def __init__(self, cfg: Config, lib: Library):
        self.lib = lib
        self.cfg = cfg
        self.wr = WebRequest(cfg)

    def synthesis(self, id1, id2, attribute_book_id, reinforce_number):
        '''
        api.tool.synthesis
            request:
                主id,副id,item_id,卷轴数
            response:
            (以下都是增加的值)
                speed:
                hp:
                attack:
                precision:
                miss:
            (fight是合成后的值)
                fight:
        '''
        body = [
            float(id1),
            float(id2),
            float(attribute_book_id),
            float(reinforce_number),
        ]
        req = remoting.Request(target='api.tool.synthesis', body=body)
        ev = remoting.Envelope(AMF0)
        ev['/1'] = req
        bin_msg = remoting.encode(ev, strict=True)
        resp = self.wr.post("/pvz/amf/", data=bin_msg.getvalue())
        try:
            resp_ev = remoting.decode(resp)
        except Exception as e:
            raise RuntimeError(str(e))
        return resp_ev["/1"]


class HeritageMan:
    def __init__(self, cfg: Config, lib: Library):
        self.lib = lib
        self.cfg = cfg
        self.wr = WebRequest(cfg)
        self.heritage_book_dict = {
            "HP": lib.name2tool["HP传承书"].id,
            "攻击": lib.name2tool["攻击传承书"].id,
            "命中": lib.name2tool["命中传承书"].id,
            "闪避": lib.name2tool["闪避传承书"].id,
            "护甲": lib.name2tool["护甲传承书"].id,
            "穿透": lib.name2tool["穿透传承书"].id,
            "速度": lib.name2tool["速度传承书"].id,
        }
        self.heritage_attribute_dict = {
            "HP": "hp_max",
            "攻击": "attack",
            "命中": "precision",
            "闪避": "miss",
            "护甲": "armor",
            "穿透": "piercing",
            "速度": "speed",
        }
        self.id1, self.id2 = None, None
        self.book_choice_index, self.reinforce_number_index = None, None

    def exchange_one(self, id1, id2, heritage_item_id, heritage_reinforce_number):
        '''
        api.tool.synthesis
            request:
                主id,副id,item_id,卷轴数
            response:
            (以下都是增加的值)
                speed:
                hp:
                attack:
                precision:
                miss:
            (fight是合成后的值)
                fight:
        '''
        body = [
            float(id2),
            float(id1),
            float(heritage_item_id),
            float(heritage_reinforce_number),
        ]
        response = self.wr.amf_post(
            body, 'api.apiorganism.exchangeOne', "/pvz/amf/", "传承单项属性"
        )
        if response.status != 0:
            return {
                "success": False,
                "result": response.body.description,
            }
        else:
            return {
                "success": True,
                "result": "单项属性传承成功",
            }

    def exchange_all(self, id1, id2):
        '''
        api.tool.synthesis
            request:
                主id,副id,item_id,卷轴数
            response:
            (以下都是增加的值)
                speed:
                hp:
                attack:
                precision:
                miss:
            (fight是合成后的值)
                fight:
        '''
        body = [float(id2), float(id1)]
        response = self.wr.amf_post(
            body, 'api.apiorganism.exchangeAll', "/pvz/amf/", "传承全属性"
        )
        if response.status != 0:
            return {
                "success": False,
                "result": response.body.description,
            }
        else:
            return {
                "success": True,
                "result": "全属性传承成功",
            }
            
    def save(self, save_dir):
        save_path = os.path.join(save_dir, "user_heritageman")
        with open(save_path, "wb") as f:
            pickle.dump(
                {
                    "id1": self.id1,
                    "id2": self.id2,
                    "book_choice_index": self.book_choice_index,
                    "reinforce_number_index": self.reinforce_number_index,
                },
                f,
            )

    def load(self, load_dir):
        load_path = os.path.join(load_dir, "user_heritageman")
        if os.path.exists(load_path):
            with open(load_path, "rb") as f:
                d = pickle.load(f)
            for k, v in d.items():
                if hasattr(self, k):
                    setattr(self, k, v)
