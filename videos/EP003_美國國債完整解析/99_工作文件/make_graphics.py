"""生成 EP003 的 graphics.json（数据来自财政部 / FRED，运行时在线取数）。"""
import csv
import json
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "03_画面素材/graphics.json")
G = {}


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read().decode()


# ---------- 财政部 2026 年殖利率 ----------
TR = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all"
      "?type=daily_treasury_yield_curve&field_tdr_date_value=2026&page&_format=csv")
rows = [r for r in csv.DictReader(get(TR).splitlines()) if r["10 Yr"]][::-1]  # 旧 → 新
xs = list(range(len(rows)))
ys = [float(r["10 Yr"]) for r in rows]
months = {}
for i, r in enumerate(rows):
    m = int(r["Date"][:2])
    months.setdefault(m, i)
fed_i = next(i for i, r in enumerate(rows) if r["Date"] == "09/16/2026")
assert rows[0]["Date"] == "01/02/2026" and rows[-1]["Date"] == "10/09/2026", (rows[0]["Date"], rows[-1]["Date"])
SRC_TR = "資料：美國財政部「每日國債殖利率曲線」（Daily Treasury Par Yield Curve Rates）"
G["ch_10y_year"] = {
    "type": "line", "bg": "sc_vault_door", "title": "十年期美債殖利率（2026 年）",
    "series": [{"x": xs, "y": ys, "color": "blue", "width": 6, "fill": True}],
    "ylim": [3.8, 5.5], "yticks": [4.0, 4.5, 5.0], "yfmt": "{:.1f}%",
    "xticks": [[i, f"{m}月"] for m, i in sorted(months.items())],
    "annot": [
        {"x": 0, "y": ys[0], "text": "1月2日\n4.19%", "dx": 130, "dy": -90, "color": "ink", "anchor": "c"},
        {"x": fed_i, "y": ys[fed_i], "text": "9月16日\n聯準會升息 1 碼", "dx": -40, "dy": 120, "color": "red"},
        {"x": xs[-1], "y": ys[-1], "text": "10月9日\n5.24%", "dx": -20, "dy": -90, "color": "red", "anchor": "c", "glow": True},
    ],
    "source": SRC_TR,
}

# ---------- 十年期殖利率长期 ----------
FR = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10&cosd=1962-01-01"
import datetime as dt  # noqa: E402

hist = []
for r in list(csv.reader(get(FR).splitlines()))[1:]:
    if r[1] in ("", "."):
        continue
    d = dt.date.fromisoformat(r[0])
    hist.append((d.year + (d.timetuple().tm_yday - 1) / 366, float(r[1]), r[0]))
keep = {i for i in range(0, len(hist), 6)} | {len(hist) - 1}
peak = max(hist, key=lambda h: h[1])
low20 = min((h for h in hist if h[2].startswith("2020")), key=lambda h: h[1])
keep |= {hist.index(peak), hist.index(low20)}
pts = [hist[i] for i in sorted(keep)]
assert peak[2] == "1981-09-30" and abs(peak[1] - 15.84) < 1e-6, peak
assert low20[2] == "2020-08-04" and abs(low20[1] - 0.52) < 1e-6, low20
G["ch_10y_history"] = {
    "type": "line", "bg": "sc_stair_steps", "title": "十年期美債殖利率：六十年的軌跡",
    "series": [{"x": [p[0] for p in pts], "y": [p[1] for p in pts], "color": "blue", "width": 5},
               {"x": [1990.0, 2007.0], "y": [5.86, 5.86], "color": "green", "width": 7}],
    "xlim": [1962, 2027], "ylim": [0, 17], "yticks": [0, 5, 10, 15], "yfmt": "{:.0f}%",
    "xticks": [[y, str(y)] for y in range(1970, 2030, 10)], "draw": 4.2,
    "annot": [
        {"x": peak[0], "y": peak[1], "text": "1981年9月\n15.84%", "dx": -200, "dy": 30, "color": "red"},
        {"x": 2000.0, "y": 5.86, "text": "1990–2006 平均 5.86%", "dx": 0, "dy": -140, "color": "green", "size": 34, "leader": False},
        {"x": low20[0], "y": low20[1], "text": "2020年8月\n0.52%", "dx": -20, "dy": -110, "color": "ink"},
        {"x": hist[-1][0], "y": hist[-1][1], "text": "今天\n5.24%", "dx": 0, "dy": -100, "color": "red", "glow": True},
    ],
    "source": "資料：聖路易聯邦準備銀行 FRED（DGS10，日資料）",
}

# ---------- 数据卡 ----------
G["card_open_loss"] = {
    "type": "compare", "bg": "sc_vault_door", "title": "「最安全的資產」今年的帳面損益",
    "columns": [
        {"label": "1月2日買進十年期", "value": "−7.5%", "color": "red", "hl": True, "sub": "殖利率 4.19% → 5.24%"},
        {"label": "1月2日買進三十年期", "value": "−10.5%", "color": "red", "hl": True, "sub": "殖利率 4.86% → 5.60%"}],
    "source": "估算：依債券定價公式，假設以票面價買進；殖利率資料：美國財政部（2026-10-09）",
}
G["card_debt_counter"] = {
    "type": "counter", "bg": "sc_ledger_desk", "title": "美國聯邦債務總額", "label": "2026年10月8日",
    "value": 40.3, "decimals": 1, "unit": "兆美元", "sub": "8月18日第一次站上 40 兆美元",
    "source": "資料：美國財政部 Debt to the Penny（Total Public Debt Outstanding）",
}
G["card_agenda"] = {
    "type": "plist", "bg": "sc_ledger_desk", "heading": "這支影片要講清楚的 7 件事",
    "items": [["1", "國債到底是什麼"], ["2", "有哪五種"], ["3", "怎麼賣出去"], ["4", "價格為什麼跟利率反著走"],
              ["5", "誰在持有、利息有多驚人"], ["6", "真正的風險在哪裡"], ["7", "普通人怎麼用"]],
}
G["card_71_29"] = {
    "type": "stack", "bg": "web_treasury", "headline": "每花 1 美元",
    "parts": [{"value": 71, "text": "71 美分", "label": "是收來的", "color": "blue"},
              {"value": 29, "text": "29 美分", "label": "要靠借", "color": "red", "hl": True}],
    "note": "2026 財年前 11 個月：收入 4.85 兆，支出 6.81 兆（美元）",
    "source": "資料：美國財政部 Monthly Treasury Statement（2026 年 8 月）",
}
G["card_deficit_debt"] = {
    "type": "pflow", "bg": "sc_ledger_desk", "title": "赤字 ≠ 債務",
    "boxes": [{"text": "這一年的缺口\n＝ 赤字", "sub": "前 11 個月約 1.97 兆", "color": "red"},
              {"text": "年年累加", "sub": "過去每一年的缺口", "color": "amber"},
              {"text": "帳單總額\n＝ 債務", "sub": "40.3 兆美元", "color": "blue"}],
    "note": "信用卡：這個月多刷多少是赤字，帳單共欠多少才是債務", "ny": 650,
    "source": "資料：美國財政部",
}
G["card_debt_split"] = {
    "type": "stack", "bg": "web_treasury", "headline": "總債務 40.3 兆美元（2026-10-08）",
    "parts": [{"value": 32.45, "text": "32.5 兆", "label": "公眾持有（市場上的投資人）", "color": "blue"},
              {"value": 7.85, "text": "7.9 兆", "label": "政府內部持有\n（如社會安全信託基金）", "color": "green"}],
    "source": "資料：美國財政部 Debt to the Penny（Debt Held by the Public / Intragovernmental Holdings）",
}
hist_debt = [("2000", 5.674), ("2008", 10.025), ("2019", 22.719), ("2020", 26.945), ("2023", 33.167), ("2024", 35.465),
             ("2025", 37.638), ("2026", 40.172)]
G["ch_debt_history"] = {
    "type": "bars", "bg": "sc_stair_steps", "title": "美國聯邦債務總額", "unit": "兆美元（各年 9 月底）",
    "items": [{"label": y, "value": v, "text": f"{v:.1f}"} for y, v in hist_debt], "hl": [7], "vmax": 44,
    "source": "資料：美國財政部 Debt to the Penny",
}
G["ch_marketable"] = {
    "type": "stack", "bg": "web_treasury", "headline": "可流通國債 31.8 兆美元（2026 年 9 月底）",
    "parts": [{"value": 7.118, "text": "7.1 兆", "label": "國庫券 22%", "color": "green"},
              {"value": 16.282, "text": "16.3 兆", "label": "中期債 51%", "color": "blue"},
              {"value": 5.551, "text": "5.6 兆", "label": "長期債 17%", "color": "amber"},
              {"value": 2.173, "text": "2.2 兆", "label": "TIPS 7%", "color": "red"},
              {"value": 0.708, "text": "0.7 兆", "label": "浮動利率 2%", "color": "fade"}],
    "source": "資料：美國財政部 Monthly Statement of the Public Debt（MSPD），2026-09-30",
}
G["card_bill_example"] = {
    "type": "pflow", "bg": "sc_hourglass", "title": "國庫券：折價買進，到期領回面額",
    "boxes": [{"text": "買進\n979 美元", "sub": "面額 1,000 美元的半年期", "color": "blue"},
              {"text": "持有 6 個月", "sub": "沒有票面利息", "color": "amber"},
              {"text": "領回\n1,000 美元", "sub": "多出的 21 美元就是利息", "color": "green"}],
    "note": "以半年期國庫券殖利率約 4.3% 估算", "ny": 650, "source": "示意：殖利率 4.32%（2026-10-09 六個月期）",
}
G["card_maturities"] = {
    "type": "ptimeline", "bg": "sc_hourglass", "title": "借多久：三種主要期限",
    "events": [{"date": "4–52 週", "label": "國庫券\n7.1 兆", "color": "green"},
               {"date": "2–10 年", "label": "中期債\n16.3 兆", "color": "blue"},
               {"date": "20–30 年", "label": "長期債\n5.6 兆", "color": "amber"}],
    "source": "資料：TreasuryDirect；MSPD 2026-09-30",
}
G["card_five_types"] = {
    "type": "plist", "bg": "sc_hourglass", "heading": "國債的五種長相",
    "items": [["1", "國庫券 Bills", "一年內 · 折價賣"], ["2", "中期債 Notes", "2–10 年 · 半年付息"],
              ["3", "長期債 Bonds", "20–30 年 · 半年付息"], ["4", "抗通膨債 TIPS", "本金隨物價調整"],
              ["5", "浮動利率債 FRN", "2 年 · 利率跟國庫券"]],
    "source": "資料：TreasuryDirect",
}
G["card_coupon_yield"] = {
    "type": "compare", "bg": "sc_hourglass", "title": "票面利率 ≠ 殖利率",
    "columns": [{"label": "票面利率", "value": "固定", "color": "blue", "sub": "印在債券上\n發行之後不再變"},
                {"label": "殖利率", "value": "會變", "color": "red", "hl": True, "sub": "用今天市價買進\n實際的年化報酬"}],
    "ops": ["≠"],
}
G["card_auction_aug"] = {
    "type": "hbars", "bg": "sc_trading_hall", "title": "2026 年 8 月季度再融資：合計 1,250 億美元",
    "items": [{"label": "3 年期", "value": 58, "text": "580 億"}, {"label": "10 年期", "value": 42, "text": "420 億", "color": "red"},
              {"label": "30 年期", "value": 25, "text": "250 億"}], "vmax": 62, "hl": [1],
    "source": "資料：美國財政部季度再融資公告（2026-08-05）",
}
G["card_auction_steps"] = {
    "type": "pflow", "bg": "sc_trading_hall", "title": "單一價格拍賣",
    "boxes": [{"text": "各家報價\n殖利率＋金額", "color": "blue"}, {"text": "由低往高收\n直到賣完", "color": "amber"},
              {"text": "同一個得標\n殖利率成交", "color": "red"}],
    "note": "個人在 TreasuryDirect 只能「非競爭性投標」：100 美元到 1,000 萬美元", "ny": 650,
    "source": "資料：TreasuryDirect 拍賣說明（單一價格拍賣自 1998 年 11 月起）",
}
G["card_seesaw_calc"] = {
    "type": "compare", "bg": "sc_seesaw_dusk", "title": "利率升，債價跌：一個算給你看",
    "columns": [{"label": "你的舊債（票面 4%）", "value": "100 美元", "color": "blue"},
                {"label": "市場新債利率升到", "value": "5%", "color": "amber"},
                {"label": "舊債價格降到", "value": "92.2 美元", "color": "red", "hl": True, "sub": "下跌約 7.8%"}],
    "ops": ["→", "→"], "source": "十年期、半年付息債券，持有到期總報酬追上 5% 的價格",
}
G["ch_duration"] = {
    "type": "bars", "bg": "sc_seesaw_dusk", "title": "利率上升 1 個百分點，債價大約下跌",
    "items": [{"label": "2 年期", "value": -1.9, "text": "−1.9%", "color": "blue"},
              {"label": "10 年期", "value": -7.8, "text": "−7.8%", "color": "amber"},
              {"label": "30 年期", "value": -15.5, "text": "−15.5%", "color": "red"}],
    "hl": [2], "vmin": -17, "source": "估算：票面利率 4%、殖利率 4% → 5% 的債券",
}
G["ch_loss_cases"] = {
    "type": "bars", "bg": "sc_seesaw_dusk", "title": "真實案例：買進後到今天的帳面損益",
    "items": [{"label": "2 年期\n1月2日買", "value": -1.3, "text": "−1.3%", "color": "blue"},
              {"label": "10 年期\n1月2日買", "value": -7.5, "text": "−7.5%", "color": "amber"},
              {"label": "30 年期\n1月2日買", "value": -10.5, "text": "−10.5%", "color": "amber"},
              {"label": "10 年期\n2020年8月買", "value": -16.3, "text": "−16.3%", "color": "red"}],
    "hl": [3], "vmin": -19, "source": "估算：依債券定價公式；殖利率資料：美國財政部。持有到期不會有這筆損失",
}
G["card_hold_rule"] = {
    "type": "compare", "bg": "sc_hourglass", "title": "持有多久，決定利率上升對你是好是壞",
    "columns": [{"label": "持有時間 < 存續期間", "value": "吃虧", "color": "red", "sub": "價格下跌的損失\n大於再投資的增益"},
                {"label": "持有時間 ≥ 存續期間", "value": "大致抵銷", "color": "green", "hl": True, "sub": "再投資賺的利息\n追得上價格下跌"}],
    "ops": ["VS"],
}
G["ch_curve"] = {
    "type": "curve", "bg": "sc_vault_door", "title": "殖利率曲線：1月2日 vs 10月9日",
    "cats": ["3個月", "6個月", "1年", "2年", "5年", "10年", "30年"],
    "series": [{"name": "1月2日", "color": "blue", "above": False, "values": [3.65, 3.58, 3.47, 3.47, 3.74, 4.19, 4.86]},
               {"name": "10月9日", "color": "red", "above": True, "values": [4.25, 4.32, 4.47, 4.80, 5.02, 5.24, 5.60]}],
    "ylim": [3.0, 6.0], "yticks": [3, 4, 5, 6], "source": SRC_TR,
}
G["card_term_premium"] = {
    "type": "bars", "bg": "sc_vault_door", "title": "十年期「期限溢價」：多要求的補償", "unit": "金—賴特模型估計",
    "items": [{"label": "1月初", "value": 0.58, "text": "0.58%", "color": "blue"},
              {"label": "10月初", "value": 1.08, "text": "1.08%", "color": "red"}],
    "hl": [1], "vmax": 1.3, "source": "資料：聖路易聯邦準備銀行 FRED（THREEFYTP10，Kim-Wright 模型）",
}
G["card_oil_cpi"] = {
    "type": "compare", "bg": "sc_rain_window", "title": "推高利率的三個數字",
    "columns": [{"label": "WTI 原油（美元/桶）", "value": "57 → 96", "color": "amber", "sub": "1月2日 → 10月6日\n4月7日一度 114"},
                {"label": "8月消費者物價", "value": "+3.4%", "color": "red", "hl": True, "sub": "年增率"},
                {"label": "聯邦基金利率", "value": "3.75–4%", "color": "blue", "sub": "9月16日調升 1 碼"}],
    "source": "資料：聖路易聯儲 FRED（DCOILWTICO、CPIAUCNS）；聯準會",
}
G["card_fed_statement"] = {
    "type": "pquote", "bg": "web_fed", "label": "聯準會 FOMC 聲明 · 2026年9月16日",
    "quote": "通膨仍然偏高。今天的政策行動，將有助於更及時地回到委員會 2% 的目標。",
    "highlight": ["通膨仍然偏高"], "size": 64, "note": "12 比 0 一致通過 · 目標區間 3.50–3.75% → 3.75–4.00%",
    "source": "出處：聯準會新聞稿，2026-09-16（節譯）",
}
G["ch_real_nominal"] = {
    "type": "stack", "bg": "sc_rain_window", "headline": "十年期殖利率今年上升 1.05 個百分點",
    "parts": [{"value": 0.97, "text": "+0.97", "label": "實質殖利率（TIPS）\n1.94% → 2.91%", "color": "blue", "hl": True},
              {"value": 0.08, "text": "+0.08", "label": "市場預期通膨", "color": "amber"}],
    "note": "名目 4.19% → 5.24%", "source": "資料：美國財政部名目與實質殖利率曲線（2026-01-02、2026-10-09）",
}
G["ch_holders_foreign"] = {
    "type": "hbars", "bg": "web_taipei", "title": "部分外國持有人（2026 年 7 月，兆美元）",
    "items": [{"label": "日本", "value": 1.104, "text": "1.10"}, {"label": "英國", "value": 0.998, "text": "1.00"},
              {"label": "中國大陸", "value": 0.618, "text": "0.62"}, {"label": "加拿大", "value": 0.426, "text": "0.43"},
              {"label": "台灣", "value": 0.296, "text": "0.30", "color": "red"}], "hl": [4], "vmax": 1.25,
    "source": "資料：美國財政部 TIC（外國合計 9.25 兆）。英國數字含替各國客戶保管的機構",
}
G["ch_who_holds"] = {
    "type": "stack", "bg": "web_fed", "headline": "公眾持有的 32.5 兆國債，誰拿著？",
    "parts": [{"value": 4.57, "text": "14%", "label": "聯準會\n4.57 兆", "color": "green"},
              {"value": 9.25, "text": "28%", "label": "外國人\n9.25 兆", "color": "blue"},
              {"value": 18.63, "text": "57%", "label": "美國其他投資人\n約 18.6 兆", "color": "amber"}],
    "source": "資料：聯準會（2026-10-07）、財政部 TIC（2026-07）、Debt to the Penny（2026-10-08）；比例為估算",
}
G["ch_interest_vs"] = {
    "type": "hbars", "bg": "web_treasury", "title": "2026 財年前 11 個月：聯邦支出（兆美元）",
    "items": [{"label": "社會安全", "value": 1.526, "text": "1.53"}, {"label": "淨利息", "value": 1.017, "text": "1.02", "color": "red"},
              {"label": "醫療保險 Medicare", "value": 0.979, "text": "0.98"}, {"label": "國防", "value": 0.876, "text": "0.88"}],
    "hl": [1], "vmax": 1.75, "source": "資料：美國財政部 Monthly Treasury Statement（2026 年 8 月，Table 9）",
}
G["card_interest_share"] = {
    "type": "compare", "bg": "web_treasury", "title": "利息占了多大一塊",
    "columns": [{"label": "利息占稅收", "value": "21%", "color": "red", "hl": True, "sub": "每收 5 塊錢的稅\n約 1 塊先付利息"},
                {"label": "利息占赤字", "value": "52%", "color": "red", "hl": True, "sub": "超過一半的赤字\n是在為舊債付利息"}],
    "source": "計算：淨利息 1.017 兆 ÷ 收入 4.845 兆、赤字 1.966 兆（財政部月報，2026 財年前 11 個月）",
}
G["ch_interest_trend"] = {
    "type": "bars", "bg": "web_treasury", "title": "公眾持有債務的利息費用", "unit": "兆美元（財政年度）",
    "items": [{"label": "2021", "value": 0.389, "text": "0.39"}, {"label": "2024", "value": 0.896, "text": "0.90"},
              {"label": "2025", "value": 0.974, "text": "0.97"}, {"label": "2026", "value": 1.069, "text": "1.07"}],
    "hl": [3], "vmax": 1.25, "source": "資料：美國財政部 Interest Expense on the Public Debt Outstanding",
}
G["ch_avg_rate"] = {
    "type": "bars", "bg": "sc_dam_water", "title": "國債的平均利率正在爬升", "unit": "可流通國債平均利率",
    "items": [{"label": "2021年9月", "value": 1.47, "text": "1.47%"}, {"label": "2025年9月", "value": 3.41, "text": "3.41%"},
              {"label": "2026年2月", "value": 3.36, "text": "3.36%"}, {"label": "2026年9月", "value": 3.52, "text": "3.52%", "color": "amber"},
              {"label": "最新十年期", "value": 5.24, "text": "5.24%", "color": "red"}], "hl": [4], "vmax": 6,
    "source": "資料：美國財政部 Average Interest Rates on U.S. Treasury Securities；殖利率曲線（2026-10-09）",
}
G["card_debt_limit"] = {
    "type": "hbars", "bg": "web_capitol", "title": "債務上限：還剩多少空間",
    "items": [{"label": "調高前的上限", "value": 36.1, "text": "36.1 兆", "color": "fade"},
              {"label": "現在總債務", "value": 40.3, "text": "40.3 兆", "color": "red"}],
    "hl": [1], "vmax": 43, "limit": 41.1, "inside": True, "limit_label": "2025年7月調高後的上限 41.1 兆",
    "source": "資料：Debt to the Penny；OBBBA 法案（2025-07-04 簽署）",
}
G["card_ratings"] = {
    "type": "ptimeline", "bg": "web_capitol", "title": "三大評級機構，都不再給美國最高評級",
    "events": [{"date": "2011.08", "label": "標普\n三A → AA+", "color": "blue"},
               {"date": "2023.08", "label": "惠譽\nAAA → AA+", "color": "amber"},
               {"date": "2025.05", "label": "穆迪\nAaa → Aa1", "color": "red", "hl": True}],
    "source": "資料：S&P、Fitch、Moody's 公告",
}
G["card_real_return"] = {
    "type": "compare", "bg": "sc_storm_harbor", "title": "名目利息，扣掉通膨之後",
    "columns": [{"label": "三個月期國債殖利率", "value": "4.25%", "color": "blue"},
                {"label": "8月通膨（年增）", "value": "3.4%", "color": "amber"},
                {"label": "實質報酬", "value": "約 0.85%", "color": "red", "hl": True}],
    "ops": ["−", "＝"], "source": "資料：美國財政部（2026-10-09）；CPI 8月（NSA）",
}
G["card_rollover"] = {
    "type": "stack", "bg": "sc_storm_harbor", "headline": "國庫券：一年內就要換新",
    "parts": [{"value": 7.118, "text": "22%", "label": "國庫券\n7.1 兆", "color": "red", "hl": True},
              {"value": 24.717, "text": "78%", "label": "其他可流通國債\n24.7 兆", "color": "blue"}],
    "note": "到期就要再借；利率越高，成本傳導得越快", "source": "資料：MSPD 2026-09-30",
}
G["card_earnings_yield"] = {
    "type": "compare", "bg": "sc_hourglass", "title": "無風險利率是所有資產的地板",
    "columns": [{"label": "本益比 25 倍的股票", "value": "4%", "color": "blue", "sub": "盈餘殖利率 = 1 ÷ 25\n價格會上下波動"},
                {"label": "十年期美國國債", "value": "5.24%", "color": "red", "hl": True, "sub": "固定利息\n持有到期還本"}],
    "ops": ["VS"], "source": "示意；國債殖利率：美國財政部（2026-10-09）",
}
G["ch_horizon"] = {
    "type": "compare", "bg": "sc_stair_steps", "title": "把期限對上「用錢的時間」",
    "columns": [{"label": "1–3 年內要用", "value": "國庫券", "color": "green", "sub": "短年期\n波動小"},
                {"label": "3–10 年才用", "value": "中期債", "color": "blue", "sub": "階梯式配置\n每年都有一筆到期"},
                {"label": "10 年以上用不到", "value": "長期債", "color": "amber", "sub": "承受得了\n價格波動"}],
    "ops": ["→", "→"],
}
G["card_tips_breakeven"] = {
    "type": "compare", "bg": "sc_hourglass", "title": "TIPS 與一般國債：盈虧平衡的通膨",
    "columns": [{"label": "一般十年期殖利率", "value": "5.24%", "color": "blue"},
                {"label": "十年期 TIPS 實質殖利率", "value": "2.91%", "color": "green"},
                {"label": "市場隱含通膨預期", "value": "2.33%", "color": "red", "hl": True, "sub": "未來十年平均通膨高過它\nTIPS 就比較划算"}],
    "ops": ["−", "＝"], "source": "資料：美國財政部名目與實質殖利率曲線（2026-10-09）",
}
G["card_fx_example"] = {
    "type": "compare", "bg": "sc_taipei_desk", "title": "匯率會改變最後的報酬（示意）",
    "columns": [{"label": "美債殖利率", "value": "+4.5%", "color": "blue"},
                {"label": "新台幣升值 5%", "value": "−5%", "color": "red", "sub": "美元換回的新台幣變少"},
                {"label": "換回新台幣", "value": "約 −0.5%", "color": "red", "hl": True}],
    "ops": ["＋", "＝"], "source": "假設性示意，非預測",
}
G["card_summary"] = {
    "type": "plist", "bg": "sc_ledger_desk", "heading": "帶走這五件事",
    "items": [["1", "國債是政府的借據：每花 1 美元，29 美分靠借"], ["2", "五種國債，利率由拍賣「喊」出來"],
              ["3", "利率升，債價跌；期限越長，跌得越多"], ["4", "利息已超過國防：每 5 塊稅，約 1 塊付利息"],
              ["5", "重點是把期限，對上你用錢的時間"]],
}
G["brand_intro"] = {"type": "brand", "bg": "web_taipei", "text": "資產增長計劃", "sub": "EP003｜美國國債完整解析"}
G["end_card"] = {"type": "endcard", "bg": "web_taipei"}

json.dump(G, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(G), "張卡片 →", OUT)
