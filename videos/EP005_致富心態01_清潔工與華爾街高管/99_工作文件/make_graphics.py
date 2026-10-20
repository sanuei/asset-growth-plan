"""生成 EP005 的 graphics.json（纸张风格图表/文字卡、网页截图卡、纸条章节卡）。数字来源见 sources/事实核对.md。"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "03_画面素材/graphics.json")
G = {}

# 纸条卡：开场钩子、片名、四部、片尾
G["hook_open"] = {"type": "ptitle", "text": "2014 年 · 美國佛蒙特州\n清潔工留下 800 萬美元", "bg": "ill_read_town", "size": 100}
G["brand_intro"] = {"type": "ptitle", "text": "清潔工，為什麼贏了華爾街", "bg": "ill_read_town2", "size": 120}
PARTS = [("壹", "第一部", "兩個人的一生", "ill_gas_station"), ("貳", "第二部", "理財，是一種軟技能", "ill_valet"),
         ("參", "第三部", "沒有人真的對錢失去理智", "ill_two_families"), ("肆", "第四部", "一場很新的遊戲", "ill_dog_wolf")]
for i, (num, k, t, bg) in enumerate(PARTS, 1):
    G[f"part_{i}"] = {"type": "ptitle", "text": f"{k}\n{t}", "num": num, "bg": bg}
G["end_card"] = {"type": "ptitle", "text": "如果這支影片對你有幫助\n訂閱，我們下次見", "num": "訂", "bg": "ill_read_town2"}

# 网页截图卡
WEB = {
    "shot_read_wiki": ("羅納德．里德（1921–2014）", "Wikipedia", "en.wikipedia.org/wiki/Ronald_Read_(philanthropist)", "ill_read_town", 0.5),
    "shot_read_news": ("遺囑公開：600 萬美元捐給醫院和圖書館", "FOX 5 DC／美聯社 2015/2/4", "fox5dc.com/news/man-who-lived-modestly-leaves-millions-in-surprise-donations", "ill_pavilion", 0.4),
    "shot_crains": ("《克萊恩紐約商業週刊》40 Under 40（1991）", "Crain's New York Business", "crainsnewyork.com — 40 Under 40 Class of 1991", "ill_fuscone_office", 0.15),
    "shot_nber": ("研究：〈大蕭條寶寶〉", "美國國家經濟研究局 NBER", "nber.org/papers/w14813", "ill_two_families", 0.35),
    "shot_tw_2020": ("2020/7/27 台股突破 12,682 點", "科技新報（中央社）2020/7/27", "finance.technews.tw/2020/07/27/taiwan-stocks-rose-to-a-new-record", "ill_tw_1990", 0.3),
    "shot_ida_wiki": ("艾達．梅．富勒：第一位領到社會安全月退休金的人", "Wikipedia", "en.wikipedia.org/wiki/Ida_May_Fuller", "ill_ida_check", 0.5),
}
for k, (title, src, url, bg, fx) in WEB.items():
    img = "shot_crains_crop.png" if k == "shot_crains" else k + ".png"
    G[k] = {"type": "web", "img": img, "title": title, "source": src, "url_label": url, "bg": bg, "focus_x": fx, "zoom": 0.08}

# 第一部
G["card_two_men"] = {"type": "compare", "bg": "ill_mansion", "title": "2014 年，兩個人的新聞",
                     "columns": [{"label": "加油站工人 → 百貨清潔工", "value": "留下 800 萬", "size": 104, "sub": "美元，大多捐給醫院與圖書館", "color": "green", "hl": True},
                                 {"label": "哈佛 MBA → 美林高管", "value": "破產、法拍", "size": 104, "sub": "借錢擴建豪宅，金融海嘯後", "color": "red"}],
                     "ops": ["vs"], "source": "資料：《致富心態》序言；Wikipedia；New York 雜誌 2010；紐約時報 2014"}
G["card_fields"] = {"type": "compare", "bg": "ill_read_town", "title": "在哪個領域，外行能贏過頂尖專家？",
                    "columns": [{"label": "心臟手術、蓋摩天大樓、核物理", "value": "幾乎不可能", "size": 96, "sub": "沒受過訓練，做不贏專家", "color": "fade"},
                                {"label": "理財、投資", "value": "一直發生", "size": 110, "sub": "清潔工贏過華爾街菁英", "color": "red", "hl": True}],
                    "ops": ["vs"], "source": "出處：《致富心態》序言（大意）"}
G["card_read_stocks"] = {"type": "plist", "bg": "ill_wsj", "heading": "羅納德．里德的投資方法",
                         "items": [["1", "只買叫得出名字的大公司（藍籌股）", "寶僑、嬌生、摩根大通…"],
                                   ["2", "股息領了就再買進"], ["3", "不碰自己看不懂的科技股"],
                                   ["4", "至少 95 家公司，一抱幾十年"]],
                         "source": "資料：Wikipedia（引《華爾街日報》等）"}
G["card_lehman"] = {"type": "compare", "bg": "ill_crash2008", "title": "2008 年：雷曼兄弟倒閉",
                    "columns": [{"label": "如果只押一家", "value": "全軍覆沒", "size": 104, "sub": "一家倒，全部歸零", "color": "red"},
                                {"label": "里德分散在 95 家", "value": "影響不大", "size": 104, "sub": "一家倒，其他繼續長", "color": "green", "hl": True}],
                    "ops": ["vs"], "source": "資料：Wikipedia: Ronald Read"}
G["card_read_estate"] = {"type": "hbars", "bg": "ill_pavilion", "title": "將近 800 萬美元的遺產，怎麼分",
                         "items": [{"label": "布拉特爾伯勒紀念醫院", "value": 4.8, "text": "480 萬", "color": "red"},
                                   {"label": "繼子女、照顧者、朋友", "value": 2.0, "text": "200 萬"},
                                   {"label": "布魯克斯紀念圖書館", "value": 1.2, "text": "120 萬"}],
                         "vmax": 5.6, "hl": [0], "source": "資料：美聯社 2015；Wikipedia（單位：美元）"}
G["card_mansion"] = {"type": "plist", "bg": "ill_mansion", "heading": "福斯肯在格林威治的豪宅",
                     "items": [["1", "將近 1,700 平方公尺"], ["2", "11 間浴室、兩部電梯"], ["3", "兩座游泳池、7 個車庫"],
                               ["4", "每月維護費：9 萬美元"]],
                     "source": "資料：《致富心態》序言（引 New York 雜誌 2010）"}
G["card_fuscone_fall"] = {"type": "ptimeline", "bg": "ill_crash2008", "title": "理查．福斯肯",
                          "events": [{"date": "1991", "label": "40 歲以下\n40 強", "color": "blue"},
                                     {"date": "40 多歲", "label": "退休\n做慈善", "color": "green"},
                                     {"date": "2005", "label": "大量借錢\n擴建豪宅", "color": "amber"},
                                     {"date": "2008", "label": "金融海嘯\n宣告破產", "color": "red", "hl": True},
                                     {"date": "2014", "label": "格林威治\n豪宅法拍", "color": "red"}],
                          "source": "資料：Crain's 1991；《致富心態》序言（引 NY 雜誌 2010、紐約時報 2014）"}
G["card_two_men2"] = {"type": "compare", "bg": "ill_read_town2", "title": "決定結局的，不是學歷",
                      "columns": [{"label": "羅納德．里德", "value": "耐心", "size": 140, "sub": "存下、買進、等幾十年", "color": "green", "hl": True},
                                  {"label": "理查．福斯肯", "value": "停不下來", "size": 120, "sub": "借錢、擴張、賭上全部", "color": "red"}],
                      "ops": ["vs"]}

# 第二部
G["q_behavior"] = {"type": "pquote", "bg": "ill_gold_coins", "label": "《致富心態》序言（大意）",
                   "quote": "理財成不成功，跟智商關係不大，跟行為關係很大。", "highlight": ["跟行為關係很大"], "size": 70,
                   "source": "出處：摩根．豪瑟《致富心態》"}
G["card_know_do"] = {"type": "compare", "bg": "ill_night_choice", "title": "知道 vs 做到",
                     "columns": [{"label": "大家都知道", "value": "6 個月", "size": 120, "sub": "緊急預備金\n每月存下一成薪水", "color": "blue"},
                                 {"label": "真正難的是", "value": "照著做", "size": 120, "sub": "朋友換新車、股市大漲的晚上\n你還願不願意", "color": "red", "hl": True}],
                     "ops": ["≠"]}
G["card_physics_psych"] = {"type": "compare", "bg": "ill_valet", "title": "我們學理財的方式，可能錯了",
                           "columns": [{"label": "像學物理", "value": "公式、定律", "size": 100, "sub": "以為照算就對", "color": "fade"},
                                       {"label": "其實更像學心理學", "value": "人性、情緒", "size": 100, "sub": "人在錢面前怎麼想", "color": "red", "hl": True}],
                           "ops": ["→"], "source": "出處：《致富心態》序言（大意）"}

# 第三部
G["q_experience"] = {"type": "pquote", "bg": "ill_two_families", "label": "《致富心態》第 1 章（大意）",
                     "quote": "你對金錢的親身經驗，只占世界上發生過的事的億分之一，卻決定了你八成的判斷。", "highlight": ["億分之一", "八成"], "size": 62,
                     "source": "出處：摩根．豪瑟《致富心態》"}
G["q_kennedy"] = {"type": "pquote", "bg": "ill_jfk_garden", "label": "甘迺迪談大蕭條 · 1960 年（大意）",
                  "quote": "我對大蕭條沒什麼親身經歷。我唯一記得的，是父親多請了幾個園丁，只為了給他們一份工作。", "highlight": ["多請了幾個園丁"], "size": 58,
                  "source": "出處：《致富心態》第 1 章引述"}
G["card_depression_babies"] = {"type": "pflow", "bg": "ill_two_families", "title": "年輕時經歷什麼，一輩子就怎麼投資",
                               "boxes": [{"text": "在高通膨\n年代長大", "sub": "一輩子少買債券", "color": "red"},
                                         {"text": "在股市大漲\n年代長大", "sub": "一輩子多買股票", "color": "green"},
                                         {"text": "決定風險胃口", "sub": "不是智商\n是出生年代", "color": "blue"}],
                               "source": "資料：Malmendier & Nagel〈Depression Babies〉NBER w14813；美國消費者財務調查 50 年資料"}
G["card_birth_luck"] = {"type": "pquote", "bg": "ill_two_families", "label": "「債券天王」比爾．格羅斯（2019，大意）",
                        "quote": "如果我早十年或晚十年出生，可能就不會有今天的成功。", "highlight": ["早十年或晚十年"], "size": 66,
                        "source": "出處：《致富心態》第 1 章引《金融時報》2019 年專訪"}
G["card_tw_1990"] = {"type": "ptimeline", "bg": "ill_tw_1990", "title": "台股加權指數：一個 30 年的輪迴",
                     "events": [{"date": "1990/2", "label": "12,682 點\n歷史高點", "color": "blue"},
                                {"date": "1990/10", "label": "2,485 點\n約 8 個月跌掉八成", "color": "red", "hl": True},
                                {"date": "2020/7/27", "label": "突破 12,682\n睽違 30 年", "color": "green"}],
                     "source": "資料：台灣證券交易所歷史資料；科技新報（中央社）2020/7/27"}
G["card_tw_cohort"] = {"type": "compare", "bg": "ill_two_taiwanese", "title": "兩個台灣人，25 歲那年",
                       "columns": [{"label": "1965 年出生", "value": "崩盤八成", "size": 100, "sub": "1990 年第一次投資\n之後 30 年沒回到起點", "color": "red"},
                                   {"label": "1995 年出生", "value": "歷史新高", "size": 100, "sub": "2020 年第一次投資\n之後幾年一路往上", "color": "green", "hl": True}],
                       "ops": ["vs"], "note": "誰都不笨，只是活在不同的世界", "source": "試想例子；台股數據見前頁"}
G["card_lottery"] = {"type": "compare", "bg": "ill_lottery", "title": "美國：誰在買彩券？",
                     "columns": [{"label": "最低收入家庭 · 每年買彩券", "value": "412 美元", "size": 110, "sub": "是高收入家庭的 4 倍", "color": "red", "hl": True},
                                 {"label": "臨時拿不出 400 美元現金的人", "value": "約 37%", "size": 120, "sub": "美國成年人", "color": "blue"}],
                     "source": "資料：《致富心態》第 1 章；美國聯準會家庭經濟調查（SHED，近年約 63% 可用現金支付）"}
G["q_no_crazy"] = {"type": "pquote", "bg": "ill_lottery_dream", "label": "第 1 章最重要的一句話",
                   "quote": "每個人在錢上做的決定，在他當下的處境裡，都有他的道理。", "highlight": ["都有他的道理"], "size": 68,
                   "note": "沒有人真的對錢失去理智", "source": "出處：《致富心態》第 1 章（大意）"}

# 第四部
G["card_ida"] = {"type": "compare", "bg": "ill_ida_check", "title": "艾達．梅．富勒的社會安全帳",
                 "columns": [{"label": "總共繳過的稅", "value": "24.75", "size": 130, "sub": "美元", "color": "fade"},
                             {"label": "活到 100 歲，總共領到", "value": "22,888", "size": 130, "sub": "美元（第一張支票 22.54）", "color": "green", "hl": True}],
                 "ops": ["→"], "source": "資料：美國社會安全局；Wikipedia: Ida May Fuller"}
G["card_retire_old"] = {"type": "compare", "bg": "ill_old_worker", "title": "「退休」其實是很新的概念",
                        "columns": [{"label": "二戰以前 · 65 歲以上男性", "value": "過半還在工作", "size": 92, "sub": "做到做不動為止", "color": "red"},
                                    {"label": "1975 年 · 65 歲以上", "value": "只有 1/4", "size": 110, "sub": "有退休金可領", "color": "blue", "hl": True}],
                        "source": "資料：《致富心態》第 1 章（引美國員工福利研究所 EBRI）"}
G["card_new_tools"] = {"type": "ptimeline", "bg": "ill_old_worker", "title": "美國：你熟悉的理財工具有多年輕",
                       "events": [{"date": "1940", "label": "第一張\n社安支票", "color": "fade"},
                                  {"date": "1976", "label": "第一檔\n指數基金", "color": "blue"},
                                  {"date": "1978", "label": "401(k)\n退休帳戶", "color": "green"},
                                  {"date": "1998", "label": "羅斯\n個人退休帳戶", "color": "amber"}],
                       "source": "資料：《致富心態》第 1 章；美國社會安全局；Vanguard"}
G["card_tw_tools"] = {"type": "ptimeline", "bg": "ill_habit", "title": "台灣：更年輕",
                      "events": [{"date": "2003", "label": "第一檔 ETF\n元大台灣50", "color": "blue", "hl": True},
                                 {"date": "2005", "label": "勞退新制上路\n每人一個帳戶", "color": "green", "hl": True}],
                      "source": "資料：臺灣證券交易所；勞動部（勞退新制 2005/7/1）"}
G["card_dog"] = {"type": "compare", "bg": "ill_dog_wolf", "title": "我們只是新手",
                 "columns": [{"label": "人類養狗", "value": "1 萬年", "size": 130, "sub": "狗還留著狼的習性", "color": "fade"},
                             {"label": "面對現代金融體系", "value": "20–50 年", "size": 120, "sub": "卻想一上場就完美", "color": "red", "hl": True}],
                 "ops": ["vs"], "source": "出處：《致富心態》第 1 章（大意）"}
G["card_steps"] = {"type": "plist", "bg": "ill_write_notes", "heading": "看完這一集，可以做的三件事",
                   "items": [["1", "寫下你的「金錢出廠設定」", "出生年、第一次投資遇到牛市還是熊市"],
                             ["2", "不嘲笑別人的決定，也不照抄"], ["3", "把對的事變成習慣，不靠意志力"]]}
G["card_read_formula"] = {"type": "pflow", "bg": "ill_habit", "title": "里德的「秘密」，其實沒有秘密",
                          "boxes": [{"text": "花得比\n賺得少", "sub": "省下每一分錢", "color": "blue"},
                                    {"text": "放進很多\n好公司", "sub": "今天：低成本指數基金", "color": "green"},
                                    {"text": "等上\n幾十年", "sub": "讓時間做事", "color": "red"}],
                          "source": "說明：個股有風險；一般人用低成本指數基金就能做到分散"}
G["card_summary"] = {"type": "plist", "bg": "ill_read_town2", "heading": "今天的三個重點",
                     "items": [["1", "理財靠行為，不靠智商"], ["2", "每個人的金錢觀，都來自他的經歷"], ["3", "理財這場遊戲很新，我們都是新手"]]}

json.dump(G, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(G), "cards")
