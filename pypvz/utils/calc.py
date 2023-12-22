import math

'''
    感谢伟大的舍友，为小数点后第10位的精度计算做出了卓越的贡献。
    
    tem = (-3 * p**2 + 4 * p) ** 0.5
    k = i - 1
    pp = 1 - p / tem * (
        (p / 2 + tem / 2) ** k
        - (p / 2 - tem / 2) ** k
        + (1 - p) * (p / 2 + tem / 2) ** (k - 1)
        - (1 - p) * (p / 2 - tem / 2) ** (k - 1)
    )
    pp代表第k+1回合及之前出现金龙攻击的概率
    
    tem = (-3 * p**2 + 4 * p) ** 0.5
    m = p / 2 + tem / 2
    n = p / 2 - tem / 2
    result = (2 * p - p**2) / tem * (m / (1 - m) - n / (1 - n)) + 1
    result就是期望回合数
'''


def simulate_imprisonment(book_num, riguang_level):
    r'''
    n: 满级禁锢数量
    riguang_level: 10个炮灰的日光等级
    '''
    plant_riguang_possible = 0.03 * riguang_level
    no_hit_round_count_list = [1]

    for n in range(1, book_num + 1):
        p = 1 - (1 - 0.25) ** n
        # a1, a0, a_1 = 0, 1, 0
        # result = 0

        # for i in range(2, 10000):
        #     a1, a0 = (a0 + a1) * p, a1 * (1 - p)
        #     a_1_last = 1 - a0 - a1
        #     result += (a_1_last - a_1) * (i - 1)
        #     a_1 = a_1_last
    
        tem = (-3 * p**2 + 4 * p) ** 0.5
        m = p / 2 + tem / 2
        n = p / 2 - tem / 2
        result = (2 * p - p**2) / tem * (m / (1 - m) - n / (1 - n)) + 1
        
        no_hit_round_count_list.append(result)
    loss_round_count_list = [None for _ in range(book_num + 1)]
    hit_num_possible_list = [0 for _ in range(6)]

    def calc_riguang_possible(num, n):  # num <= n
        # C(num, n)*(1 - plant_riguang_possible)^num*plant_riguang_possible^(1-num)

        return (
            math.factorial(n)
            / math.factorial(num)
            / math.factorial(n - num)
            * (1 - plant_riguang_possible) ** (n - num)
            * plant_riguang_possible**num
        )

    for i in range(1, 6):
        for j in range(0, i + 1):
            hit_num_possible_list[i - j] += 0.2 * calc_riguang_possible(j, i)

    def calc_loss_round_count(n):
        if n < 0:
            return 0
        if loss_round_count_list[n] is not None:
            return loss_round_count_list[n]
        loss_round_count = 0
        for i in range(1, 5 + 1):
            loss_round_count += calc_loss_round_count(n - i) * hit_num_possible_list[i]
        loss_round_count += no_hit_round_count_list[n] * (1 + hit_num_possible_list[0])
        loss_round_count_list[n] = loss_round_count
        return loss_round_count

    calc_loss_round_count(book_num)
    return loss_round_count_list[book_num]
