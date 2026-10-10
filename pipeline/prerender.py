"""并行预渲染一期的所有画面片段（图表卡和官方视频片段），之后 assemble.py 会直接复用。

用法: .venv/bin/python pipeline/prerender.py videos/EPxxx_* [--workers 8]
"""
import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import assemble as A  # noqa: E402
import v2  # noqa: E402


def one(args):
    ep, i, v = args
    work = os.path.join(ep, "99_工作文件")
    # 只渲染这一个画面（编号与整期时间线一致，文件名才能被 assemble 复用）
    v2.build_clips(ep, [v], work, False, index_offset=i)
    return i, v["id"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    ep = a.episode.rstrip("/")
    script = json.load(open(os.path.join(ep, "01_文案/script.json"), encoding="utf-8"))
    visuals, *_ , total = v2.build_timeline_long(ep, script, A.LEAD, A.TITLE_DUR, A.decode_mp3)
    visuals[-1]["dur"] += 1.0
    jobs = [(ep, i, v) for i, v in enumerate(visuals)]
    jobs.sort(key=lambda j: -j[2]["dur"])  # 长的先做
    with ProcessPoolExecutor(a.workers) as ex:
        for f in as_completed([ex.submit(one, j) for j in jobs]):
            i, vid = f.result()
            print(f"done {i:03d} {vid}", flush=True)


if __name__ == "__main__":
    main()
