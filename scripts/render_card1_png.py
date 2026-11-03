from PIL import Image, ImageDraw, ImageFont
import os

# Create high-res rendering of Card 1 (scale 3x for crispness)
scale = 3
w_in = 2.893
h_in = 3.070
dpi = 150

img_w = int(w_in * dpi * scale)
img_h = int(h_in * dpi * scale)

img = Image.new('RGBA', (img_w, img_h), (255, 255, 255, 0))
draw = ImageDraw.Draw(img)

# Card background (#F8F9FA, border #EAECF0)
border_r = int(10 * scale)
draw.rounded_rectangle([0, 0, img_w - 1, img_h - 1], radius=border_r, fill=(0xF8, 0xF9, 0xFA, 255), outline=(0xEA, 0xEC, 0xF0, 255), width=int(1*scale))

badge_inset = int(0.05 * dpi * scale)
badge_h = int(0.19 * dpi * scale)
cat_h = int(0.15 * dpi * scale)
gap = int(0.01 * dpi * scale)

# Fonts
try:
    font_badge = ImageFont.truetype('arialbd.ttf', int(8.0 * scale * (dpi/72.0)))
    font_bold = ImageFont.truetype('arialbd.ttf', int(7.5 * scale * (dpi/72.0)))
    font_body = ImageFont.truetype('arial.ttf', int(7.5 * scale * (dpi/72.0)))
    font_cat = ImageFont.truetype('arialbd.ttf', int(8.0 * scale * (dpi/72.0)))
except:
    font_badge = font_bold = font_body = font_cat = ImageFont.load_default()

# Pill badge
b_left = badge_inset
b_top = badge_inset
b_right = img_w - badge_inset
b_bottom = b_top + badge_h
draw.rounded_rectangle([b_left, b_top, b_right, b_bottom], radius=int(4*scale), fill=(0x04, 0x11, 0x33, 255))
draw.text(((b_left + b_right)//2, (b_top + b_bottom)//2), 'STAGE 01 & 02', font=font_badge, fill=(255, 255, 255, 255), anchor='mm')

# Category title
c_top = b_bottom + gap
draw.text((b_left, c_top), 'SUBMISSION & REVIEW PROTOCOLS', font=font_cat, fill=(0x04, 0x11, 0x33, 255))

# Text Box Body
tb_top = c_top + cat_h + gap
avail_w = img_w - 2 * badge_inset

steps = [
    ('Inputs ready:', ' Client provisions environment, Snowflake schema (HS-4781), upstream systems access, and SME availability.'),
    ('Execution:', ' Track 5 delivery phases (P1–P3, Hypercare) against milestone acceptance criteria, managed by Delivery Manager.'),
    ('Submission:', ' Submit formal milestone package to Client Approver with written notice to initiate acceptance period.'),
    ('Review:', ' Client conducts 10-business-day evaluation against specifications and milestone acceptance criteria.'),
    ('Deliverable rules:', ' Phase sign-offs require auth shell (P1), Snowflake/FastAPI (P2a), UI workflows (P2b), cutover (P3), and 30-day stability (Hypercare).')
]

curr_y = tb_top
line_spacing = 1.08
line_h = int(7.5 * scale * (dpi/72.0) * line_spacing)
space_after = int(2.0 * scale * (dpi/72.0))

for lbl, body in steps:
    lbl_w = int(draw.textlength(lbl, font=font_bold))
    words = body.strip().split()
    
    first_line_words = []
    rest_words = words[:]
    
    line_txt = ''
    while rest_words:
        test_txt = (line_txt + ' ' + rest_words[0]).strip()
        test_w = lbl_w + int(draw.textlength(' ' + test_txt if line_txt else test_txt, font=font_body))
        if test_w <= avail_w:
            line_txt = test_txt
            rest_words.pop(0)
        else:
            break
            
    draw.text((b_left, curr_y), lbl, font=font_bold, fill=(0x04, 0x11, 0x33, 255))
    if line_txt:
        draw.text((b_left + lbl_w + int(2*scale), curr_y), line_txt, font=font_body, fill=(0x1D, 0x29, 0x39, 255))
    curr_y += line_h
    
    while rest_words:
        line_txt = ''
        while rest_words:
            test_txt = (line_txt + ' ' + rest_words[0]).strip()
            test_w = int(draw.textlength(test_txt, font=font_body))
            if test_w <= avail_w:
                line_txt = test_txt
                rest_words.pop(0)
            else:
                break
        if not line_txt and rest_words:
            line_txt = rest_words.pop(0)
        draw.text((b_left, curr_y), line_txt, font=font_body, fill=(0x1D, 0x29, 0x39, 255))
        curr_y += line_h
        
    curr_y += space_after

os.makedirs('reports', exist_ok=True)
out_path = 'reports/slide16_card1_fixed_7.5pt_role_only.png'
img.save(out_path)
print(f'Rendered Card 1 to {out_path} (Final height used: {curr_y}/{img_h} px -> {curr_y/img_h*100:.1f}%)')
