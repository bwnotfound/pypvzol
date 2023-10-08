from pyamf import AMF0, remoting

from . import Config, WebRequest


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

    def upgrade_quality(self, plant_id):
        body = [float(plant_id)]
        req = remoting.Request(target='api.apiorganism.qualityUp', body=body)
        ev = remoting.Envelope(AMF0)
        ev['/1'] = req
        bin_msg = remoting.encode(ev, strict=True)
        resp = self.wr.post(
            "http://s{}.youkia.pvz.youkia.com/pvz/amf/", data=bin_msg.getvalue()
        )
        result = {
            "success": False,
            "result": "解析升品结果失败，不过一般是成功的",
        }
        try:
            resp_ev = remoting.decode(resp)
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