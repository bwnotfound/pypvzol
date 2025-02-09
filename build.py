import os
import shutil

version = "pre32_1"
name = "植物大战僵尸ol助手_{}".format(version)
os.system(
    "pyinstaller "
    "--log-level=INFO "
    "--noconfirm "
    "-c "
    "-i ./dev/icon.png "
    "--onedir "
    "--collect-submodules pyamf "
    f"--name={name} "
    "./webUI.py"
)
root_dir = f"./dist/{name}"
os.rename(f"{root_dir}/{name}.exe", f"{root_dir}/pvzol助手.exe")
shutil.copyfile("./README.md", f"{root_dir}/使用须知README.txt")
shutil.copytree("./data/cache/pvz", f"{root_dir}/data/cache/pvz")
# shutil.copytree("./data/cache", f"{root_dir}/data/cache")
# youkia_dir = os.path.join(root_dir, "data/cache/youkia")
# for name in os.listdir(youkia_dir):
#     if ".swf" in name and name != "main.swf":
#         os.remove(os.path.join(youkia_dir, name))
shutil.copytree("./data/image", f"{root_dir}/data/image")
# shutil.copyfile("./information/常见问题.md", f"{root_dir}/常见问题.txt")
# shutil.copyfile("./information/如何迁移旧版本数据.txt", f"{root_dir}/如何迁移旧版本数据.txt")
shutil.copyfile("./LICENSE", f"{root_dir}/LICENSE")
# shutil.copyfile("./README.md", f"{root_dir}/警告：本助手不可盈利，分享规则请看README.txt")
shutil.copyfile("./docs/植物宝典.txt", f"{root_dir}/植物宝典.txt")
shutil.copyfile("./docs/赞助者名单.txt", f"{root_dir}/赞助者名单.txt")
# os.makedirs(f"{root_dir}/game_window")
# shutil.copytree("./game_window/build", f"{root_dir}/game_window")
# removed_file_name = [
#     "GPUCache",
#     "start_config.json",
#     "config.ini",
# ]
# for file_name in removed_file_name:
#     if os.path.exists(f"{root_dir}/game_window/{file_name}"):
#         os.remove(f"{root_dir}/game_window/{file_name}")
# shutil.copyfile("./game_window/build/game_window.exe", f"{root_dir}/game_window/game_window.exe")
# shutil.copyfile("./game_window/proxy.py", f"{root_dir}/game_window/proxy.py")
