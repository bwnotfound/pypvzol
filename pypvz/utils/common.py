import math


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
