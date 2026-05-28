import streamlit as st
from datetime import date

st.header("🚛 จ่ายค่าขนส่งให้สิบล้อ")

# ตัวอย่างรายการ Load Orders ที่ถึงปลายทางและยังไม่จ่ายค่าขนส่ง (ภายหลังดึงจาก Supabase)
demo_data = [
    {"Load Order": "LO0001", "ทะเบียน": "80-1234", "คนขับ": "สมชาย", "น้ำหนักต้นทาง (kg)": 10000, "น้ำหนักปลายทาง (kg)": 9900,
     "Transit Loss (kg)": 100, "ค่าปรับ (บาท)": 150, "ค่าขนส่ง (บาท)": 3000, "สุทธิ (บาท)": 2850},
    {"Load Order": "LO0002", "ทะเบียน": "80-5678", "คนขับ": "สมหญิง", "น้ำหนักต้นทาง (kg)": 8500, "น้ำหนักปลายทาง (kg)": 8450,
     "Transit Loss (kg)": 50, "ค่าปรับ (บาท)": 0, "ค่าขนส่ง (บาท)": 3200, "สุทธิ (บาท)": 3200},
]

st.subheader("รายการที่รอจ่ายค่าขนส่ง")
st.dataframe(demo_data, use_container_width=True)

st.markdown("---")
st.subheader("จ่ายค่าขนส่ง (เลือกทีละรายการหรือหลายรายการ)")

selected_orders = st.multiselect("เลือก Load Order ที่จะจ่าย", [d["Load Order"] for d in demo_data])

if selected_orders:
    total_pay = sum(d["สุทธิ (บาท)"] for d in demo_data if d["Load Order"] in selected_orders)
    st.write(f"รวมค่าขนส่งสุทธิที่ต้องจ่าย: **{total_pay:,.2f} บาท**")

    pay_method = st.radio("วิธีจ่าย", ["เงินสด", "โอน"], horizontal=True)
    bank_ref = ""
    if pay_method == "โอน":
        bank_ref = st.text_input("เลขที่อ้างอิงการโอน")

    pay_date = st.date_input("วันที่จ่าย", date.today())

    if st.button("✅ ยืนยันการจ่าย"):
        # TODO: อัปเดต freight_payments, เปลี่ยนสถานะเป็น PAID
        st.success(f"จ่ายค่าขนส่ง {len(selected_orders)} รายการ รวม {total_pay:,.2f} บาท เรียบร้อย!")
else:
    st.info("เลือกรายการที่ต้องการจ่ายค่าขนส่ง")

if st.button("🖨️ พิมพ์ใบสำคัญจ่าย"):
    st.write("พิมพ์ใบสำคัญจ่ายแล้ว (จำลอง)")