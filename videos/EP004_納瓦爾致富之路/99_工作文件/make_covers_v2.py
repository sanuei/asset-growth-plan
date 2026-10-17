"""EP004 封面第二版：用納瓦爾「錢全拿走、丟到街頭，5～10 年我還能再變有錢」這句話做鉤子。需在项目根目录运行。"""
import os
import sys

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "pipeline"))
import cover  # noqa: E402
from images_episode import request_image  # noqa: E402
from PIL import Image  # noqa: E402

OUT = "videos/EP004_納瓦爾致富之路/05_封面"

# C：真实照片（kris krüg, CC BY-SA 2.0），不花钱
img = cover.fit_cover(Image.open(f"{OUT}/cover_bg.png"))
img = cover.darken_text_side(img, "left")
img = cover.draw_text(img, ["錢全拿走", "丟到街頭", "我還能變富"], ["w", "w", "r"], "left")
img.save(f"{OUT}/封面_C_丟到街頭.jpg", quality=92)
print("OK C")

# D：AI 场景，纽约街头 + 背影，有名的城市符号
bg = f"{OUT}/封面_D_身無分文_bg.png"
if not os.path.exists(bg):
    prompt = (
        "A lone man in a plain dark hoodie seen from behind, standing in the middle of an empty New York City street "
        "at dawn, iconic yellow taxi cabs, Manhattan skyscrapers and steam rising from the street, his empty hands at his sides, "
        "a single crumpled one-dollar bill on the wet asphalt near his feet. He is on the right third of the frame. "
        "The left half of the frame is darker and calm, reserved for text, high contrast. "
        "YouTube thumbnail framed like a cinematic film still. " + cover.STYLE
    )
    open(bg, "wb").write(request_image("gpt-image-2", prompt))
img = cover.fit_cover(Image.open(bg))
img = cover.darken_text_side(img, "left")
img = cover.draw_text(img, ["身無分文", "10年內", "再變有錢"], ["w", "y", "r"], "left")
img.save(f"{OUT}/封面_D_身無分文.jpg", quality=92)
print("OK D")
