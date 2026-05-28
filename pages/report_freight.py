import streamlit as st
from datetime import date

st.header("📉 รายงานค่าขนส่ง/ค่าปรับ")

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("วันที่เริ่มต้น", date.today().replace(day=1))
with col2:
    end_date = st.date_input("วันที่สิ้นสุด", date.today())

st.markdown("---")

# ตัวอย่างข้อมูล
freight_data = [
    {"วันที่": "2026-05-27", "ทะเบียน": "80-1234", "ค่าขนส่ง": 3000, "ค่าปรับ": 150, "สุทธิ": 2850, "รูปแบบ": "เหมาเที่ยว"},
    {"วันที่": "2026-05-28", "ทะเบียน": "80-5678", "ค่าขนส่ง": 3200, "ค่าปรับ": 0, "สุทธิ": 3200, "รูปแบบ": "เหมาเที่ยว"},
    {"วันที่": "2026-05-29", "ทะเบียน": "80-9999", "ค่าขนส่ง": 3150, "ค่าปรับ": 100, "สุทธิ": 3050, "รูปแบบ": "บาทต่อตัน (ต้นทาง)"},
]
st.dataframe(freight_data, use_container_width=True)

total_freight = sum(d["ค่าขนส่ง"] for d in freight_data)
total_penalty = sum(d["ค่าปรับ"] for d in freight_data)
total_net = sum(d["สุทธิ"] for d in freight_data)

st.markdown(f"**รวมค่าขนส่ง:** {total_freight:,} บาท  |  **รวมค่าปรับ:** {total_penalty:,} บาท  |  **รวมจ่ายจริง:** {total_net:,} บาท")

if st.button("🖨️ พิมพ์รายงาน"):
    st.write("พิมพ์รายงานค่าขนส่ง (A4)")