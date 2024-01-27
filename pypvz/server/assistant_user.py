from queue import Queue

import pickle


class AssistantAccount:
    def __init__(self, id, data: bytes):
        self.id = id
        self.data = data
        self.usersettings_stop_channel = Queue()

    def compare_cookie(self, user1, user2):
        user1 = pickle.loads(user1)
        user2 = pickle.loads(user2)
        return user1['config']['cookie'] == user2['config']['cookie']
