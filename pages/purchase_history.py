import streamlit as st
import pandas as pd
from datetime import date

st.header("📋 ประวัติการซื้อ")

# ตัวอย่างข้อมูล (ภายหลังดึงจาก Supabase)
demo_data = [
    {"เลขที่บิล": "P0001", "วันที่": "2026-05-27", "รายการ": 2, "Physical kg": 1520, "Reporting kg": 1200},
    {"เลขที่บิล": "P0002", "วันที่": "2026-05-26", "รายการ": 1, "Physical kg": 800, "Reporting kg": 800},
]
df = pd.DataFrame(demo_data)

# ค้นหาตามช่วงวันที่
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("วันที่เริ่มต้น", date.today().replace(day=1))
with col2:
    end_date = st.date_input("วันที่สิ้นสุด", date.today())

# ในอนาคตใช้ Supabase Query กรองตามวันที่
st.dataframe(df, use_container_width=True)

# ปุ่มดูรายละเอียด
if st.button("🔍 ดูรายละเอียด"):
    st.subheader("รายละเอียดใบซื้อ (ตัวอย่าง)")
    detail = pd.DataFrame([
        {"ประเภท": "เหล็กเกรด A", "Physical kg": 1000, "Reporting kg": 800, "ราคา/ตัน Phys": 8500, "ราคา/ตัน Rep": 8500},
        {"ประเภท": "เหล็กเกรด B", "Physical kg": 520, "Reporting kg": 400, "ราคา/ตัน Phys": 4000, "ราคา/ตัน Rep": 4000}
    ])
    st.table(detail)

# ปุ่มพิมพ์ซ้ำ
if st.button("🖨️ พิมพ์ซ้ำ"):
    # TODO: INSERT print_logs, ระบุ reference_id
    st.write("พิมพ์เอกสารใหม่เรียบร้อย (จำลอง)")