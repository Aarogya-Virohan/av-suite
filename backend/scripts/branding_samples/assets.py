"""Fictional demo clinic logos and exercise line drawings for branding samples."""
from PIL import Image, ImageDraw, ImageFont
import math, os
OUT = os.path.join(os.path.dirname(__file__), "assets")
FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "app", "services", "posture", "brand", "fonts", "plus-jakarta-sans-latin-800-normal.woff")
GREEN = (46, 125, 98); ORANGE = (232, 140, 58); DARK = (34, 49, 63)

def leaf(d, cx, cy, r, col):
    d.ellipse((cx - r, cy - r * 0.55, cx + r, cy + r * 0.55), fill=col)

def mark(d, cx, cy, s):
    d.ellipse((cx - s, cy - s, cx + s, cy + s), fill=GREEN)
    d.ellipse((cx - s * .32, cy - s * .78, cx + s * .1, cy - s * .36), fill="white")  # head
    d.line([(cx - s * .1, cy - s * .3), (cx + s * .1, cy + s * .25)], fill="white", width=int(s * .16))
    d.line([(cx + s * .1, cy + s * .25), (cx - s * .25, cy + s * .7)], fill="white", width=int(s * .14))
    d.line([(cx + s * .1, cy + s * .25), (cx + s * .5, cy + s * .62)], fill="white", width=int(s * .14))
    d.line([(cx - s * .55, cy - s * .2), (cx + s * .55, cy - s * .05)], fill=ORANGE, width=int(s * .14))

def logos():
    f = lambda n: ImageFont.truetype(FONT, n)
    # round (opaque white background, as many clinics upload)
    im = Image.new("RGB", (600, 600), "white"); d = ImageDraw.Draw(im)
    d.ellipse((20, 20, 580, 580), outline=GREEN, width=16); mark(d, 300, 260, 150)
    d.text((300, 470), "SUKOON", font=f(64), fill=DARK, anchor="mm")
    im.save(f"{OUT}/logo_round.png")
    # square (transparent background, dark artwork)
    im = Image.new("RGBA", (500, 500), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((10, 10, 490, 490), 70, fill=DARK); mark(d, 250, 210, 120)
    d.text((250, 410), "SUKOON", font=f(56), fill="white", anchor="mm")
    im.save(f"{OUT}/logo_square.png")
    # wide wordmark (transparent, dark text: low contrast on the band)
    im = Image.new("RGBA", (1200, 320), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    mark(d, 160, 160, 130)
    d.text((330, 120), "Sukoon", font=f(120), fill=DARK, anchor="lm")
    d.text((336, 230), "PHYSIO & REHAB", font=f(54), fill=GREEN, anchor="lm")
    im.save(f"{OUT}/logo_wide.png")
    # tall (opaque cream background, JPEG)
    im = Image.new("RGB", (300, 900), (250, 246, 236)); d = ImageDraw.Draw(im)
    mark(d, 150, 230, 120)
    for i, ch in enumerate("SUKOON"):
        d.text((150, 420 + i * 78), ch, font=f(70), fill=DARK, anchor="mm")
    im.save(f"{OUT}/logo_tall.jpg", quality=92)

def figure(name, pose):
    W, H = 900, 640
    im = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(im)
    d.rectangle((0, H - 90, W, H), fill=(236, 240, 242))
    lw = 22; c = (52, 73, 94); a = (226, 118, 52)
    if pose == "bridge":
        d.ellipse((150, 455, 230, 535), fill=c)
        d.line([(230, 510), (450, 380), (620, 470), (640, 550)], fill=c, width=lw, joint="curve")
        d.line([(300, 470), (330, 550)], fill=c, width=lw)
        d.line([(420, 330), (450, 280)], fill=a, width=8); d.polygon([(450, 260), (435, 290), (465, 292)], fill=a)
    elif pose == "squat":
        d.ellipse((420, 90, 500, 170), fill=c)
        d.line([(455, 175), (430, 340), (560, 400), (520, 550)], fill=c, width=lw, joint="curve")
        d.line([(450, 220), (640, 230)], fill=c, width=lw)
        d.line([(330, 330), (330, 420)], fill=a, width=8); d.polygon([(330, 440), (315, 410), (345, 410)], fill=a)
    elif pose == "chin":
        d.ellipse((400, 120, 500, 220), fill=c)
        d.line([(450, 225), (450, 450)], fill=c, width=lw)
        d.line([(450, 450), (420, 550)], fill=c, width=lw); d.line([(450, 450), (480, 550)], fill=c, width=lw)
        d.line([(560, 170), (630, 170)], fill=a, width=8); d.polygon([(540, 170), (570, 155), (570, 185)], fill=a)
    elif pose == "clam":
        d.ellipse((140, 380, 220, 460), fill=c)
        d.line([(220, 430), (480, 450)], fill=c, width=lw)
        d.line([(480, 450), (600, 400), (700, 470)], fill=c, width=lw, joint="curve")
        d.line([(480, 450), (620, 520), (700, 480)], fill=c, width=lw, joint="curve")
        d.arc((560, 300, 700, 440), 200, 300, fill=a, width=8)
    elif pose == "stretch":
        d.ellipse((380, 100, 460, 180), fill=c)
        d.line([(420, 185), (440, 380)], fill=c, width=lw)
        d.line([(440, 380), (330, 550)], fill=c, width=lw); d.line([(440, 380), (600, 540)], fill=c, width=lw)
        d.line([(425, 240), (300, 120)], fill=c, width=lw); d.line([(425, 240), (560, 300)], fill=c, width=lw)
    im.save(f"{OUT}/ex_{name}.jpg", quality=90)


def posture_photo(view):
    W, H = 600, 900
    im = Image.new("RGB", (W, H), (244, 246, 247)); d = ImageDraw.Draw(im)
    c = (120, 134, 150); ln = (0, 150, 136); pt = (230, 90, 60)
    if view == "side":
        pts = [(300, 140), (312, 260), (300, 470), (308, 650), (300, 830)]
        d.ellipse((255, 95, 345, 185), fill=c); d.line(pts[1:], fill=c, width=46, joint="curve")
    else:
        d.ellipse((255, 95, 345, 185), fill=c); d.line([(300, 190), (300, 520)], fill=c, width=90)
        d.line([(210, 230), (390, 238)], fill=c, width=40); d.line([(270, 520), (262, 840)], fill=c, width=40); d.line([(330, 520), (338, 840)], fill=c, width=40)
        d.line([(210, 230), (180, 470)], fill=c, width=30); d.line([(390, 238), (420, 478)], fill=c, width=30)
        pts = [(210, 230), (390, 238), (262, 520), (338, 520)]
        d.line([pts[0], pts[1]], fill=ln, width=4); d.line([pts[2], pts[3]], fill=ln, width=4)
    d.line([(300, 60), (300, 860)], fill=ln, width=2)
    for p in pts:
        d.ellipse((p[0] - 9, p[1] - 9, p[0] + 9, p[1] + 9), fill=pt)
    im.save(f"{OUT}/posture_{view}.jpg", quality=88)

