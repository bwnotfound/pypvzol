# import sys

# from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget
# from PyQt5.QtCore import QUrl, QThread, pyqtSignal, QTimer
# from PyQt5.QtNetwork import QNetworkCookie
# from PyQt5.QtWebEngineWidgets import (
#     QWebEngineView,
#     QWebEngineSettings,
#     QWebEnginePage,
# )
# from PyQt5.QtWebEngineCore import QWebEngineHttpRequest


# class GameWindow(QMainWindow):
#     def __init__(self, cookie_str, scale_rate=1.5, parent=None):
#         super().__init__(parent=parent)
#         self.cookie_str = cookie_str
#         self.scale_rate = scale_rate
#         self.init_ui()

#     def init_ui(self):
#         self.move(100, 100)

#         # 创建WebEngineView
#         self.web_view = QWebEngineView(self)

#         # 设置WebEngineSettings以启用ActiveX组件
#         settings = self.web_view.settings()
#         settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)

#         # 设置cookie
#         cookie = QNetworkCookie(
#             self.cookie_str.split("=")[0].encode("utf-8"),
#             self.cookie_str.split("=")[1].encode("utf-8"),
#         )
#         print(cookie.value().data().decode("utf-8"))
#         urlOrigin = QUrl("http://pvzol.org/")
#         self.web_view.page().profile().cookieStore().setCookie(cookie, origin=urlOrigin)
#         req = QWebEngineHttpRequest(QUrl("http://pvzol.org/pvz/index.php/default/main"))
#         self.web_view.load(req)
#         # 修改页面元素
#         self.web_view.page().loadFinished.connect(self.on_load_finished)

#     def on_load_finished(self, m=None):
#         print("load finished")
#         self.web_view.page().runJavaScript(
#             f"""
#             let emb = document.getElementsByTagName('embed');
#             emb[0].width = emb[0].width * {self.scale_rate};
#             emb[0].height = emb[0].height * {self.scale_rate};
#             """,
#             lambda x: None,
#         )
#         self.web_view.setMinimumSize(
#             int(self.web_view.page().contentsSize().width() * self.scale_rate),
#             int(self.web_view.page().contentsSize().height() * self.scale_rate),
#         )
#         self.resize(
#             int(self.web_view.page().contentsSize().width() * self.scale_rate),
#             int(self.web_view.page().contentsSize().height() * self.scale_rate),
#         )


# class _CreateGameWindow(QWidget):
#     create_signal = pyqtSignal(str, float)

#     def __init__(self):
#         super().__init__()
#         self.create_signal.connect(self.create_window)
#         self.window_list = []
#         self.timer = QTimer(self)
#         self.timer.timeout.connect(self.update_frame)
#         self.timer.start(5)

#     def update_frame(self):
#         QApplication.processEvents()

#     def create_window(self, cookie, scale_rate):
#         window = GameWindow(cookie, scale_rate=scale_rate)
#         window.show()
#         self.window_list.append(window)
#         self.window_list = [w for w in self.window_list if w.isVisible()]


# class _CreateGameWindowThread(QThread):
#     def __init__(self, queue, signal):
#         super().__init__()
#         self.queue = queue
#         self.signal = signal

#     def run(self):
#         while True:
#             try:
#                 data = self.queue.get()
#                 if data is None:
#                     break
#                 cookie, scale_rate = data
#                 print("接收到: {}\n{}".format(cookie, scale_rate))
#                 self.signal.emit(cookie, scale_rate)
#             except Exception:
#                 break
#         print("over")


# def run_game_window(queue):
#     app = QApplication(sys.argv)
#     cg = _CreateGameWindow()
#     t = _CreateGameWindowThread(queue, cg.create_signal)
#     t.start()
#     while True:
#         app_return = app.exec()
#     # sys.exit(app_return)
