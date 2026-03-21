import os
import io
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image
from datetime import datetime

# -------- ARABIC SUPPORT --------
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    arabic_support = True
except ImportError:
    arabic_support = False

# Get script & template directory
script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
assets_dir = os.path.join(script_dir, "assets")

# -------- REGISTER ARABIC FONT --------
# Place Amiri-Regular.ttf in your assets/ folder.
# Download free from: https://fonts.google.com/specimen/Amiri
ARABIC_FONT_NAME = "Amiri"
arabic_font_path = os.path.join(assets_dir, "Amiri-Regular.ttf")
arabic_font_loaded = False
if os.path.exists(arabic_font_path):
    pdfmetrics.registerFont(TTFont(ARABIC_FONT_NAME, arabic_font_path))
    arabic_font_loaded = True


def has_arabic(text):
    """Returns True if the text contains any Arabic characters."""
    return any('\u0600' <= ch <= '\u06FF' for ch in text)


def reshape_arabic(text):
    """
    Reshapes Arabic letters so they connect properly,
    then applies BiDi algorithm for correct RTL direction.
    Requires: pip install arabic-reshaper python-bidi
    """
    if arabic_support and has_arabic(text):
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    return text


def draw_text(c, x, y, text, fallback_font="Helvetica", size=10):
    """
    Draws text using Arabic font + reshaping if Arabic characters detected,
    otherwise falls back to the standard font.
    """
    if has_arabic(text) and arabic_font_loaded:
        c.setFont(ARABIC_FONT_NAME, size)
        c.drawString(x, y, reshape_arabic(text))
    else:
        c.setFont(fallback_font, size)
        c.drawString(x, y, text)
    c.setFont(fallback_font, size)  # always reset to fallback after


def crop_top(image_path, crop_px=300):
    """
    Crops `crop_px` pixels from the TOP of the image to remove white padding.
    Tune crop_px until the arabic text sits flush below the logo.
    """
    img = Image.open(image_path)
    w, h = img.size
    cropped = img.crop((0, crop_px, w, h))
    buf = io.BytesIO()
    cropped.save(buf, format="PNG")
    buf.seek(0)
    return buf


# -------- HEADER --------
st.set_page_config(
    page_title="Invoice Generator",
    page_icon="🧾",
    layout="wide"
)

# Logo left aligned, above the title
logo_display_path = os.path.join(assets_dir, "logo.png")
if os.path.exists(logo_display_path):
    col_logo, col_spacer = st.columns([1, 5])
    with col_logo:
        st.image(logo_display_path, width=120)

st.header("🧾 Invoice Generator")

# Warn if arabic libraries not installed
if not arabic_support:
    st.warning(
        "⚠️ Arabic reshaping libraries not installed. "
        "Arabic text will not render correctly in the PDF. "
        "Run: `pip install arabic-reshaper python-bidi`"
    )

# -------- HIDE +/- BUTTONS --------
st.markdown("""
    <style>
    button[data-testid="stNumberInputStepDown"],
    button[data-testid="stNumberInputStepUp"] {
        display: none;
    }
    </style>
""", unsafe_allow_html=True)

# -------- SESSION STATE FOR ROWS --------
if "num_rows" not in st.session_state:
    st.session_state.num_rows = 1

if "rows" not in st.session_state:
    st.session_state.rows = [{"description": "", "quantity": 1, "price": 0.0}]

# -------- USER INPUTS --------
col1, col2 = st.columns(2)
with col1:
    customer_name = st.text_input("Customer Name", placeholder="Enter customer name")
    customer_phone = st.text_input("Customer Phone Number", placeholder="e.g. 98841770 (max 8 digits)")
    phone_digits = "".join(filter(str.isdigit, customer_phone))
    if customer_phone and (not phone_digits or len(phone_digits) > 8):
        st.error("Phone number must not exceed 8 digits.")
        phone_valid = False
    else:
        phone_valid = True

with col2:
    invoice_date = st.date_input("Date", value=datetime.now().date())

st.markdown("---")

# -------- ITEMS TABLE --------
st.subheader("Invoice Items")

header_cols = st.columns([4, 1.5, 2, 1])
header_cols[0].markdown("**Description**")
header_cols[1].markdown("**Quantity**")
header_cols[2].markdown("**Price (KD)**")
header_cols[3].markdown("**Subtotal**")
st.markdown("<hr style='margin: 4px 0 8px 0;'>", unsafe_allow_html=True)

while len(st.session_state.rows) < st.session_state.num_rows:
    st.session_state.rows.append({"description": "", "quantity": 1, "price": 0.0})

total = 0.0
for i in range(st.session_state.num_rows):
    row_cols = st.columns([4, 1.5, 2, 1])
    with row_cols[0]:
        st.session_state.rows[i]["description"] = st.text_input(
            f"desc_{i}", label_visibility="collapsed",
            placeholder="Item description",
            value=st.session_state.rows[i]["description"],
            key=f"desc_{i}"
        )
    with row_cols[1]:
        st.session_state.rows[i]["quantity"] = st.number_input(
            f"qty_{i}", label_visibility="collapsed",
            min_value=0, value=st.session_state.rows[i]["quantity"],
            key=f"qty_{i}"
        )
    with row_cols[2]:
        st.session_state.rows[i]["price"] = st.number_input(
            f"price_{i}", label_visibility="collapsed",
            min_value=0.0, format="%.3f",
            value=st.session_state.rows[i]["price"],
            key=f"price_{i}"
        )
    subtotal = st.session_state.rows[i]["quantity"] * st.session_state.rows[i]["price"]
    total += subtotal
    with row_cols[3]:
        st.markdown(f"<div style='padding: 8px 0; font-weight: 500;'>{subtotal:.3f}</div>", unsafe_allow_html=True)

# -------- TOTAL ROW --------
st.markdown("<hr style='margin: 8px 0 4px 0;'>", unsafe_allow_html=True)
total_cols = st.columns([4, 1.5, 2, 1])
total_cols[2].markdown("**TOTAL**")
total_cols[3].markdown(f"**{total:.3f} KD**")

st.markdown("")
if st.button("➕ Add Row"):
    st.session_state.num_rows += 1
    st.session_state.rows.append({"description": "", "quantity": 1, "price": 0.0})
    st.rerun()

# -------- PDF GENERATION --------
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("**📄 GENERATE INVOICE PDF**", type="primary", use_container_width=True):
        if not customer_name.strip():
            st.error("Please enter a customer name before generating the invoice.")
        elif not phone_valid:
            st.error("Please fix the phone number before generating the invoice.")
        else:
            try:
                pdf_buffer = io.BytesIO()
                c = canvas.Canvas(pdf_buffer, pagesize=A4)
                width, height = A4  # 595 x 842 pts

                # --------------------------------------------------------
                # TUNING VARIABLES — adjust these to perfect the layout
                # --------------------------------------------------------
                LOGO_W, LOGO_H      = 260, 130      # logo rendered size
                LOGO_Y              = height - 15 - LOGO_H   # logo bottom-left Y

                ARABIC_CROP_PX      = 250           # pixels cropped from TOP of arabic image
                                                    # increase → removes more white padding from top
                                                    # decrease → keeps more of the top whitespace
                ARABIC_W, ARABIC_H  = 220, 90       # arabic image rendered size
                ARABIC_GAP          = 0             # positive = move UP into logo's bottom space
                                                    # negative = move DOWN away from logo
                ARABIC_Y            = LOGO_Y + ARABIC_GAP - ARABIC_H

                TITLE_Y             = ARABIC_Y - 22  # INVOICE title position
                # --------------------------------------------------------

                # ---- LOGO ----
                logo_path = os.path.join(assets_dir, "logo.png")
                if os.path.exists(logo_path):
                    c.drawImage(
                        logo_path,
                        width / 2 - LOGO_W / 2,
                        LOGO_Y,
                        width=LOGO_W,
                        height=LOGO_H,
                        preserveAspectRatio=True,
                        mask='auto'
                    )

                # ---- ARABIC TEXT IMAGE (cropped + centered, directly below logo) ----
                arabic_path = os.path.join(assets_dir, "arabic-text.png")
                if os.path.exists(arabic_path):
                    cropped_buf = crop_top(arabic_path, crop_px=ARABIC_CROP_PX)
                    c.drawImage(
                        ImageReader(cropped_buf),
                        width / 2 - ARABIC_W / 2,
                        ARABIC_Y,
                        width=ARABIC_W,
                        height=ARABIC_H,
                        preserveAspectRatio=False,
                        mask='auto'
                    )

                # ---- INVOICE TITLE ----
                c.setFont("Helvetica-Bold", 24)
                c.drawCentredString(width / 2, TITLE_Y, "INVOICE")

                # ---- CUSTOMER INFO ----
                date_str = invoice_date.strftime("%d/%m/%Y")
                info_y = TITLE_Y - 28
                c.setFont("Helvetica", 10)

                c.drawString(50, info_y, "Date")
                c.drawString(165, info_y, ":")
                c.drawString(180, info_y, date_str)

                info_y -= 20
                c.drawString(50, info_y, "Customer Name")
                c.drawString(165, info_y, ":")
                draw_text(c, 180, info_y, customer_name, size=10)

                info_y -= 20
                c.drawString(50, info_y, "Phone Number")
                c.drawString(165, info_y, ":")
                c.setFont("Helvetica", 10)
                c.drawString(180, info_y, customer_phone if customer_phone else "-")

                # ---- DIVIDER ----
                divider_y = info_y - 14
                c.setStrokeColorRGB(0.2, 0.2, 0.2)
                c.setLineWidth(1)
                c.line(50, divider_y, width - 50, divider_y)

                # ---- TABLE HEADER ----
                table_top   = divider_y - 20
                col_desc_x  = 50
                col_qty_x   = 310
                col_price_x = 380
                col_sub_x   = 460

                c.setFillColorRGB(0.15, 0.15, 0.15)
                c.rect(50, table_top - 5, width - 100, 22, fill=1, stroke=0)
                c.setFillColorRGB(1, 1, 1)
                c.setFont("Helvetica-Bold", 10)
                c.drawString(col_desc_x + 5, table_top + 2, "Description")
                c.drawCentredString(col_qty_x + 30, table_top + 2, "Qty")
                c.drawCentredString(col_price_x + 30, table_top + 2, "Unit Price")
                c.drawCentredString(col_sub_x + 30, table_top + 2, "Subtotal")

                # ---- TABLE ROWS ----
                row_h = 22
                y = table_top - 5
                c.setFont("Helvetica", 10)

                for idx, row in enumerate(st.session_state.rows[:st.session_state.num_rows]):
                    y -= row_h
                    c.setFillColorRGB(0.97, 0.97, 0.97) if idx % 2 == 0 else c.setFillColorRGB(1, 1, 1)
                    c.rect(50, y - 3, width - 100, row_h, fill=1, stroke=0)

                    subtotal = row["quantity"] * row["price"]
                    c.setFillColorRGB(0, 0, 0)

                    # Description — auto-detects Arabic and reshapes/reorders
                    desc_text = str(row["description"])[:45]
                    draw_text(c, col_desc_x + 5, y + 4, desc_text, size=10)

                    c.setFont("Helvetica", 10)
                    c.drawCentredString(col_qty_x + 30, y + 4, str(row["quantity"]))
                    c.drawCentredString(col_price_x + 30, y + 4, f"{row['price']:.3f}")
                    c.drawCentredString(col_sub_x + 30, y + 4, f"{subtotal:.3f}")

                # ---- TOTAL ROW ----
                y -= row_h
                c.setFillColorRGB(0.15, 0.15, 0.15)
                c.rect(50, y - 3, width - 100, row_h, fill=1, stroke=0)
                c.setFillColorRGB(1, 1, 1)
                c.setFont("Helvetica-Bold", 11)
                c.drawString(col_desc_x + 5, y + 4, "TOTAL")
                c.drawCentredString(col_sub_x + 30, y + 4, f"{total:.3f} KD")

                # ---- SIGNATURE SECTION ----
                sig_top = y - 80
                if sig_top < 140:
                    sig_top = 140

                # Thin divider above signatures
                c.setStrokeColorRGB(0.7, 0.7, 0.7)
                c.setLineWidth(0.5)
                c.line(50, sig_top + 10, width - 50, sig_top + 10)

                # ---- MANAGER (left) ----
                c.setFillColorRGB(0, 0, 0)
                c.setFont("Helvetica-Bold", 11)
                c.drawString(50, sig_top - 8, "Manager")

                # Dotted signature line
                c.setStrokeColorRGB(0, 0, 0)
                c.setLineWidth(0.5)
                c.setDash(1, 3)
                c.line(50, sig_top - 28, 200, sig_top - 28)
                c.setDash()

                # sig.png — floats ABOVE the dotted line
                sig_path = os.path.join(assets_dir, "sig.png")
                if os.path.exists(sig_path):
                    SIG_W = 150
                    SIG_H = 25
                    sig_x = 65
                    sig_y = sig_top - 28 + 3
                    c.drawImage(
                        sig_path,
                        sig_x,
                        sig_y,
                        width=SIG_W,
                        height=SIG_H,
                        preserveAspectRatio=True,
                        mask='auto'
                    )

                # Logo as stamp (rotated, over manager line) — YOUR TUNED VALUES KEPT
                if os.path.exists(logo_path):
                    c.saveState()
                    c.translate(145, sig_top - 52)
                    c.rotate(15)
                    c.drawImage(logo_path, -45, -28, width=80, height=45,
                                preserveAspectRatio=True, mask='auto')
                    c.restoreState()

                # ---- CUSTOMER (right) ----
                c.setFillColorRGB(0, 0, 0)
                c.setFont("Helvetica-Bold", 11)
                c.drawRightString(width - 50, sig_top - 8, "Customer")

                # Dotted signature line
                c.setStrokeColorRGB(0, 0, 0)
                c.setLineWidth(0.5)
                c.setDash(1, 3)
                c.line(width - 200, sig_top - 28, width - 50, sig_top - 28)
                c.setDash()

                # ---- FOOTER ----
                footer_y = 55
                c.setFillColorRGB(0.5, 0.5, 0.5)
                c.setFont("Helvetica", 9)
                c.drawCentredString(width / 2, footer_y + 13, "Tel: +965-98841770")
                c.drawCentredString(width / 2, footer_y, "Email: datalabkwt@gmail.com")

                c.save()
                pdf_buffer.seek(0)

                st.download_button(
                    "**📥 DOWNLOAD INVOICE PDF**",
                    pdf_buffer,
                    file_name=f"invoice_{customer_name.replace(' ', '_')}_{date_str.replace('/', '')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

            except Exception as e:
                st.error(f"Error generating PDF: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

# -------- FOOTER --------
st.caption(f"📅 Current date: {datetime.now().strftime('%d/%m/%Y')}")