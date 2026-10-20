"""EP005 的 3 条独立 Shorts（纸张风格 pipeline/shorts_paper.py，繁体 lang=tc）。
每条：点题钩子 → 背景 → 2～3 个硬细节 → 反转 → 带走的道理 → 二选一提问。画面按词切换（beats.at），约 2～3 秒一切。"""
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
EP = os.path.dirname(HERE)

# 网页截图也当图片用（shorts_paper 从 场景图/ 读）
for k in ("shot_read_news", "shot_read_wiki", "shot_crains_crop", "shot_tw_2020", "shot_nber"):
    src = os.path.join(EP, "03_画面素材/网页截图", k + ".png")
    dst = os.path.join(EP, "03_画面素材/场景图", k + ".png")
    if os.path.exists(src) and not os.path.exists(dst):
        shutil.copy(src, dst)

END = {"kicker": "如果這個故事對你有幫助", "line1": "訂閱，一起讀完", "line2": "《致富心態》", "seal": "訂"}

SHORTS = {
 "S01": {
  "hook": {"kicker": "致富心態 · 序言", "title": "清潔工留下 800 萬美元", "sub": "他沒有秘密，只有耐心", "seal": "壹"},
  "cap_hl": ["800萬美元", "95家", "480萬", "120萬", "耐心"],
  "paras": [
   "一個在百貨公司拖了17年地板的清潔工，過世後，留下將近800萬美元。",
   "他叫羅納德．里德，住在美國佛蒙特州的一個小鎮。他做了將近25年的加油站工人，外套破了，就用別針別起來，開一台二手小車，停車還專挑不用投幣的位子。",
   "沒有人知道，他每天都讀《華爾街日報》，把省下來的每一分錢，拿去買寶僑、嬌生這種大公司的股票。領了股息就再買進，一抱就是幾十年。",
   "他過世的時候，手上至少有95家公司的股票。2008年雷曼兄弟倒閉，他也有持股，但分散在95家公司裡，影響不大。",
   "遺囑公開，480萬美元捐給醫院，120萬美元捐給圖書館，都是這兩個地方史上最大的捐款。",
   "他沒有秘密：花得比賺得少，買很多好公司，然後等。你覺得，致富靠的是聰明，還是耐心？",
  ],
  "beats": [
   {"img": "ill_janitor", "fx": 0.5, "zoom": "in", "pops": [{"kind": "label", "text": "17 年 · 百貨公司清潔工", "x": 40, "y": 110, "delay": 0.5}]},
   {"at": "過世後", "img": "ill_read_town", "fx": 0.45, "zoom": "in"},
   {"at": "將近800萬美元", "card": {"type": "num", "big": "800 萬", "sub": "美元 · 2014 年過世時的遺產"}},
   {"at": "他叫羅納德", "img": "ill_read_town", "scale": 1.5, "fx": 0.42, "fy": 0.4, "zoom": "in", "pops": [{"kind": "label", "text": "羅納德．里德 1921–2014", "x": 40, "y": 110}]},
   {"at": "佛蒙特州", "img": "web_brattleboro", "fx": 0.5, "zoom": "in"},
   {"at": "加油站工人", "img": "ill_gas_station", "fx": 0.4, "zoom": "in"},
   {"at": "外套破了", "img": "ill_safety_pin", "fx": 0.5, "zoom": "in", "pops": [{"kind": "stamp", "text": "別針", "at": "別針", "x": 620, "y": 780, "rot": -8, "size": 96}]},
   {"at": "停車還專挑", "card": {"type": "list", "title": "他的日常", "items": ["外套破了用別針", "開二手小車", "只停不用投幣的車位"]}},
   {"at": "沒有人知道", "img": "ill_wsj", "fx": 0.5, "zoom": "in"},
   {"at": "每一分錢", "img": "ill_wsj", "scale": 1.5, "fx": 0.6, "fy": 0.55, "zoom": "in"},
   {"at": "寶僑", "card": {"type": "note", "kicker": "他只買叫得出名字的大公司", "text": "寶僑、嬌生\n摩根大通、奇異……", "hl": "寶僑、嬌生"}},
   {"at": "領了股息", "img": "ill_stock_box", "fx": 0.5, "zoom": "in"},
   {"at": "他過世的時候", "card": {"type": "num", "big": "95 家", "sub": "過世時手上公司的股票數"}},
   {"at": "2008年雷曼兄弟", "img": "ill_crash2008", "fx": 0.5, "zoom": "in", "pops": [{"kind": "stamp", "text": "倒閉", "at": "倒閉", "x": 560, "y": 700, "rot": 7, "size": 100}]},
   {"at": "但分散在", "card": {"type": "compare", "title": "雷曼倒閉，對他影響多大？", "rows": [["只押一家", "全部歸零", "no"], ["分散 95 家", "影響不大", "ok"]]}},
   {"at": "遺囑公開", "img": "shot_read_news", "fx": 0.35, "zoom": "in"},
   {"at": "480萬美元", "card": {"type": "list", "title": "遺囑怎麼分", "items": ["醫院：480 萬美元", "圖書館：120 萬美元", "家人與朋友：200 萬美元"]}},
   {"at": "都是這兩個地方", "img": "ill_pavilion", "fx": 0.5, "zoom": "in"},
   {"at": "他沒有秘密", "card": {"type": "list", "title": "他的方法", "items": ["花得比賺得少", "買很多好公司", "然後，等"]}},
   {"at": "你覺得", "img": "ill_read_town2", "dim": 0.62, "card": {"type": "ask", "q": "致富靠的是？", "opts": ["聰明", "耐心"], "foot": "留言告訴我你的答案"}},
  ],
 },
 "S02": {
  "hook": {"kicker": "致富心態 · 序言", "title": "哈佛 MBA、美林高管，為什麼破產", "sub": "豪宅每月維護費 9 萬美元", "seal": "貳"},
  "cap_hl": ["哈佛", "美林", "9萬美元", "破產", "沒有任何收入", "法院拍賣"],
  "paras": [
   "哈佛商學院畢業、美林證券高階主管、四十多歲就退休，這樣的人，最後竟然破產了。",
   "他叫理查．福斯肯。1991年，他被紐約的商業雜誌，選為四十歲以下最有成就的四十位商業人士之一。",
   "2005年前後，他大量借錢，擴建自己在格林威治的豪宅：11間浴室、兩部電梯、兩座游泳池、7個車庫，光是每個月的維護費，就要9萬美元。",
   "然後，2008年，金融海嘯來了。資產大幅縮水，借來的錢卻一毛都不會少。他對破產法官說：我現在沒有任何收入。2014年，豪宅被法院拍賣。",
   "諷刺的是，同一年，一個沒念過大學的清潔工，留下了800萬美元。決定結局的，不是學歷，是行為。你覺得，讓人破產的，是能力不夠，還是停不下來？",
  ],
  "beats": [
   {"img": "ill_fuscone_office", "fx": 0.5, "zoom": "in", "pops": [{"kind": "label", "text": "哈佛 MBA · 美林證券", "x": 40, "y": 110, "delay": 0.5}]},
   {"at": "四十多歲就退休", "img": "ill_mansion", "fx": 0.5, "zoom": "in"},
   {"at": "竟然破產了", "img": "ill_foreclosure", "fx": 0.5, "zoom": "in", "pops": [{"kind": "stamp", "text": "破產", "at": "破產", "x": 560, "y": 740, "rot": -7, "size": 110}]},
   {"at": "他叫理查", "img": "shot_crains_crop", "fx": 0.2, "zoom": "in", "pops": [{"kind": "label", "text": "理查．福斯肯", "x": 40, "y": 110}]},
   {"at": "1991年", "card": {"type": "note", "kicker": "1991 年 · 紐約商業雜誌", "text": "40 歲以下\n最有成就的 40 人", "hl": "最有成就"}},
   {"at": "2005年前後", "img": "ill_mansion", "scale": 1.4, "fx": 0.5, "fy": 0.6, "zoom": "in"},
   {"at": "11間浴室", "card": {"type": "list", "title": "格林威治豪宅", "items": ["11 間浴室", "兩部電梯、兩座游泳池", "7 個車庫"]}},
   {"at": "光是每個月", "card": {"type": "num", "big": "9 萬", "sub": "美元 · 每個月的維護費"}},
   {"at": "然後", "img": "ill_crash2008", "fx": 0.5, "zoom": "in", "pops": [{"kind": "label", "text": "2008 金融海嘯", "x": 40, "y": 110}]},
   {"at": "借來的錢", "card": {"type": "compare", "title": "金融海嘯之後", "rows": [["資產", "大幅縮水", "no"], ["借來的錢", "一毛都不少", "no"]]}},
   {"at": "他對破產法官說", "img": "ill_lamp", "dim": 0.6, "card": {"type": "quote", "text": "我現在\n沒有任何收入。", "hl": "沒有任何收入", "by": "—— 福斯肯對破產法官", "seal": "破"}},
   {"at": "2014年", "img": "ill_foreclosure", "scale": 1.4, "fx": 0.6, "fy": 0.55, "zoom": "in", "pops": [{"kind": "stamp", "text": "法拍", "at": "法院拍賣", "x": 520, "y": 760, "rot": 6, "size": 110}]},
   {"at": "諷刺的是", "img": "ill_read_town", "fx": 0.45, "zoom": "in"},
   {"at": "800萬美元", "card": {"type": "compare", "title": "2014 年，兩個人", "rows": [["清潔工", "留下 800 萬", "ok"], ["華爾街菁英", "豪宅法拍", "no"]]}},
   {"at": "決定結局的", "card": {"type": "note", "kicker": "決定結局的", "text": "不是學歷\n是行為", "hl": "是行為"}},
   {"at": "你覺得", "img": "ill_mansion", "dim": 0.62, "card": {"type": "ask", "q": "讓人破產的是？", "opts": ["能力不夠", "停不下來"], "foot": "留言告訴我你的答案"}},
  ],
 },
 "S03": {
  "hook": {"kicker": "致富心態 · 第一章", "title": "你哪一年出生，決定你怎麼看股票", "sub": "台股 1990：30 年才回來", "seal": "參"},
  "cap_hl": ["12,682點", "2,485點", "八成", "30年", "1965年", "1995年", "50年"],
  "paras": [
   "你哪一年出生，可能決定了你一輩子怎麼看股票。",
   "1990年2月，台股衝上12,682點。接下來大約8個月，一路跌到2,485點，跌掉了八成。之後整整30年，直到2020年7月，才突破那個高點。",
   "如果你1965年出生，25歲第一次投資，就遇上崩盤八成。如果你1995年出生，25歲那年，台股剛好創下歷史新高。",
   "經濟學家研究了美國50年的資料，發現年輕時經歷過股市大漲的人，一輩子會多買股票；在高通膨年代長大的人，一輩子會少買債券。",
   "所以，沒有人真的對錢失去理智，大家只是活在不同的世界裡。你第一次投資，遇到的是牛市，還是熊市？",
  ],
  "beats": [
   {"img": "ill_two_taiwanese", "fx": 0.5, "zoom": "in"},
   {"at": "一輩子怎麼看股票", "img": "ill_two_taiwanese", "scale": 1.5, "fx": 0.75, "fy": 0.45, "zoom": "in"},
   {"at": "1990年2月", "img": "ill_tw_1990", "fx": 0.5, "zoom": "in", "pops": [{"kind": "label", "text": "1990 · 台北號子", "x": 40, "y": 110}]},
   {"at": "12,682點", "card": {"type": "num", "big": "12,682", "sub": "1990 年 2 月 · 台股歷史高點", "color": "blue"}},
   {"at": "一路跌到", "card": {"type": "num", "big": "2,485", "sub": "約 8 個月後 · 跌掉八成"}},
   {"at": "之後整整30年", "card": {"type": "timeline", "rows": [["1990.2", "12,682 點"], ["1990.10", "2,485 點"], ["2020.7.27", "突破 12,682 點"]], "hl": [1, 2]}},
   {"at": "突破那個高點", "img": "shot_tw_2020", "fx": 0.3, "zoom": "in"},
   {"at": "如果你1965年出生", "img": "ill_two_taiwanese", "scale": 1.6, "fx": 0.25, "fy": 0.5, "zoom": "in", "pops": [{"kind": "label", "text": "1965 年出生", "x": 40, "y": 110}]},
   {"at": "就遇上崩盤八成", "img": "ill_tw_1990", "scale": 1.5, "fx": 0.3, "fy": 0.6, "zoom": "in", "pops": [{"kind": "stamp", "text": "崩盤", "at": "崩盤", "x": 560, "y": 760, "rot": -7, "size": 110}]},
   {"at": "如果你1995年出生", "img": "ill_two_taiwanese", "scale": 1.6, "fx": 0.78, "fy": 0.5, "zoom": "in", "pops": [{"kind": "label", "text": "1995 年出生", "x": 1040, "y": 110, "anchor": "r", "from": "right"}]},
   {"at": "台股剛好", "card": {"type": "compare", "title": "25 歲第一次投資", "rows": [["1965 年出生", "崩盤八成", "no"], ["1995 年出生", "歷史新高", "ok"]]}},
   {"at": "經濟學家", "img": "shot_nber", "fx": 0.3, "zoom": "in"},
   {"at": "年輕時經歷過", "card": {"type": "list", "title": "年輕時經歷什麼，一輩子就怎麼投資", "items": ["股市大漲長大 → 多買股票", "高通膨長大 → 少買債券"]}},
   {"at": "所以", "img": "ill_two_families", "fx": 0.5, "zoom": "in"},
   {"at": "大家只是活在", "card": {"type": "note", "kicker": "沒有人真的對錢失去理智", "text": "大家只是活在\n不同的世界裡", "hl": "不同的世界"}},
   {"at": "你第一次投資", "img": "ill_tw_1990", "dim": 0.62, "card": {"type": "ask", "q": "你第一次投資遇到的是？", "opts": ["牛市", "熊市"], "foot": "留言告訴我你的答案"}},
  ],
 },
}

cfg = {}
for sid, sp in SHORTS.items():
    d = os.path.join(EP, "08_Shorts", sid)
    for sub in ("01_文案", "02_配音/segments", "99_工作文件"):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    script = {"episode": "EP005-" + sid, "version": 3, "tts_speed": 1.1, "title": sid,
              "sections": [{"id": "s0", "chapter": sid, "title_card": None,
                            "paragraphs": [{"id": f"p{i:02d}", "text": t, "visuals": ["beat"]} for i, t in enumerate(sp["paras"], 1)]}]}
    json.dump(script, open(os.path.join(d, "01_文案/script.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    cfg[sid] = {"template": "paper", "lang": "tc", "output_in_folder": True, "bgm_seed": 51,
                "hook": sp["hook"], "cap_hl": sp["cap_hl"], "beats": sp["beats"], "end": END}
    print(sid, sum(len(t) for t in sp["paras"]), "字")
json.dump(cfg, open(os.path.join(EP, "08_Shorts/shorts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
