"""生成 03_画面素材/graphics.json：章节卡（黑底胶片 ftitle）、信息卡（graphics3 纸张卡）、网页截图卡。改卡片就改这里再运行。"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "03_画面素材/graphics.json")
G = {}

# ---------- 黑底胶片卡：开场观点、片名、四部、片尾 ----------
G["brand_intro"] = {"type": "ftitle", "label": "歡迎收看", "seed": 2, "size": 140, "text": "資產增長計劃",
                    "sub": "用一本好書，陪你一起看懂錢"}
G["hook_thesis"] = {"type": "ftitle", "label": "《致富心態》第二章", "seed": 3, "size": 96,
                    "text": "任何事，\n都沒有表面看起來那麼好，\n也沒有那麼糟。"}
G["title_main"] = {"type": "ftitle", "label": "致富心態 · 拆書", "seed": 5, "size": 150, "text": "運氣與風險",
                   "sub": "百萬分之一的好運，和百萬分之一的意外"}
G["part_1"] = {"type": "ftitle", "label": "第一部", "seed": 11, "text": "百萬分之一的運氣"}
G["part_2"] = {"type": "ftitle", "label": "第二部", "seed": 12, "text": "百萬分之一的風險"}
G["part_3"] = {"type": "ftitle", "label": "第三部", "seed": 13, "text": "大膽和魯莽，只差一毫米"}
G["part_4"] = {"type": "ftitle", "label": "第四部", "seed": 14, "text": "成功和失敗，\n都是糟糕的老師"}
G["end_card"] = {"type": "ftitle", "label": "如果這支影片對你有幫助", "seed": 15, "size": 130, "text": "訂閱，我們下次見"}

# ---------- 信息卡 ----------
G["card_two_sides"] = {"type": "compare", "bg": "ill_twins", "title": "同一種力量，兩個方向",
                       "columns": [{"label": "落在你這邊", "value": "運氣", "size": 150, "sub": "結果比努力應得的更好", "color": "green", "hl": True},
                                   {"label": "落在另一邊", "value": "風險", "size": 150, "sub": "結果比努力應得的更糟", "color": "red", "hl": True}]}
G["card_3000"] = {"type": "counter", "bg": "ill_rummage_sale", "label": "1968 年 · 家長會舊貨義賣的收入", "value": 3000,
                  "unit": "美元", "sub": "拿來租一台電傳打字機終端，連上奇異公司的大型電腦"}
G["card_funnel"] = {"type": "hbars", "bg": "ill_sea_students", "title": "1968 年，全世界的高中生",
                    "items": [{"label": "全世界", "value": 303000000, "text": "3 億 300 萬"},
                              {"label": "美國", "value": 18000000, "text": "1,800 萬"},
                              {"label": "華盛頓州", "value": 270000, "text": "27 萬"},
                              {"label": "西雅圖", "value": 100000, "text": "10 萬出頭"},
                              {"label": "湖濱中學", "value": 300, "text": "約 300 人", "color": "red"}],
                    "source": "資料：《致富心態》第 2 章（引聯合國統計）"}
G["card_million"] = {"type": "counter", "bg": "ill_lit_window", "label": "從 3 億，到", "value": 300, "unit": "人",
                     "sub": "全世界一百萬個學生裡，只有一個能進這種學校"}
G["q_lakeside"] = {"type": "pquote", "bg": "ill_terminal_room", "label": "比爾．蓋茲 · 2005 年湖濱中學演講",
                   "quote": "如果沒有湖濱，就不會有微軟。", "highlight": ["就不會有微軟"], "size": 84,
                   "source": "出處：蓋茲基金會網站演講全文（2005/9/23）"}
G["q_phone"] = {"type": "pquote", "bg": "ill_phone_bed", "label": "蓋茲 · 紀錄片《蓋茲之道》（2019）",
                "quote": "到現在我都還記得肯特的電話號碼：525-7851。", "highlight": ["525-7851"], "size": 70,
                "source": "出處：Netflix《Inside Bill's Brain》（《致富心態》第 2 章引述）"}
G["card_dreams"] = {"type": "plist", "bg": "ill_dreams", "heading": "兩個少年的計畫",
                    "items": [["1", "當執行長？"], ["2", "能有多大的影響力？"], ["3", "去當將軍？還是當大使？"],
                              ["4", "不管做什麼，都要一起做"]]}
G["q_together"] = {"type": "pquote", "bg": "ill_empty_desk", "label": "蓋茲回憶肯特（紀錄片）",
                   "quote": "我們本來會一起念書。我想，我們一定會一起上大學。", "highlight": ["一起上大學"], "size": 66,
                   "source": "出處：《致富心態》第 2 章引述"}
G["card_kent_time"] = {"type": "ptimeline", "bg": "ill_climb_class", "title": "肯特．伊凡斯",
                       "events": [{"date": "八年級", "label": "和蓋茲\n成為好友", "color": "blue"},
                                  {"date": "1971", "label": "一起寫\n排課程式", "color": "green"},
                                  {"date": "1972/5/28", "label": "登山課練習時\n墜落，17 歲", "color": "red", "hl": True}],
                       "source": "資料：維基百科 Paul Allen、Bill Gates 條目；Find a Grave"}
G["card_twin_odds"] = {"type": "compare", "bg": "ill_wheel", "title": "同樣是百萬分之一",
                       "columns": [{"label": "比爾．蓋茲", "value": "好運", "size": 140, "sub": "進了一所租得起電腦的學校", "color": "green", "hl": True},
                                   {"label": "肯特．伊凡斯", "value": "風險", "size": 140, "sub": "高中生登山喪命的機率", "color": "red", "hl": True}],
                       "source": "資料：《致富心態》第 2 章"}
G["card_7b"] = {"type": "counter", "bg": "ill_sea_students", "label": "這場遊戲裡，除了你，還有", "value": 70,
                "unit": "億人", "sub": "還有數不清的變數"}
G["q_shiller"] = {"type": "pquote", "bg": "web_shiller", "label": "羅伯．席勒 · 2013 諾貝爾經濟學獎",
                  "quote": "關於投資，我最想知道的是：成功的投資裡，運氣到底占了幾成。", "highlight": ["運氣到底占了幾成"],
                  "size": 62, "source": "出處：《致富心態》第 2 章（作者訪談）"}
G["card_why_silent"] = {"type": "compare", "bg": "ill_spotlight", "title": "為什麼我們很少談運氣？",
                        "columns": [{"label": "說別人靠運氣", "value": "像嫉妒", "size": 120, "sub": "聽起來刻薄", "color": "red"},
                                    {"label": "說自己靠運氣", "value": "很洩氣", "size": 120, "sub": "不想承認", "color": "blue"}]}
G["card_siblings"] = {"type": "hbars", "bg": "ill_brothers", "title": "兄弟之間有多像？（相關係數）",
                      "items": [{"label": "收入", "value": 0.5, "text": "約 0.5", "color": "red"},
                                {"label": "身高", "value": 0.5, "text": "約 0.5"},
                                {"label": "體重", "value": 0.3, "text": "約 0.3"}],
                      "source": "資料：Mazumder，芝加哥聯準會 2004；2011"}
G["card_80_20"] = {"type": "compare", "bg": "ill_flat_stock", "title": "一支股票，五年沒漲",
                   "columns": [{"label": "可能一", "value": "判斷錯了", "size": 100, "sub": "一開始就不該買", "color": "fade"},
                               {"label": "可能二", "value": "判斷對了", "size": 100, "sub": "八成會賺，只是碰上那兩成", "color": "blue", "hl": True}]}
G["card_blame"] = {"type": "compare", "bg": "ill_blame", "title": "我們的雙重標準",
                   "columns": [{"label": "別人失敗了", "value": "決策錯", "size": 120, "sub": "結果不好，一定是決定不好", "color": "red"},
                               {"label": "自己失敗了", "value": "運氣差", "size": 120, "sub": "我當時有很多理由", "color": "blue"}]}
G["card_coin"] = {"type": "compare", "bg": "ill_coin_toss", "title": "《富比士》封面只登一種人",
                  "columns": [{"label": "決定正確，運氣差", "value": "沒人報導", "size": 100, "sub": "", "color": "fade"},
                              {"label": "決定普通甚至魯莽，運氣好", "value": "登上封面", "size": 100, "sub": "", "color": "green", "hl": True}]}
G["q_vanderbilt"] = {"type": "pquote", "bg": "ill_vanderbilt_office", "label": "鐵路大亨范德比爾特（書中引述）",
                     "quote": "天哪，約翰，你不會以為，我們真能照紐約州的法律來經營鐵路吧？", "highlight": ["照紐約州的法律"], "size": 60,
                     "source": "出處：《致富心態》第 2 章引 A. T. Vanderbilt II《Fortune's Children》"}
G["card_same_act"] = {"type": "compare", "bg": "ill_courtroom", "title": "同樣挑戰法律底線",
                      "columns": [{"label": "范德比爾特（成功）", "value": "叫氣魄", "size": 120, "sub": "美國史上最有錢的人之一", "color": "green"},
                                  {"label": "安隆（2001 倒閉）", "value": "叫犯罪", "size": 120, "sub": "人人唾棄", "color": "red"}]}
G["card_graham"] = {"type": "compare", "bg": "ill_graham_desk", "title": "葛拉漢自己的規矩，和他最賺的一筆",
                    "columns": [{"label": "平常，任何一檔股票", "value": "≤ 5%", "size": 130, "sub": "分散投資", "color": "blue"},
                                {"label": "1948 年，蓋可保險", "value": "約 25%", "size": 130, "sub": "公司四分之一的資金", "color": "red", "hl": True}]}
G["card_geico"] = {"type": "ptimeline", "bg": "web_geico", "title": "葛拉漢與蓋可保險",
                   "events": [{"date": "1948", "label": "71 萬美元\n買下一半股份", "color": "blue"},
                              {"date": "1972", "label": "約 4 億美元", "color": "green", "hl": True},
                              {"date": "結果", "label": "比二十年來其他投資\n加起來還多", "color": "amber"}],
                   "source": "資料：《智慧型股票投資人》後記；IFA、Gurufocus 整理"}
G["q_graham"] = {"type": "pquote", "bg": "web_graham", "label": "班傑明．葛拉漢《智慧型股票投資人》後記",
                 "quote": "一次幸運的機會，還是一個極其精明的決定，我們分得清嗎？", "highlight": ["我們分得清嗎"], "size": 66,
                 "source": "出處：The Intelligent Investor（1973 年版後記，節譯）"}
G["card_yahoo"] = {"type": "ptimeline", "bg": "ill_rejected_bid", "title": "拒絕收購：一個叫遠見，一個叫傻",
                   "events": [{"date": "2006", "label": "雅虎出 10 億\n祖克柏拒絕", "color": "green"},
                              {"date": "2008", "label": "微軟出 446 億\n雅虎拒絕", "color": "red"},
                              {"date": "2017", "label": "雅虎核心業務\n只賣 44.8 億", "color": "red", "hl": True}],
                   "source": "資料：微軟新聞稿（SEC，2008/2/1）；Verizon 2017"}
G["card_mm"] = {"type": "compare", "bg": "ill_tightrope", "title": "只差一毫米，而且事後才知道",
                "columns": [{"label": "結果好", "value": "大膽", "size": 150, "sub": "", "color": "green"},
                            {"label": "結果壞", "value": "魯莽", "size": 150, "sub": "", "color": "red"}]}
G["card_lessons"] = {"type": "plist", "bg": "ill_letter_son", "heading": "作者給的兩個方向",
                     "items": [["1", "讚美、看不起一個人，都要小心"],
                               ["2", "少研究極端個案，多找普遍規律"]]}
G["q_letter"] = {"type": "pquote", "bg": "ill_letter_son", "label": "作者寫給兒子的信（節錄）",
                 "quote": "不是所有成功都來自努力，也不是所有貧窮都因為懶惰。", "highlight": ["不是所有成功都來自努力"], "size": 66,
                 "source": "出處：《致富心態》第 2 章"}
G["q_gates_teacher"] = {"type": "pquote", "bg": "ill_pedestal", "label": "比爾．蓋茲《擁抱未來》（1995）",
                        "quote": "成功是個很糟糕的老師，它會讓聰明人以為自己不會失敗。", "highlight": ["很糟糕的老師"], "size": 66,
                        "source": "出處：The Road Ahead（1995）"}
G["card_plan"] = {"type": "pflow", "bg": "ill_safety_net", "title": "與其祈求每次都對",
                  "boxes": [{"text": "留出\n安全空間", "sub": "一次失敗不至於全盤崩潰", "color": "blue"},
                            {"text": "留在場上", "sub": "不被迫退出", "color": "green"},
                            {"text": "等好運來", "sub": "時間站在你這邊", "color": "red"}]}
G["card_summary"] = {"type": "plist", "bg": "ill_wait_rain", "heading": "今天的三個重點",
                     "items": [["1", "運氣和風險是雙胞胎"],
                               ["2", "大膽和魯莽只差一毫米"],
                               ["3", "撐得過壞運氣，才等得到好運氣"]]}

# ---------- 网页截图卡 ----------


def web(sid, title, source, url, bg, fx=0.5):
    G[sid] = {"type": "web", "img": sid + ".png", "title": title, "source": source, "url_label": url,
              "bg": bg, "focus_x": fx, "zoom": 0.08}


web("shot_gates_speech", "蓋茲 2005 年湖濱中學演講", "蓋茲基金會", "gatesfoundation.org/ideas/speeches/2005/09/bill-gates-lakeside-school", "ill_terminal_room")
web("shot_gates_speech2", "「如果沒有湖濱，就不會有微軟」", "蓋茲基金會", "gatesfoundation.org/ideas/speeches/2005/09/bill-gates-lakeside-school", "ill_terminal_room", 0.45)
web("shot_nobel_shiller", "羅伯．席勒，2013 年諾貝爾經濟學獎", "NobelPrize.org", "nobelprize.org/prizes/economic-sciences/2013/shiller/facts", "ill_spotlight")
web("shot_wiki_vanderbilt", "康內留斯．范德比爾特（1794–1877）", "Wikipedia", "en.wikipedia.org/wiki/Cornelius_Vanderbilt", "ill_railroad_build")
web("shot_wiki_enron", "安隆醜聞（2001）", "Wikipedia", "en.wikipedia.org/wiki/Enron_scandal", "ill_enron_boxes")
web("shot_wiki_graham", "班傑明．葛拉漢：價值投資之父", "Wikipedia", "en.wikipedia.org/wiki/Benjamin_Graham", "ill_graham_desk")
web("shot_sec_yahoo", "2008/2/1 微軟提議以 446 億美元收購雅虎", "微軟新聞稿（SEC 文件）", "sec.gov — Microsoft Proposes Acquisition of Yahoo! for $31 per Share", "ill_rejected_bid", 0.3)
web("shot_zuck_yahoo", "祖克柏：拒絕雅虎 10 億後，董事會想開除我", "Yahoo Finance／Moneywise 2025", "finance.yahoo.com — Mark Zuckerberg says Facebook's board 'tried to fire' him", "ill_boardroom_2006", 0.3)

if __name__ == "__main__":
    json.dump(G, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(G), "张卡 →", OUT)
