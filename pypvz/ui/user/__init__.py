import os
import pickle


def load_data(load_dir, load_name, instance=None):
    data = {}
    if isinstance(load_dir, str):
        load_path = os.path.join(load_dir, load_name)
        if os.path.exists(load_path):
            with open(load_path, "rb") as f:
                data = pickle.load(f)
        else:
            data = {}
    else:
        assert isinstance(load_dir, dict)
        data = load_dir
    if instance is not None:
        for k, v in data.items():
            if hasattr(instance, k):
                setattr(instance, k, v)
    return data


def save_data(data, save_dir, save_name):
    if save_dir is not None:
        save_path = os.path.join(save_dir, save_name)
        with open(save_path, "wb") as f:
            pickle.dump(data, f)
    return data


from .auto_challenge import SingleCave
from .auto_pipeline import PipelineMan, PipelineScheme, Pipeline
from .usersettings import UserSettings
