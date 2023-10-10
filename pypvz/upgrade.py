import logging
from pyamf import AMF0, remoting, DecodeError

from . import Config, WebRequest, Library


class UpgradeMan:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.wr = WebRequest(cfg)
        self.quality_name = [
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
        ]

    def upgrade_quality(self, plant_id, retry=True):
        body = [float(plant_id)]
        req = remoting.Request(target='api.apiorganism.qualityUp', body=body)
        ev = remoting.Envelope(AMF0)
        ev['/1'] = req
        bin_msg = remoting.encode(ev, strict=True)
        
        result = {
            "success": False,
            "result": "解析升品结果失败，不过一般是成功的",
        }
        try:
            while True:
                resp = self.wr.post(
                    "http://s{}.youkia.pvz.youkia.com/pvz/amf/", data=bin_msg.getvalue()
                )
                try:
                    resp_ev = remoting.decode(resp)
                    break
                except DecodeError:
                    if not retry:
                        break
                logging.info("重新尝试请求升级品质")
            response = resp_ev["/1"]
            if response.status != 0:
                if response.body.description == "Error:t0004":
                    result["success"] = True
                    result["result"] = "升品失败，大概率是已经升到魔神了"
                    result["quality_name"] = "魔神"
                else:
                    result["success"] = True
                    result["result"] = "升品失败，未知错误，当做升级为魔神了。如有需要请重新尝试"
                    result["quality_name"] = "魔神"
            else:
                try:
                    result['success'] = True
                    quality_name = response.body['quality_name']
                    result['result'] = "升品成功，当前品质为{}".format(quality_name)
                    result['quality_name'] = quality_name
                except:
                    pass
        except:
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
        body = [float(id1), float(id2), float(attribute_book_id), float(reinforce_number)]
        req = remoting.Request(target='api.tool.synthesis', body=body)
        ev = remoting.Envelope(AMF0)
        ev['/1'] = req
        bin_msg = remoting.encode(ev, strict=True)
        resp = self.wr.post(
            "http://s{}.youkia.pvz.youkia.com/pvz/amf/", data=bin_msg.getvalue()
        )
        try:
            resp_ev = remoting.decode(resp)
        except Exception as e:
            raise RuntimeError(str(e))
        return resp_ev["/1"]