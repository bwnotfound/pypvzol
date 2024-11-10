import requests
import concurrent.futures
import base64


class BaseProxyExtractor:
    def __init__(self, name, test_url_list=None):
        if test_url_list is None:
            test_url_list = ["http://pvzol.org/"]
        self.test_url_list = test_url_list
        self.name = name
    
    def test_proxy(self, proxy):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64............WIFI MicroMessenger/7.0.20.1781(0x6700143B) WindowsWechat(0x63090618) XWEB/8259 Flue",
        }
        proxy = {
            "http": proxy,
            "https": proxy,
        }
        headers, proxy = self.handle_param(headers, proxy)
        try:
            resp = requests.get(self.test_url_list[0], headers=headers, proxies=proxy, timeout=2)
            if resp.status_code == 407:
                raise RuntimeError(f"{self.name}代理认证失败")
            if resp.status_code != 200:
                return None
            return proxy
        except Exception as e:
            return None
    
    def test_proxies(self, proxies):
        filterd_proxies = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(self.test_proxy, proxy) for proxy in proxies]
            for future in concurrent.futures.as_completed(futures):
                proxy = future.result()
                if proxy is not None:
                    filterd_proxies.append(proxy)
        return filterd_proxies

    def setup(self, *args):
        raise NotImplementedError

    def handle_param(self, headers, proxies):
        raise NotImplementedError

    def fetch_proxies(self):
        raise NotImplementedError

    def filter_proxies(self, proxies):
        return self.test_proxies(proxies)


class 巨量IPManager(BaseProxyExtractor):
    def __init__(self):
        super().__init__("巨量IP代理")
        self.username = ""
        self.password = ""
        self.api_url = ""

    @property
    def auth_code(self):
        return base64.b64encode(f"{self.username}:{self.password}".encode()).decode()

    def setup(self, *args):
        self.api_url = "http://v2.api.juliangip.com/postpay/getips?city_name=1&ip_remain=1&num=2&pt=1&result_type=json&trade_no=6779103794906538&sign=e83da1cd96170fe4b48f52aa81f3f9dd"
        self.username = "15007115061"
        self.password = "roDeITRM"

    def handle_param(self, headers, proxies):
        headers["Proxy-Authorization"] = f"Basic {self.auth_code}"
        return headers, proxies

    def fetch_proxies(self):
        resp = requests.get(self.api_url)
        if resp.status_code != 200:
            raise Exception(f"请求失败: {resp.status_code}")
        resp_json = resp.json()
        code = resp_json["code"]
        if code != 200:
            raise Exception(f"请求失败: {resp_json.get('msg')}")
        data = resp_json["data"]["proxy_list"]
        proxy_list = []
        for item in data:
            proxy = item.split(",")[0]
            proxy_list.append(proxy)
        proxy_list = self.filter_proxies(proxy_list)
        return proxy_list

if __name__ == "__main__":
    man = 巨量IPManager()
    man.setup()
    print(man.fetch_proxies())
