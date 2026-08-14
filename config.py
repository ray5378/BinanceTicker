"""自选币种配置持久化

配置保存在 %APPDATA%/BinanceTicker/config.json（Windows），
或程序同目录（其他平台）。
"""
import json
import os
import sys

APP_NAME = "BinanceTicker"

DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT", "XRPUSDT"]

PRESET_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "LINKUSDT", "DOTUSDT", "AVAXUSDT",
    "TRXUSDT", "SHIBUSDT", "LTCUSDT", "NEARUSDT", "TONUSDT",
]


def _config_dir():
    base = os.environ.get("APPDATA")
    if base:
        path = os.path.join(base, APP_NAME)
        os.makedirs(path, exist_ok=True)
        return path
    return os.path.dirname(os.path.abspath(sys.argv[0]))


CONFIG_PATH = os.path.join(_config_dir(), "config.json")


def load_symbols():
    """读取自选交易对列表，失败时返回默认列表。"""
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            data = json.load(f)
        symbols = [str(s).strip().upper() for s in data.get("symbols", [])]
        return [s for s in symbols if s]
    except Exception:
        return list(DEFAULT_SYMBOLS)


def save_symbols(symbols):
    """保存自选交易对列表。"""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"symbols": [s.upper() for s in symbols]}, f,
                      ensure_ascii=False, indent=2)
    except Exception:
        pass