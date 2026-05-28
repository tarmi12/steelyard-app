import streamlit as st
from datetime import date

st.header("⚖️ ชั่งออก (ตัดสต็อกหน้าลานทันที)")

# จำลอง Load Orders (ภายหลังดึงจาก Supabase)
load_order_options = {
    "LO0001": {"truck": "80-1234", "product": "เหล็กเกรด A", "destination": "โรงงาน A"},
    "LO0002": {"truck": "80-5678", "product": "เหล็กเกรด B", "destination": "โรงงาน B"},
}

load_order = st.selectbox("เลือก Load Order", list(load_order_options.keys()))
if load_order:
    info = load_order_options[load_order]
    st.write(f"🚛 รถ: {info['truck']} | สินค้า: {info['product']} | ปลายทาง (ตามจอง): {info['destination']}")

st.markdown("---")

# น้ำหนักชั่ง
col1, col2, col3 = st.columns(3)
with col1:
    gross = st.number_input("น้ำหนักหนัก (Gross) kg", min_value=0, value=0)
with col2:
    tare = st.number_input("น้ำหนักเบา (Tare) kg", min_value=0, value=0)
with col3:
    net = gross - tare if gross >= tare else 0
    st.metric("น้ำหนักสุทธิ (Net)", f"{net:,} kg")

# ข้อมูลเพิ่มเติม
destination = st.selectbox("โรงงานปลายทาง (ยืนยัน)", ["โรงงาน A", "โรงงาน B", "โรงงาน C"])
arrival_date = st.date_input("วันที่ถึงปลายทาง", date.today())
remark = st.text_area("หมายเหตุ")

st.markdown("---")

if st.button("✅ Preview & บันทึก"):
    if net <= 0:
        st.error("น้ำหนักสุทธิต้องมากกว่า 0")
    else:
        # TODO: บันทึก weigh_out + ตัด Physical Stock (inventory_transactions)
        st.success(f"ชั่งออก Load Order {load_order} เรียบร้อย! ตัด Physical Stock {net} kg")
        st.balloons()

if st.button("🖨️ พิมพ์สลิปชั่งออก"):
    # TODO: พิมพ์สลิป 80mm พร้อม QR, INSERT print_logs
    st.write("พิมพ์สลิปแล้ว (จำลอง)")