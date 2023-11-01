# Python implementation of 植物大战僵尸 ol 助手

使用 Python 实现的植物大战僵尸 ol 助手，具有一些原有助手没有的功能。

该项目为开源项目，项目地址：https://github.com/bwnotfound/pypvzol

注意，目前支持私服不支持官服，等私服适配加完后再适配官服。

## 介绍

本项目目的是实现原有助手没有但十分有必要的功能，同时开源保证安全性。

目前支持的功能有

1.  自动练级（优先高等级炮灰打高等级洞口）
2.  自动进化（可以自主设置进化路线）
3.  自动刷品（支持多个植物同时刷品）
4.  自动购买普通商店物品（可以自动买进化材料）
5.  自动使用道具
6.  自动领取任务奖励
7.  自动合成滚包

该助手支持私服的使用

**请一定要看使用提醒**

由于带有一定的练手性质，所以代码可能较为混乱，同时更新随缘。

## 声明

本项目为开源项目，项目的贡献者不知道所有用户的输入，因此不负责任何用户的输入。

因使用本项目而造成的任何损失和影响都与本项目贡献者无关，用户需对自己的操作负责。

本项目仅供学习交流使用，不得用于商业用途，否则后果自负。

将该项目用于任何途径造成的任何损失均由自己承担，项目拥有者不负任何责任。

使用本项目的任何代码或者二进制文件都视为已同意本声明。

## 使用规约

1.  本项目是基于学术交流目的建立，仅供交流与学习使用，并非为生产环境准备，因其造成的损失将由自己承担。
2.  任何基于本项目制作的视频都必须在简介中声明项目来源。
3.  不可用本项目进行网络攻击。
4.  禁止使用该项目从事违法行为与宗教、政治等活动，该项目维护者坚决抵制上述行为，不同意此条则禁止使用该项目。
5.  继续使用视为已同意本仓库 README 所述相关条例，本仓库 README 已进行劝导义务，不对后续可能存在问题负责。
6.  如果将此项目用于任何其他企划，请提前联系并告知本仓库作者，十分感谢。

## 使用提醒

1.  1~11 区是一定使用不了的，需要注意
2.  **该助手所有功能在 24 区上测试过，部分功能在 46 区上测试过** 如果有 bug 请提交 issue 或者 pr。
3.  请一定要看控制台的输出，因为报错信息并不会全部都在日志面板上显示，同时日志面板也不是很方便
4.  拦截区无能为力，因为 418 访问拦截十分频繁，使用体验不好（当然还是好用的）
5.  Cookie 的获取方法如下：在植物大战僵尸 ol 网页版登录后，按 F12 打开开发者工具，在上方工具栏中点击“控制台”，然后下方输入`document.cookie`，回车，即可获取到 cookie 值。如果你用了原有助手，那么把原有助手的 Config 文件夹下你对应区的 xml 文件打开，搜索`UserCookies`也能获取到 cookie 值。
6.  cookie 值长这样`pvz_youkia=......`或者`pvzol=......`。也可以在种子文件里面找到`<UserCookies>.......</UserCookies>`。中间的就是cookie
7.  助手是不支持 win7 的，也不会在 win7 环境下测试。目前保证助手支持 win10 及以上

## 使用方法

1.  要删除列表物品，选中物品并按“删除键(Delete)或者“退格键(Backspace)”即可（这点操作基本是通用的）
2.  大部分列表支持多选。多选方法：按住 ctrl 然后左键即可
3.  练级功能设置上，默认是每次挑战前利用设置的血瓶为血量为 0 的所有植物回血。所有主力均会出战，炮灰与洞口等级差大于等于 5 的会出战，同时优先使用更高等级的炮灰。
4.  进化功能：单选一个植物，点击添加路线，然后选择路线后点击修改路线。在右边的面板有当前植物的下一个进化形态，单击选择即可。如果有进化形态选错了，可以在左边面板删除。退出修改路线后，单选或多选同种植物，然后再选择对应路线点击进化就行。注意可以多选植物进化，也可以从进化路线中间开始进化，例如冥鬼王+4，可以用冥鬼王->冥鬼王Max的进化路线进化
5.  由于该助手请求次数很快，所以小部分请求是会发生错误的。这种时候重新运行即可。
6.  部分列表可能不会及时反馈结果，如果要看结果请手动点击`刷新仓库`然后再打开对应窗口即可
7.  自动合成的本质就是选取一个主植物(底座)和一些用于滚的植物(合成池)，然后每次从合成池中选一个植物吃主植物(底座)，吃完后移除被吃的主植物(底座)，接着把吃了底座的植物设置为新的主植物(底座)。循环上述过程中从而自动合成。然而虽然我测试过是无误的，但依旧可能在实际使用中存在 bug。请积极在 issue 反馈或者 b 站私信我，同时慎重使用该功能。

### 运行源码

如果只是使用，直接下载 release 里的文件即可。

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

2.  Q: 为什么要为这个凉透了的游戏写个助手呢？

    A: ~~因为我想写，所以我写了。~~ 其实主要是是练手，当然也是因为我还算是比较喜欢这个游戏。既然暂时还没有被强登，同时也处于快速上升期，那就索性安安心心地当休闲养老游戏了。

3.  Q: 为什么有助手了还要写一个呢？

    A: 原来助手没有练级功能(强行练级很低效)，也没有自定义进化，同时似乎有后台爬用户信息的嫌疑，于是干脆自己写一个

4.  Q: 还玩这 sb 游戏呢？

    A: 还真是

5.  Q: 为什么压缩包这么大

    A: 因为 python 的一个库(pyqt6)很大

## Bug list:

列一些知道但暂时还没去管的 bug

1.  老区（例如 1 区）和新区的 api 不一致，例如 url 中是"pvz-"开头的
2.  暂未添加主力回血功能，所以主力植物不强的话可能会死(死后按照选择的血瓶回血)。Log 文本框还未与主线程独立，会卡死，各个挑战次数统计还未实现，所以每次打开都会重新计算

## TODO LIST:

1.  添加世界副本选项
2.  支持副本次数指定
3.  时钟怀表刷新
4.  自动升级宝石
5.  考虑添加远程端口能够简单控制助手
6.  副本和宝石副本的层级控制
7.  页面ui调整
8.  日志缓存恢复，掉落统计
9.  能够刷新用户面板的数据
10. 自动合成的底座植物显示所有属性，加入换行以分辨什么是主属性
11. 自动滚包锁定植物（也可以锁定属性）
12. 优化竞技场，挑战到出错再获取列表信息
13. 小号给大号用时之沙
14. 把带级和刷洞区分一下
15. 进化的超时bug处理并单独线程处理
16. 添加魔刷刷品