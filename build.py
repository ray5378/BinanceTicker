"""PyInstaller 打包脚本：python build.py"""
import os

import PyInstaller.__main__

HERE = os.path.dirname(os.path.abspath(__file__))

args = [
    os.path.join(HERE, "main.py"),
    "--name", "BinanceTicker",
    "--onefile",
    "--noconsole",
    "--clean",
    "--noconfirm",
]

icon = os.path.join(HERE, "assets", "icon.ico")
if os.path.exists(icon):
    args += ["--icon", icon]

PyInstaller.__main__.run(args)
print("Done: dist/BinanceTicker.exe")