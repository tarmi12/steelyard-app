import streamlit as st

st.header("🚘 จัดการรถ/คนขับ")

st.subheader("เพิ่ม / แก้ไข ข้อมูลรถ")

with st.form("truck_form"):
    plate = st.text_input("ทะเบียนรถ")
    driver = st.text_input("ชื่อคนขับ")
    phone = st.text_input("เบอร์โทร")
    company = st.text_input("บริษัทขนส่ง")
    empty_weight = st.number_input("น้ำหนักเบารถ (kg)", min_value=0, step=10)
    freight_method = st.radio("วิธีคิดค่าขนส่งเริ่มต้น", ["เหมาเที่ยว", "บาทต่อตัน"], index=0)

    if st.form_submit_button("บันทึก"):
        # TODO: INSERT/UPDATE trucks ใน Supabase
        st.success(f"บันทึกข้อมูลรถ {plate} เรียบร้อย!")

st.markdown("---")
st.subheader("รายการรถทั้งหมด (ตัวอย่าง)")
trucks = [
    {"ทะเบียน": "80-1234", "คนขับ": "สมชาย", "เบอร์": "081-234-5678", "บริษัท": "สมชายขนส่ง", "น้ำหนักเบา": 5000, "วิธีคิด": "เหมาเที่ยว"},
    {"ทะเบียน": "80-5678", "คนขับ": "สมหญิง", "เบอร์": "089-876-5432", "บริษัท": "สมหญิงโลจิสติกส์", "น้ำหนักเบา": 4800, "วิธีคิด": "เหมาเที่ยว"},
]
st.table(trucks)