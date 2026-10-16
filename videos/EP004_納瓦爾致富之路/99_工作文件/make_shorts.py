"""EP004 的 3 条独立 Shorts（频道主 10/16：不从长视频截取，每条是完整的短片，有自己的文案和配音）。
结构：钩子（第一句就是最震撼的事实）→ 是什么 → 2～3 个硬数字 → 反转 → 结尾抛问题。"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
EP = os.path.dirname(HERE)

SHORTS = {
 "S01": {
  "hook": ["600萬股被算成零", "兩年後公司賣了6.2億美元"], "flash": ["股份＝0"],
  "paras": [
   ("p01", "四位創辦人，手上超過600萬股，在公司合併的時候，被算成零。", ["ill_shares_zero"]),
   ("p02", "這是矽谷投資人納瓦爾的真實經歷。1999年，他和夥伴創辦評論網站Epinions，拿了頂級創投的錢。2003年公司合併，他們被告知，公司只值兩三千萬美元。", ["ill_dotcom"]),
   ("p03", "問題出在清算優先權：公司賣掉時，創投的特別股先拿回錢，剩下的才輪到普通股。賣價不夠高，創辦人就什麼都沒有。", ["ill_court"]),
   ("p04", "諷刺的是，兩年後，eBay用6.2億美元，買下了這家公司。納瓦爾提告，最後和解，卻被說職業生涯完了。", ["v_ebay"]),
   ("p05", "他沒有離開，反而把這次的教訓，寫成教創業者談判的部落格，後來做出了AngelList。如果是你，你會告自己的投資人嗎？", ["ill_network"]),
  ],
  "visuals": {
   "ill_shares_zero": {"img": "ill_shares_zero", "fx": 0.45, "zoom": "in"},
   "ill_dotcom": {"img": "ill_dotcom", "fx": 0.5, "zoom": "out"},
   "ill_court": {"img": "ill_court", "fx": 0.3, "zoom": "in"},
   "v_ebay": {"card": "bars", "title": "同一家公司，相隔兩年",
              "bars": [{"label": "2003 被告知", "value": 0.38, "color": "gray", "fmt": "≤ {:.2f} 億美元", "final": "≤ 0.38 億美元", "delay": 0.3},
                       {"label": "2005 eBay 收購", "value": 6.2, "color": "r", "fmt": "{:.1f} 億美元", "final": "6.2 億美元", "delay": 1.0}],
              "note": "創辦人的普通股：被算成 0", "note_at": 2.6, "source": "資料：訴訟內容（NYT 2005）；eBay 新聞稿（SEC 2005/6/1）"},
   "ill_network": {"img": "ill_network", "fx": 0.55, "zoom": "in"},
  },
 },
 "S02": {
  "hook": ["靠上班很難變有錢？", "矽谷天使：你要擁有股權"], "flash": ["一天只有", "24 小時"],
  "paras": [
   ("p01", "一天只有24小時，所以光靠上班，你很難變有錢。這句話，來自矽谷天使投資人納瓦爾。", ["ill_rent_time"]),
   ("p02", "他的意思是：出租自己的時間，你不會致富，你必須擁有股權。領薪水，收入跟時間綁在一起；擁有股權，公司成長，你那一份就跟著變大，而且是在你睡覺的時候。", ["v_quote"]),
   ("p03", "一般人不一定會創業，但可以買股權。每個月投入一萬元，假設年報酬7%，30年後，本金360萬，大約會變成1,220萬。多出來的那一大段，不是你多加班賺來的。", ["ill_own_piece", "v_compound"]),
   ("p04", "當然，報酬不是保證，也千萬不要借錢重壓。你的月薪，現在有幾成，變成了所有權？", ["ill_taipei_worker"]),
  ],
  "visuals": {
   "ill_rent_time": {"img": "ill_rent_time", "fx": 0.4, "zoom": "in"},
   "v_quote": {"card": "quote", "lines": [["出租自己的時間，"], ["你不會致富。"], ["你必須"], ["擁有股權"]],
               "highlight": ["擁有股權"], "source": "出處：Naval 2018 年推文串（中文為大意）"},
   "ill_own_piece": {"img": "ill_own_piece", "fx": 0.55, "zoom": "in"},
   "v_compound": {"card": "bars", "title": "每月 1 萬元、年報酬 7%（假設）",
                  "bars": [{"label": "本金 30 年", "value": 360, "color": "gray", "fmt": "{:,.0f} 萬", "final": "360 萬", "delay": 0.3},
                           {"label": "30 年後", "value": 1220, "color": "g", "fmt": "{:,.0f} 萬", "final": "約 1,220 萬", "delay": 1.0}],
                  "note": "僅為示意，不代表實際報酬", "note_at": 2.4, "source": "試算：月複利 7%/12"},
   "ill_taipei_worker": {"img": "ill_taipei_worker", "fx": 0.4, "zoom": "in"},
  },
 },
 "S03": {
  "hook": ["不需要任何人批准", "你今天就能用的槓桿"], "flash": ["無需許可的", "槓桿"],
  "paras": [
   ("p01", "有一種槓桿，不需要任何人批准，你今天就能開始用。", ["ill_lever"]),
   ("p02", "矽谷投資人納瓦爾說，槓桿有三種。第一種是勞力，你得先說服別人跟著你。第二種是資本，你得先說服別人把錢交給你。", ["v_three"]),
   ("p03", "第三種，是程式和媒體。寫一段程式、錄一集節目、寫一本書，複製一百萬份，幾乎不用額外成本，也不需要任何人點頭。", ["ill_copies"]),
   ("p04", "主持人喬．羅根，一個人一支麥克風，就觸及了全世界的聽眾。很多新的財富，都來自這裡。", ["ill_mic"]),
   ("p05", "一開始沒人看沒關係，作品會在你睡覺的時候，替你累積信用和機會。你會從哪一種作品開始？", ["ill_create_night"]),
  ],
  "visuals": {
   "ill_lever": {"img": "ill_lever", "fx": 0.5, "zoom": "in"},
   "v_three": {"card": "quote", "lines": [["勞力：", "要人跟著你"], ["資本：", "要人給你錢"], ["程式與媒體："], ["不需要任何人批准"]],
               "highlight": ["不需要任何人批准"], "source": "出處：The Almanack of Naval Ravikant（大意）"},
   "ill_copies": {"img": "ill_copies", "fx": 0.6, "zoom": "in"},
   "ill_mic": {"img": "ill_mic", "fx": 0.35, "zoom": "in"},
   "ill_create_night": {"img": "ill_create_night", "fx": 0.45, "zoom": "in"},
  },
 },
}

cfg = {}
for sid, sp in SHORTS.items():
    d = os.path.join(EP, "08_Shorts", sid)
    for sub in ("01_文案", "02_配音/segments", "99_工作文件"):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    script = {"episode": "EP004-" + sid, "version": 3, "tts_speed": 1.1, "title": sid,
              "sections": [{"id": "s0", "chapter": sid, "title_card": None,
                            "paragraphs": [{"id": pid, "text": t, "visuals": v} for pid, t, v in sp["paras"]]}]}
    json.dump(script, open(os.path.join(d, "01_文案/script.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    cfg[sid] = {"standalone": True, "hook": sp["hook"], "flash": sp["flash"], "visuals": sp["visuals"], "bgm_seed": 44}
    print(sid, sum(len(t) for _, t, _ in sp["paras"]), "字")
json.dump(cfg, open(os.path.join(EP, "08_Shorts/shorts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
