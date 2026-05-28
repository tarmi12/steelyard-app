import streamlit as st

st.header("⚙️ ตั้งค่าระบบ (เจ้าของเท่านั้น)")

st.subheader("เกณฑ์น้ำหนักขาดระหว่างขนส่ง")
transit_loss_pct = st.number_input("เกณฑ์ % ที่ยอมรับได้", min_value=0.0, max_value=100.0, value=0.5, step=0.1)
transit_loss_kg = st.number_input("เกณฑ์น้ำหนักสูงสุด (kg)", min_value=0, value=50, step=10)

st.subheader("ค่าขนส่งเริ่มต้น")
freight_flat_rate = st.number_input("อัตราเหมาเที่ยว (บาท)", min_value=0.0, value=3000.0, step=100.0)
freight_per_ton_rate = st.number_input("อัตราต่อตัน (บาท)", min_value=0.0, value=100.0, step=10.0)
base_weight_option = st.radio("ฐานน้ำหนักเริ่มต้นสำหรับคิดค่าขนส่งแบบต่อตัน", ["ต้นทาง", "ปลายทาง"], index=0)

st.subheader("ข้อมูลบริษัท (สำหรับเอกสาร)")
company_name = st.text_input("ชื่อบริษัท", "บริษัท ลานเหล็กไทย จำกัด")
company_address = st.text_area("ที่อยู่", "123 หมู่ 4 ต.บางปู อ.เมือง จ.สมุทรปราการ")

if st.button("💾 บันทึกการตั้งค่า"):
    # TODO: บันทึกใน system_settings หรือตารางอื่นๆ
    st.success("บันทึกการตั้งค่าระบบเรียบร้อย!")