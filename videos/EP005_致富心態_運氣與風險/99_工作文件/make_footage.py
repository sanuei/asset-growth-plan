"""生成 03_画面素材/视频素材/footage.json（本集用到的视频片段）。时间点来自抽帧总览，src 在 视频素材/raw/。

来源与授权：
- Prelinger Archives（Internet Archive）：只用标明公有领域（creativecommons.org/licenses/publicdomain）的影片。
- Wikimedia Commons：作者与授权见 raw/commons.json。
- Mixkit：只用 Mixkit Free License（可商用、免署名）的片段，画面上仍标「Mixkit」。
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "03_画面素材/视频素材/footage.json")
RAW = os.path.join(os.path.dirname(HERE), "03_画面素材/视频素材/raw")

PRE = "影片：Prelinger Archives（公有領域）"
MIX = "影片：Mixkit"
commons = json.load(open(os.path.join(RAW, "commons.json"), encoding="utf-8"))


def cm(key):
    v = commons[key]
    return {"src": v["file"], "credit": f"影片：{v['artist'][:40]} · {v['license']} · Wikimedia Commons"}


F = {}


def pre(fid, film, start, **kw):
    F[fid] = {"src": film + ".mp4", "start": start, "credit": PRE, **kw}


def mix(fid, num, start=0.0, **kw):
    F[fid] = {"src": f"m_{num}.mp4", "start": start, "credit": MIX, **kw}


def com(fid, key, start=0.0, **kw):
    F[fid] = {**cm(key), "start": start, **kw}


# 西雅图（1961、1962 世博）
com("v_seattle61", "c_seattle_documentary_clip_1961", 9.0)
pre("v_seattle62", "Century21964", 34.0)
pre("v_monorail", "Century21964", 40.5)
pre("v_fair_crowd", "Century21964", 83.0)
pre("v_needle_night", "Century21964", 750.5)
pre("v_teens_monorail", "Century21964", 20.5)
# 电传打字机、大型电脑
pre("v_tty_hands", "Telegram1956", 310.5)
pre("v_tty_woman", "Telegram1956", 374.0)
pre("v_tty_print", "Telegram1956", 900.5)
pre("v_tty_paper", "Telegram1956", 1010.5)
pre("v_office50s", "Telegram1956", 800.5)
com("v_fernschreiber", "c_fernschreiberpr_fung", 1.0)
com("v_fernschreiber2", "c_fernschreiberpr_fung", 14.0)
pre("v_mainframe", "OnGuard1956", 110.5)
pre("v_mainframe2", "OnGuard1956", 250.5)
pre("v_punchcard", "OnGuard1956", 160.5)
pre("v_tapedrive", "OnGuard1956", 230.5)
pre("v_panel_lights", "OnGuard1956", 610.5)
# 电话
pre("v_phone_boy", "WeLearnA1965", 20.5)
pre("v_phone_teen", "WeLearnA1965", 30.5)
pre("v_dial_beige", "WeLearnA1965", 830.5)
pre("v_dial_black", "WeLearnA1965", 990.5)
com("v_w48_dial", "c_telefon_w48_deutsche_bundespost_1950er_j", 0.5)
# 学校
pre("v_classroom", "MindYour1953", 410.5)
pre("v_school_walk", "MindYour1953", 380.5)
pre("v_teen_phone53", "MindYour1953", 210.5)
pre("v_school_hall", "MindYour1953", 455.5)
mix("v_students", 4519, 2.0)
mix("v_library", 21595, 1.0)
mix("v_notes", 50109, 0.5)
# 登山、雪山
com("v_climb", "c_u_s_army_troops_participate_in_mountaine", 22.0)
com("v_climb2", "c_u_s_army_troops_participate_in_mountaine", 48.0)
com("v_rim", "c_summit_rim_of_mount_st_helens", 2.0)
com("v_rim2", "c_summit_rim_of_mount_st_helens", 40.0)
com("v_rim_person", "c_summit_rim_of_mount_st_helens", 82.0)
mix("v_peaks_fog", 4396, 0.5)
mix("v_peak_fly", 51689, 3.0)
mix("v_snow_hills", 3371, 4.0)
# 运气、风险、时间
mix("v_hourglass", 28901, 0.5)
com("v_dice_slow", "c_dice_rolling_slowmotion_2018_9", 0.5)
mix("v_dice_throw", 5238, 0.5)
mix("v_dice_mix", 5232, 0.5)
mix("v_poker", 5240, 0.5)
mix("v_coins_hand", 18263, 0.5)
mix("v_magazine", 41194, 1.0)
mix("v_magazines", 21590, 1.0)
mix("v_newspaper", 41192, 0.5)
mix("v_crowd", 4401, 1.0)
mix("v_sunset_tracks", 1594, 2.0)
mix("v_handshake", 30016, 0.5)
# 华尔街
pre("v_wallst", "big_board", 3.5)
pre("v_nyse_floor", "big_board", 40.5)
pre("v_nyse_floor2", "big_board", 644.0)
pre("v_nyse_floor3", "big_board", 724.0)
pre("v_stockboard", "big_board", 244.0)
pre("v_ticker", "big_board", 580.5)
pre("v_trader_phone", "big_board", 220.5)
pre("v_city60s", "ChanceYouTak", 30.5)
pre("v_tower_up", "ChanceYouTak", 40.5)
# 铁路
pre("v_old_loco", "Mainline1957", 110.5)
pre("v_old_loco2", "Mainline1957", 210.5)
pre("v_old_locos", "Mainline1957", 200.5)
pre("v_tracks", "Mainline1957", 120.5)
pre("v_streamliner", "Mainline1957", 300.5)
pre("v_railyard", "Mainline1957", 720.5)
com("v_steam", "c_steam_train_60163_tornado_whistles_past", 38.0)
# 盖茨本人
com("v_gates_talk", "c_bill_gates_itu_150_video", 10.0)
com("v_gates_talk2", "c_bill_gates_itu_150_video", 70.0)
com("v_gates_talk3", "c_bill_gates_itu_150_video", 120.0)

# 同一素材的其他段落（避免同一段画面重复出现）
pre("v_classroom2", "MindYour1953", 420.5)
pre("v_classroom3", "MindYour1953", 430.5)
pre("v_tty_hands2", "Telegram1956", 312.5)
pre("v_tty_print2", "Telegram1956", 912.5)
com("v_dice_slow2", "c_dice_rolling_slowmotion_2018_9", 4.0)
mix("v_dice_throw2", 5238, 4.0)
mix("v_newspaper2", 41192, 4.0)
mix("v_crowd2", 4401, 10.0)
mix("v_snow_hills2", 3371, 12.0)
mix("v_sunset_tracks2", 1594, 12.0)
mix("v_magazine2", 41194, 8.0)
pre("v_jets", "OnGuard1956", 70.5)
mix("v_crowd3", 4401, 16.0)
pre("v_ticker2", "big_board", 742.0)
mix("v_students2", 4519, 10.0)

if __name__ == "__main__":
    json.dump(F, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(F), "个片段 →", OUT)
