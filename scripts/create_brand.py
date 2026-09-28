"""Generate DimaScript's geometric mark and Windows installer artwork."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / 'assets'
ART = ASSETS / 'installer'
ART.mkdir(parents=True, exist_ok=True)
NAVY, TEAL, WHITE = '#172B3A', '#137D78', '#FFFFFF'


def mark(size):
    im = Image.new('RGBA', (512, 512))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((8, 8, 504, 504), radius=116, fill=NAVY)
    # A D-shaped outline with three speech bars in the counter.
    d.rounded_rectangle((121, 94, 403, 418), radius=134, fill=WHITE)
    d.rectangle((121, 94, 238, 418), fill=WHITE)
    d.rounded_rectangle((176, 150, 347, 362), radius=81, fill=NAVY)
    d.rectangle((176, 150, 239, 362), fill=NAVY)
    for x, h in [(196, 64), (236, 128), (276, 90)]:
        d.rounded_rectangle((x, 256-h/2, x+23, 256+h/2), radius=11, fill='#57D4BE')
    return im.resize((size, size), Image.Resampling.LANCZOS)


mark(256).save(ASSETS / 'app.ico', sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
mark(64).save(ASSETS / 'brand.png')
mark(512).save(ART / 'mark.png')
font = 'C:/Windows/Fonts/segoeui.ttf'
bold = 'C:/Windows/Fonts/segoeuib.ttf'
canvas = Image.new('RGB', (328, 628), NAVY)
d = ImageDraw.Draw(canvas)
canvas.paste(mark(88), (36, 52), mark(88))
d.text((36, 172), 'DimaScript', fill=WHITE, font=ImageFont.truetype(bold, 38))
d.text((38, 226), '2.0', fill='#A4BBC7', font=ImageFont.truetype(font, 23))
# Abstract transcript lines; no slogan or advertising copy.
for y, length in [(394, 225), (421, 175), (448, 206), (475, 133)]:
    d.rounded_rectangle((38,y,38+length,y+7), radius=3, fill='#355665')
d.rounded_rectangle((38,552,92,557), radius=2, fill='#57D4BE')
canvas.save(ART / 'wizard.bmp')
small = Image.new('RGB', (110,110), WHITE)
small.paste(mark(82), (14,14), mark(82))
small.save(ART / 'wizard-small.bmp')
print('Brand assets generated:', ROOT)
