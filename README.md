# Python implementation of 植物大战僵尸 ol 助手

使用 Python 实现的植物大战僵尸 ol 助手。

该项目为开源项目，项目地址：https://github.com/bwnotfound/pypvzol

注意，目前支持私服不支持官服，等私服适配加完后再适配官服。

## 关于开源协议

植物大战僵尸ol助手 © 2023/11/25 by 蓝白bw is licensed under CC BY-NC-SA 4.0. To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/

本项目使用的开源协议为 CC BY-NC-SA 4.0，该协议要求署名、非商业使用、相同方式共享。

## 声明

本项目为开源项目，项目的贡献者不知道所有用户的输入，因此不负责任何用户的输入。

因使用本项目而造成的任何损失和影响都与本项目贡献者无关，用户需对自己的操作负责。

本项目仅供学习交流使用，不得用于商业用途，否则后果自负。

将该项目用于任何途径造成的任何损失均由自己承担，项目拥有者不负任何责任。

使用本项目的任何代码或者二进制文件都视为已同意本声明以及LICENSE文件声明的协议。

## 使用规约

1.  本项目是基于学术交流目的建立，仅供交流与学习使用，并非为生产环境准备，因其造成的损失将由自己承担。
2.  任何基于本项目制作的视频都必须在简介中声明项目来源。
3.  不可用本项目进行网络攻击。
4.  禁止使用该项目从事违法行为与宗教、政治等活动，该项目维护者坚决抵制上述行为，不同意此条则禁止使用该项目。
5.  继续使用视为已同意本仓库 README 所述相关条例，本仓库 README 已进行劝导义务，不对后续可能存在问题负责。
6.  如果将此项目用于任何其他企划，请提前联系并告知本仓库作者，十分感谢。

## 使用提醒

1.  请一定要看控制台的输出，因为报错信息并不会全部都在日志面板上显示，同时日志面板也不是很方便
2.  Cookie 的获取方法如下：打开`cookie.xml`文件找到`<UserCookies>......</UserCookies>`。中间省略的就是cookie。

## 通用使用方法

1.  要删除列表物品，选中物品并按“删除键(Delete)或者“退格键(Backspace)”即可（这点操作基本是通用的）
2.  大部分列表支持多选。多选方法：按住 ctrl 然后左键即可
3.  当希望刷新助手数据，请手动点击`刷新仓库`然后再打开对应窗口即可

### 运行源码

1.  python 版本选择: 3.10.6 (理论上 3.8~3.11 都可用)
2.  安装依赖:
    ```shell
    # 如果可以的话，建议使用虚拟环境venv
    $ pip install -r requirements.txt
    ```
3.  运行：
    ```shell
    $ python webUI.py
    ```

## 后话

~~关注 B 站[蓝白 bw](https://space.bilibili.com/107433411)喵， 关注[蓝白 bw](https://space.bilibili.com/107433411)谢谢喵~~

### Q&A

1.  Q: 为什么要叠这么多甲呢？

    A: 别问，问就是没版权爱发电。

2.  Q: 为什么压缩包这么大

    A: 因为 python 的一个库(pyqt6)很大

3.  Q: 为什么官服不能用？

    A: 小傻瓜，还玩官服呢。之后可能会适配官服，当然大概率是不考虑官服适配了

4.  Q: 私服怎么玩？

    A: 请自行B站查找教程，这里不提供相关教程


## TODO LIST:

#### 新加内容

1.  (可选)加默认模板和种子文件识别功能
2.  判断难度4打的是谁
3.  技能遗忘
4.  自动复合加速，底座分出去的时候分出去的和底座同时滚
5.  添加商店购买面板                            
6.  添加跨服队伍设置
7.  回调道具自动使用
8.  添加跨服奖励自动领取


#### BUG LIST

1. 全自动留待修复：
   1. 买东西如果买相同的东西就会无法成功购买
2. "During handle of the above exception" 较多小模块网络超时bug


新助手pre27更新内容：

TODO:
1.  自动速度复合
2.  一键设置用某品质全自动滚包(非复合)

新加内容：
1.  优化刷洞加速
2.  全自动刷洞默认设置优化
3.  添加刷洞自动用宝石书

修复内容：
1.  修复跨服挑战次数用不完的bug
2.  修复全自动用沙子timeout后中断的bug

新助手pre26更新内容：

新加内容：
1.  重改自动复合和全自动的k值意义(以助手内方案为准)
2.  全自动添加资源预检
3.  加入自动开副本
4.  优化植物信息显示
5.  自动升级技能模块添加多线程，添加自动升级宝石
6.  副本挑战支持多线程，添加副本二层适配，添加自动使用副本挑战书功能
7.  添加连胜次数统计与20次自动退出
8.  助手文件夹添加宝典
9.  添加vip剩余天数展示
10. 添加日志本地存储
11. 添加服务器配置导出功能
12. 添加智能领地，添加领地多线程
13. 自动复合添加无极一套数量展示
14. 全自动魔神箱子数量加入防呆，并添加一键设置数量功能
15. 添加自定义品质序列
16. 添加领地互斥
17. 添加宝石副本开图

修复内容：
1.  修复传承面板传出植物消失bug
2.  修复副本挑战不完全就退出的bug
3.  修复自动挑战植物没血后无法退出的bug
4.  修复打洞回血对死了的主力回复两次的bug
5.  修复并发频繁后等很久后才继续的bug
6.  服务器更新、ip限流、账号限流等待次数改为无限

注意：本次助手更新更改了全自动和自动复合的k值意义，请重新设置方案！！！


新助手pre25更新内容：

新加内容：
1.  添加了jjc指令打和自动领jjc奖励
2.  添加了用户信息刷新功能
3.  添加每日签到领取累计签到奖励
4.  添加自动参数推荐图片展示
5.  添加禁锢模拟
6.  开箱换成多线程，避免卡死
7.  添加进化多线程
8.  添加花园植物选取专属展示
9.  添加自动指令

修复内容：
1.  修复多用户并发锁共用的问题
2.  修复领地、跨服匹配不到人而自动中断的问题
3.  修复跨服莫名停止的bug
4.  修复进化bug
5.  修复副本回血bug
6.  修复副本、花园设置出战植物设置不方便问题
7.  修复全自动当某一个属性到了设定值之后不会立即停止的问题
8.  修复打洞一批后就中断继续循环的问题

注意：本次更新可以迁移data，方法是复制data文件夹到新版本的文件夹中