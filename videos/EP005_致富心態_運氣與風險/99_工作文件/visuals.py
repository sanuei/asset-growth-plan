"""每段的画面安排。写法：「画面id@词」= 念到这个词时切进来（词要按顺序出现在这段文字里）；第一个画面从段落开头开始。
画面 id：ill_ = AI 插图，web_ = Commons 照片，v_ = 视频片段（视频素材/footage.json），shot_ = 网页截图卡，
card_/q_/part_/hook_/title_/end_ = graphics.json 里的卡片。同一素材再用一次时加「#2」。
"""
V = {
    # ---------- 开场：频道介绍，然后先讲观点 ----------
    "p00": ["brand_intro"],
    "p01": ["hook_thesis", "v_library@這是《致富心態》", "ill_spotlight@你看到的每一個成功", "v_dice_slow@背後都有運氣",
            "ill_coin_toss@你看到的每一個失敗", "v_peaks_fog@背後都有風險", "card_two_sides@而這兩樣東西"],
    "p02": ["v_seattle61", "v_tty_hands@租到了", "web_asr33@電腦終端機", "ill_terminal_room@兩個少年", "v_tty_paper@沒日沒夜",
            "v_gates_talk@其中一個", "web_microsoft_aerial@創辦了微軟"],
    "p03": ["ill_briefcase", "ill_schedule@和他一起寫程式", "ill_dreams@一起計畫", "v_climb@17歲那年",
            "ill_empty_desk@再也沒有回來", "ill_twins@同一所學校", "v_dice_throw@百萬分之一", "ill_two_paths@兩個相反的方向"],
    "p04": ["title_main", "web_gates_allen_1970@看懂運氣和風險", "v_crowd@每一個人的財富", "v_hourglass@既然結果",
            "ill_spotlight#2@我們該怎麼看待", "ill_bench_dusk@和自己的失敗"],

    # ---------- 第一部 百萬分之一的運氣 ----------
    "p05": ["part_1", "ill_teacher@數學和科學老師", "v_classroom@他覺得學生", "v_punchcard@要動手做", "v_mainframe@就該懂一點電腦"],
    "p06": ["ill_rummage_sale", "card_3000@大約3000美元", "web_asr33_chm@租一台電傳打字機", "v_fernschreiber@透過電話線",
            "v_mainframe2@奇異公司的大型電腦", "v_tty_woman@讓學生分時共用", "v_tapedrive@在那個年代", "web_asr33#2@都沒有這麼先進"],
    "p07": ["v_school_walk", "web_gates_allen_1970#2@認識了高他兩屆", "v_school_hall@電腦不是正式課程", "ill_night_coding@兩個人就把",
            "v_tty_print@放學後", "v_panel_lights@週末也不停", "web_asr33_carriage@很快"],
    "p08": ["ill_magazine_dream", "v_magazine@你覺得經營", "v_wallst@財富500強", "web_allen@艾倫說不知道",
            "v_needle_night@也許有一天", "web_microsoft_aerial#2@後來的事"],
    "p09": ["v_notes", "ill_sea_students@根據聯合國", "v_crowd3@全世界大約有", "card_funnel@其中1800萬", "web_lakeside@而在湖濱中學念書"],
    "p10": ["card_million", "v_crowd2@全世界一百萬", "ill_lit_window@只有一個人", "v_fernschreiber2@替學生租電腦", "web_gates_1977@蓋茲，剛好"],
    "p11": ["v_gates_talk2", "shot_gates_speech@2005年", "shot_gates_speech2@如果沒有湖濱", "v_gates_talk3@他非常聰明",
            "v_tty_hands2@十幾歲時", "web_asr33_chm#2@連很多專家", "v_dice_mix@百萬分之一的好運"],

    # ---------- 第二部 百萬分之一的風險 ----------
    "p12": ["part_2", "web_gates_allen_1970#3@除了蓋茲和艾倫", "ill_briefcase#2@還有一個叫肯特", "v_classroom2@全班成績最好"],
    "p13": ["v_monorail", "ill_phone_bed@每天講好久", "q_phone@幾十年後", "v_w48_dial@525"],
    "p14": ["v_tty_print2", "v_classroom3@學校排課", "ill_schedule#2@學校把這件事", "v_tty_hands#2@要寫程式"],
    "p15": ["v_city60s", "ill_briefcase#3@肯特總是提著", "card_dreams@他們常常計畫", "ill_dreams#2@不管做什麼"],
    "p16": ["q_together", "ill_empty_desk#2@說到這裡"],
    "p17": ["v_snow_hills", "ill_climb_class@肯特參加了", "web_shuksan@在華盛頓州的舒克桑山", "v_rim@他失足墜落",
            "card_kent_time@那年17歲", "ill_bad_news@蓋茲說", "web_asr33_carriage#2@那套排課程式"],
    "p18": ["v_rim2", "web_shuksan2@一個高中生", "card_twin_odds@蓋茲遇上了", "web_gates_allen_1970#5@永遠沒有機會", "ill_two_paths#2@同樣的力量", "v_rim_person@方向卻"],
    "p19": ["ill_twins#2", "v_hourglass#2@生活中的每一個結果", "card_7b@這場遊戲裡", "v_poker@你控制不了",
            "web_gates_2014#2@每一個比爾", "ill_empty_desk#3@都可能有一個肯特", "ill_wheel@只是命運的轉盤"],

    # ---------- 第三部 大膽和魯莽，只差一毫米 ----------
    "p20": ["part_3", "shot_nobel_shiller@作者問過", "web_shiller@關於投資", "q_shiller@席勒說"],
    "p21": ["v_nyse_floor", "v_ticker@但運氣很難量化", "card_why_silent@而且說別人", "ill_spotlight#3@所以，我們乾脆"],
    "p22": ["v_library#2", "ill_brothers@兄弟之間", "card_siblings@不輸給身高", "ill_three_births@你受的教育",
            "v_handshake@道理不難懂", "ill_brothers#2@他們多半不會承認"],
    "p23": ["ill_enron_boxes", "v_stockboard@投資虧錢", "v_trader_phone@有時候是", "ill_flat_stock@他買了一支股票",
            "card_80_20@可能是他", "ill_flat_stock#2@連他自己"],
    "p24": ["v_magazine2", "ill_blame@人們習慣", "card_blame@把自己的失敗", "v_tower_up@因為我們看不到", "v_office50s@輪到自己"],
    "p25": ["ill_newsstand", "v_magazines@不會登那些", "card_coin@卻一定會登", "v_coins_hand@兩種人都在擲硬幣", "ill_coin_toss#2@只是擲出了"],
    "p26": ["v_old_loco", "web_vanderbilt@美國鐵路大亨", "v_old_locos@剛談完", "ill_vanderbilt_office@他的顧問", "q_vanderbilt@范德比爾特回答"],
    "p27": ["v_steam", "v_old_loco2@難怪他會成功", "ill_railroad_build@那個年代", "v_tracks@不管三七二十一", "shot_wiki_vanderbilt@成了美國史上"],
    "p28": ["ill_courtroom", "v_railyard@同樣是挑戰", "web_enron@2001年", "shot_wiki_enron@因為財務造假", "ill_enron_boxes#2@人人唾棄",
            "web_rockefeller@洛克斐勒", "ill_courtroom#2@一位法官", "web_rockefeller#2@歷史學家", "card_same_act@一個叫氣魄"],
    "p29": ["v_nyse_floor2", "web_graham@班傑明", "shot_wiki_graham@是巴菲特的老師", "ill_graham_desk@可是1948年",
            "web_geico@買下蓋可保險", "card_graham@大約是公司"],
    "p30": ["card_geico", "v_ticker2@賺的錢比他", "q_graham@葛拉漢自己寫"],
    "p31": ["web_zuckerberg", "ill_boardroom_2006@2006年", "shot_zuck_yahoo@當時管理團隊", "web_zuckerberg#2@今天",
            "shot_sec_yahoo@但2008年", "ill_rejected_bid@雅虎也拒絕了", "web_yahoo_hq@後來雅虎", "card_yahoo@這時"],
    "p32": ["ill_tightrope", "card_mm@中間只差", "v_dice_slow2@運氣、風險"],

    # ---------- 第四部 成功和失敗，都是糟糕的老師 ----------
    "p33": ["part_4", "card_lessons@第一", "ill_blame#2@想看不起", "v_crowd#2@不要把一個結果"],
    "p34": ["ill_letter_son", "ill_three_births#2@有些人出生在", "v_fair_crowd@有些人生在充滿機會", "v_sunset_tracks@我希望你成功",
            "q_letter@但你要知道", "v_students@評價別人"],
    "p35": ["card_lessons#2", "ill_newsstand#2@我們最愛研究", "ill_enron_boxes#3@登上頭條", "v_dice_throw2@但結果越極端",
            "v_nyse_floor3@巴菲特的成功", "ill_free_morning@但像能掌控", "v_students2@這種普遍的規律"],
    "p36": ["web_gates_2014#3", "q_gates_teacher@成功是個", "ill_pedestal@如果你承認", "ill_twins#3@它的雙胞胎兄弟", "v_peak_fly@隨時可能"],
    "p37": ["ill_flat_stock#3", "ill_bad_news#2@它會讓聰明人", "v_snow_hills2@可是有時候", "card_plan@所以，與其祈求", "ill_safety_net@不要讓一次失敗", "ill_wait_rain@留在場上"],
    "p38": ["v_sunset_tracks2", "ill_bench_dusk#2@當你回頭看"],
    "p39": ["card_summary", "ill_tightrope#2@第二", "ill_newsstand#3@別急著把別人的成功", "ill_blame#3@也別急著", "ill_wait_rain#2@第三", "hook_thesis#2@任何事，都沒有", "end_card@如果這支影片"],
}
