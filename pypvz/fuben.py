from .web import WebRequest
from .config import Config


class FubenCave:
    def __init__(self, root):
        self.name = root['name']
        self.cave_id = int(root['cave_id'])
        self.rest_count = int(root['lcc'])


class FubenRequest:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.wr = WebRequest(cfg)

    def get_caves(self, layer):
        body = [float(layer)]
        response = self.wr.amf_post("api.fuben.display", body)
        if response.status != 0:
            return {
                "success": False,
                "message": response.body.description,
            }
        caves = [FubenCave(root) for root in response.body['_caves']]
        return caves
