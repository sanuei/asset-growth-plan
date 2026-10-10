"""EP003 封面第二版：两张，把「有名的东西」放进画面，文字更少更猛。需在项目根目录运行。"""
import concurrent.futures as cf
import os
import sys

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "pipeline"))
import cover  # noqa: E402
from images_episode import request_image  # noqa: E402
from PIL import Image  # noqa: E402

OUT = "videos/EP003_美國國債完整解析/05_封面"
STYLE = cover.STYLE
PROMPTS = {
    "封面_A_山姆大叔": (
        "A middle-aged man dressed as classic Uncle Sam, tall red-white-and-blue star-spangled top hat, white goatee, "
        "navy coat, pointing his index finger straight at the camera with a stern serious expression. "
        "He is on the right third of the frame, head and shoulders. Behind him, dark stormy sky and a giant glowing "
        "red number-less stack of US hundred-dollar bills. The left half of the frame is empty dark background."
    ),
    "封面_B_國會山莊鈔票": (
        "The US Capitol dome at dusk on the right two thirds of the frame, dramatic storm clouds, lit from within, "
        "US hundred-dollar bills raining down from the sky and one large bill burning at the edges in the foreground. "
        "The left third of the frame is empty dark background, high contrast."
    ),
}
LINES = {
    "封面_A_山姆大叔": (["美國欠了", "40兆美元", "會害到你？"], ["w", "y", "w"]),
    "封面_B_國會山莊鈔票": (["最安全的資產", "竟然虧7.5%"], ["w", "r"]),
}


def gen(name):
    bg = f"{OUT}/{name}_bg.png"
    if not os.path.exists(bg):
        data = request_image("gpt-image-2", PROMPTS[name] + ". YouTube thumbnail framed like a cinematic film still. " + STYLE)
        open(bg, "wb").write(data)
    return name


with cf.ThreadPoolExecutor(2) as ex:
    for n in ex.map(gen, PROMPTS):
        lines, colors = LINES[n]
        img = cover.fit_cover(Image.open(f"{OUT}/{n}_bg.png"))
        img = cover.darken_text_side(img, "left")
        img = cover.draw_text(img, lines, colors, "left")
        img.save(f"{OUT}/{n}.jpg", quality=92)
        print("OK", n)
