import streamlit as st
from datetime import date
import qrcode
from io import BytesIO
from PIL import Image

st.header("⚖️ ชั่งออก (ตัดสต็อกหน้าลานทันที)")

load_orders = ["LO0001", "LO0002"]
selected_lo = st.selectbox("เลือก Load Order", load_orders)
if selected_lo:
    st.write("รถ: 80-1234 | สินค้า: เหล็กเกรด A | ปลายทาง: โรงงาน A")

col1, col2, col3 = st.columns(3)
with col1:
    gross = st.number_input("น้ำหนักหนัก (Gross) kg", min_value=0, value=15000)
with col2:
    tare = st.number_input("น้ำหนักเบา (Tare) kg", min_value=0, value=5000)
with col3:
    net = gross - tare if gross >= tare else 0
    st.metric("น้ำหนักสุทธิ (Net)", f"{net:,} kg")

destination = st.selectbox("โรงงานปลายทาง", ["โรงงาน A", "โรงงาน B", "โรงงาน C"])
arrival_date = st.date_input("วันที่ถึงปลายทาง", date.today())
remark = st.text_area("หมายเหตุ")

if st.button("Preview & บันทึก"):
    # TODO: บันทึก weigh_out, ตัด Physical Stock
    st.success("ชั่งออกเรียบร้อย ตัด Physical Stock แล้ว")
    st.session_state.weigh_out_id = selected_lo + "_WO001"
    st.session_state.print_ready = True

if st.session_state.get("print_ready"):
    st.markdown("---")
    st.subheader("🖨️ สลิปชั่งออก (80mm)")

    line_url = st.session_state.get("line_oa_url", "https://line.me/R/ti/p/@your_bot_id")
    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(line_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    st.image(buf, width=200, caption="สแกนเพื่อส่งหลักฐานปลายทางผ่าน LINE")

    st.write(f"**เลขเอกสาร:** {st.session_state.weigh_out_id}")
    st.write(f"**ทะเบียน:** 80-1234")
    st.write(f"**น้ำหนักสุทธิ:** {net:,} kg")
    st.write(f"**ปลายทาง:** {destination}")
    st.write(f"**วันที่ถึง:** {arrival_date}")
    st.write(f"**หมายเหตุ:** {remark}")

    if st.button("พิมพ์สลิปอีกครั้ง"):
        st.write("พิมพ์...")

    if st.button("เสร็จสิ้น"):
        st.session_state.print_ready = False
        st.session_state.weigh_out_id = None
        st.rerun()