"""
Letter Tracing Book Generator -- All-in-one Streamlit Web App
----------------------------------------------------------------
Everything in ONE file: the letter-drawing engine + the website UI.

DEPLOY (free, ~5 minutes):
1. Create a GitHub repo, add these 2 files ONLY: app.py, requirements.txt
2. Go to https://share.streamlit.io -> "New app" -> connect your GitHub repo
   -> main file path: app.py -> Deploy.
3. Done -- you get a public URL you can use / share / link from Etsy.

RUN LOCALLY:
    pip install -r requirements.txt
    streamlit run app.py
"""

import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import string
import io

# ============================================================
# CONFIG
# ============================================================
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
# Streamlit Cloud runs on Debian and ships DejaVu fonts by default, so this
# path works out of the box with no extra setup. (Locally on your own machine
# it may differ -- if this exact path doesn't exist, PIL will raise an error;
# just point FONT_PATH at any .ttf bold font you have.)

PAGE_W, PAGE_H = 2550, 3300          # 8.5 x 11 in @ 300 DPI
MARGIN = 150
DOT_RADIUS = 3
DOT_SPACING = 13
GLYPH_RENDER_SIZE = 500
LETTERS_PER_ROW = 5
ROWS_PER_CASE_DEFAULT = 4
LINE_GRAY = (120, 120, 120)
DOT_GRAY = (90, 90, 90)
TITLE_COLOR = (20, 20, 20)

LETTERS = string.ascii_uppercase


# ============================================================
# ENGINE: turn a letter into a dotted-outline glyph image
# ============================================================
@st.cache_data(show_spinner=False)
def dotted_glyph(char, font_size=GLYPH_RENDER_SIZE):
    font = ImageFont.truetype(FONT_PATH, font_size)
    pad = 40
    canvas_size = font_size + pad * 2
    img = Image.new("L", (canvas_size, canvas_size), 0)
    draw = ImageDraw.Draw(img)
    draw.text((pad, pad), char, font=font, fill=255)

    arr = np.array(img)
    contours, _ = cv2.findContours(arr, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)

    dotted = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    ddraw = ImageDraw.Draw(dotted)

    for cnt in contours:
        pts = cnt.reshape(-1, 2)
        if len(pts) < 2:
            continue
        acc = 0.0
        last = pts[0]
        ddraw.ellipse(
            [last[0] - DOT_RADIUS, last[1] - DOT_RADIUS,
             last[0] + DOT_RADIUS, last[1] + DOT_RADIUS],
            fill=DOT_GRAY + (255,),
        )
        for p in pts[1:]:
            d = np.linalg.norm(p - last)
            acc += d
            if acc >= DOT_SPACING:
                ddraw.ellipse(
                    [p[0] - DOT_RADIUS, p[1] - DOT_RADIUS,
                     p[0] + DOT_RADIUS, p[1] + DOT_RADIUS],
                    fill=DOT_GRAY + (255,),
                )
                acc = 0.0
            last = p

    bbox = dotted.getbbox()
    if bbox:
        dotted = dotted.crop(bbox)
    return dotted


def draw_ruled_line(draw, x1, x2, y_top, y_mid, y_base):
    draw.line([(x1, y_top), (x2, y_top)], fill=LINE_GRAY, width=3)
    dash, gap = 14, 10
    x = x1
    while x < x2:
        draw.line([(x, y_mid), (min(x + dash, x2), y_mid)], fill=LINE_GRAY, width=2)
        x += dash + gap
    draw.line([(x1, y_base), (x2, y_base)], fill=(60, 60, 60), width=4)


def make_page(upper, lower, glyph_cache, rows_per_case=ROWS_PER_CASE_DEFAULT):
    page = Image.new("RGB", (PAGE_W, PAGE_H), (255, 255, 255))
    draw = ImageDraw.Draw(page)

    title_font = ImageFont.truetype(FONT_PATH, 70)
    header_font = ImageFont.truetype(FONT_PATH, 55)

    draw.text((MARGIN, 90), "Name:", font=header_font, fill=TITLE_COLOR)
    name_line_x1 = MARGIN + 200
    draw.line([(name_line_x1, 140), (PAGE_W - MARGIN, 140)], fill=(30, 30, 30), width=3)

    draw.text((MARGIN, 190), f"Trace the letter {upper}{lower}.", font=title_font, fill=TITLE_COLOR)

    top_y = 380
    usable_w = PAGE_W - 2 * MARGIN
    col_w = usable_w / LETTERS_PER_ROW
    row_h = 210

    def draw_case_block(letter, start_y, n_rows):
        glyph = glyph_cache[letter]
        gw, gh = glyph.size
        y = start_y
        for r in range(n_rows):
            y_top = y + 20
            y_base = y + row_h - 40
            y_mid = (y_top + y_base) // 2
            draw_ruled_line(draw, MARGIN, PAGE_W - MARGIN, y_top, y_mid, y_base)

            target_h = (y_base - y_top) * 0.95
            scale = target_h / gh
            target_w = gw * scale
            resized = glyph.resize((max(1, int(target_w)), max(1, int(target_h))))

            for c in range(LETTERS_PER_ROW):
                cx = MARGIN + col_w * c + col_w * 0.15
                paste_y = int(y_base - target_h)
                page.paste(resized, (int(cx), paste_y), resized)
            y += row_h
        return y

    y_cursor = draw_case_block(upper, top_y, rows_per_case)
    y_cursor += 30
    draw_case_block(lower, y_cursor, rows_per_case)

    footer_font = ImageFont.truetype(FONT_PATH, 40)
    footer_text = "Letter Tracing Practice"
    fw = draw.textlength(footer_text, font=footer_font)
    draw.text(((PAGE_W - fw) / 2, PAGE_H - 110), footer_text, font=footer_font, fill=(150, 150, 150))

    return page


# ============================================================
# WEBSITE UI
# ============================================================
st.set_page_config(page_title="Letter Tracing Book Generator", page_icon="✏️", layout="centered")

st.title("✏️ Letter Tracing Book Generator")
st.write(
    "Pick your options below, then click **Generate** to build a print-ready "
    "PDF tracing workbook -- one page per letter, uppercase + lowercase, dotted "
    "trace guides on ruled handwriting lines."
)

st.subheader("1. Choose letters")
mode = st.radio("Which letters?", ["Full alphabet (A-Z)", "Custom selection"], horizontal=True)

if mode == "Full alphabet (A-Z)":
    selected = list(string.ascii_uppercase)
else:
    selected = st.multiselect("Pick letters", list(string.ascii_uppercase), default=["A", "B", "C"])

st.subheader("2. Options")
col1, col2 = st.columns(2)
with col1:
    rows_per_case = st.slider("Practice rows per case (upper/lower)", 2, 6, 4)
with col2:
    book_title = st.text_input("Book title (for your reference only)", "My Letter Tracing Book")

st.divider()

if st.button("🚀 Generate My Book", type="primary", use_container_width=True):
    if not selected:
        st.error("Please select at least one letter.")
    else:
        progress = st.progress(0, text="Building glyphs...")
        glyph_cache = {}
        total = len(selected)

        for i, L in enumerate(selected):
            glyph_cache[L] = dotted_glyph(L)
            glyph_cache[L.lower()] = dotted_glyph(L.lower())
            progress.progress((i + 1) / total * 0.5, text=f"Building glyph {L}...")

        pages = []
        for i, L in enumerate(selected):
            page = make_page(L, L.lower(), glyph_cache, rows_per_case=rows_per_case)
            pages.append(page)
            progress.progress(0.5 + (i + 1) / total * 0.5, text=f"Composing page {L}{L.lower()}...")

        buf = io.BytesIO()
        pages[0].save(buf, format="PDF", save_all=True, append_images=pages[1:])
        buf.seek(0)

        progress.progress(1.0, text="Done!")
        st.success(f"Your book is ready -- {len(pages)} page(s)!")

        st.download_button(
            label="⬇️ Download PDF",
            data=buf,
            file_name=f"{book_title.replace(' ', '_')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

        st.image(pages[0], caption=f"Preview: {selected[0]}{selected[0].lower()}", use_container_width=True)
