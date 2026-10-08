"""读取同目录 .env 里的密钥和设置。"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.expanduser("~/Library/Fonts")
FONT_BOLD = os.path.join(FONT_DIR, "SourceHanSansTC-Bold.otf")
FONT_HEAVY = os.path.join(FONT_DIR, "SourceHanSansTC-Heavy.otf")


def load_env():
    env = {}
    with open(os.path.join(HERE, ".env"), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


ENV = load_env()
