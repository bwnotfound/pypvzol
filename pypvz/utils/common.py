import math

from ..repository import Plant
from .. import Library, Repository
from ..library import attribute2plant_attribute


def format_number(t):
    if isinstance(t, str):
        t = int(t)
    assert isinstance(t, int)
    if t < 1e4:
        result = str(t)
    elif t < 1e8 and t >= 1e4:
        result = "{:.2f}万".format(t / 1e4)
    elif t >= 1e8 and t < 1e12:
        result = "{:.2f}亿".format(t / 1e8)
    elif t >= 1e12:
        t = t / 1e8
        t_exponent = int(math.log10(t))
        t_mantissa = t / math.pow(10, t_exponent)
        result = "{:.2f}x10^{}亿".format(t_mantissa, t_exponent)
    else:
        raise ValueError('t({}) must be positive'.format(t))
    return result


def second2str(t):
    result = "{}秒".format(t % 60)
    t /= 60
    if t == 0:
        return result
    result = "{}分".format(int(t % 60)) + result
    t /= 60
    if t == 0:
        return result
    result = "{}小时".format(int(t % 24)) + result
    return result


def format_plant_info(
    plant: Plant,
    lib: Library,
    repo: Repository = None,
    grade=True,
    quality=True,
    normal_skill=False,
    spec_skill=False,
    chosen_attribute=None,
    show_normal_attribute=False,
    attribute_list=[],
    need_tab=False,
):
    tab = "    " if need_tab else ""
    sep = "\n{}".format(tab)
    if repo is not None:
        if isinstance(plant, str):
            plant = int(plant)
        if isinstance(plant, int):
            plant = repo.get_plant(plant)
    if plant is None:
        return ""
    assert isinstance(plant, Plant)
    msg = "{}".format(plant.name(lib))
    if grade:
        msg += "({})".format(plant.grade)
    if quality:
        msg += "[{}]".format(plant.quality_str)

    if normal_skill:
        for skill_id in plant.skill_id_list:
            skill = lib.get_skill(skill_id)
            msg += "{}{}({}级)".format(sep, skill["name"], skill["grade"])

    if spec_skill:
        if plant.special_skill_id is not None:
            spec_skill = lib.get_spec_skill(plant.special_skill_id)
            msg += "{}专属:{}({}级)".format(
                (" " if not normal_skill else sep),
                spec_skill["name"],
                spec_skill['grade'],
            )

    if chosen_attribute is not None:
        msg += "-{}:{}".format(
            chosen_attribute.replace("特", ""),
            format_number(
                getattr(
                    plant,
                    attribute2plant_attribute[chosen_attribute],
                )
            ),
        )
    if show_normal_attribute:
        attribute_list = [
            "HP",
            "攻击",
            "命中",
            "闪避",
            "穿透",
            "护甲",
        ]
    for attr_name in attribute_list:
        msg += "\n{}{}:{}".format(
            tab,
            attr_name.replace("特", ""),
            format_number(getattr(plant, attribute2plant_attribute[attr_name])),
        )

    return msg
