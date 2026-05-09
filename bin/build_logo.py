#!/usr/bin/env python3
"""Generate assets/logo.png — horizontal lockup: canary icon + "Thermal Canary" wordmark."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
ICON = ROOT / "assets" / "icon.png"
FONT_PATH = ROOT / "bin" / "fonts" / "Exo2-SemiBold.ttf"
OUT = ROOT / "assets" / "logo.png"

CANVAS = (1400, 400)
BIRD_HEIGHT = 320
BIRD_X = 80
BIRD_Y = (CANVAS[1] - BIRD_HEIGHT) // 2   # 40px top/bottom margin
GAP = 60
FONT_SIZE = 140
COLOR_THERMAL = (242, 242, 242, 255)       # warm off-white
COLOR_CANARY  = (245, 197, 24, 255)        # matches bird yellow
SHADOW        = (0, 0, 0, 80)
OPTICAL_NUDGE = -20                        # raise text to align with bird body centroid

canvas = Image.new("RGBA", CANVAS, (0, 0, 0, 0))

# Bird
bird = Image.open(ICON).convert("RGBA")
bw = int(bird.width * BIRD_HEIGHT / bird.height)
bird = bird.resize((bw, BIRD_HEIGHT), Image.LANCZOS)
bird_layer = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
bird_layer.paste(bird, (BIRD_X, BIRD_Y), bird)
canvas = Image.alpha_composite(canvas, bird_layer)

# Font with fallback chain
for font_path in [FONT_PATH, "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
    try:
        font = ImageFont.truetype(str(font_path), FONT_SIZE)
        break
    except (OSError, IOError):
        continue
else:
    font = ImageFont.load_default()

text_x = BIRD_X + bw + GAP
text_y = (CANVAS[1] - FONT_SIZE) // 2 + OPTICAL_NUDGE
w_thermal = font.getbbox("Thermal ")[2]

# Shadow layer
shadow_layer = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
sd = ImageDraw.Draw(shadow_layer)
sd.text((text_x, text_y + 2), "Thermal ", font=font, fill=SHADOW)
sd.text((text_x + w_thermal, text_y + 2), "Canary", font=font, fill=SHADOW)
shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=2))
canvas = Image.alpha_composite(canvas, shadow_layer)

# Text layer
text_layer = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
td = ImageDraw.Draw(text_layer)
td.text((text_x, text_y), "Thermal ", font=font, fill=COLOR_THERMAL)
td.text((text_x + w_thermal, text_y), "Canary", font=font, fill=COLOR_CANARY)
canvas = Image.alpha_composite(canvas, text_layer)

canvas.save(OUT, "PNG", optimize=True)
print(f"Saved {OUT} ({OUT.stat().st_size // 1024} KB)")
