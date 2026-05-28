import streamlit as st
from datetime import date

st.header("💰 เคลียร์บิลปลายทาง (คำนวณเงิน, เลือก VAT/No VAT)")

# จำลองรายการ Weigh Out ที่รอเคลียร์ (ภายหลังดึงจาก Supabase)
weigh_out_options = {
    "WO0001": {"load_order": "LO0001", "net_weight": 10000, "truck": "80-1234", "destination": "โรงงาน A"},
    "WO0002": {"load_order": "LO0002", "net_weight": 8500, "truck": "80-5678", "destination": "โรงงาน B"},
}

selected_wo = st.selectbox("เลือก Weigh Out", list(weigh_out_options.keys()))
if selected_wo:
    wo = weigh_out_options[selected_wo]
    st.write(f"🚛 {wo['truck']} | น้ำหนักต้นทาง: {wo['net_weight']:,} kg | ปลายทาง: {wo['destination']}")

st.markdown("---")

# ข้อมูลจากปลายทาง (อาจดึงจาก destination_weigh_in)
dest_weight = st.number_input("น้ำหนักปลายทาง (kg)", min_value=0, step=10)
impurity_pct = st.number_input("% สิ่งเจือปน", min_value=0.0, max_value=100.0, step=0.1, value=0.0)
net_billable = dest_weight * (1 - impurity_pct / 100) if dest_weight > 0 else 0
st.metric("น้ำหนักสุทธิที่คิดเงิน (Net Billable)", f"{net_billable:,.2f} kg")

# ราคา
final_price_per_ton = st.number_input("ราคาขายสุทธิต่อตัน (บาท)", min_value=0.0, step=100.0, value=8000.0)
discount = st.number_input("ส่วนลด (บาท)", min_value=0.0, step=100.0, value=0.0)

# ประเภทบิล
sale_type = st.radio("ประเภทบิล", ["ปกติ (มี VAT 7%)", "นอกระบบ (No VAT)"])
vat_mode = "NORMAL" if sale_type.startswith("ปกติ") else "NO_VAT"

# คำนวณ
if net_billable > 0:
    total_amount = (net_billable / 1000) * final_price_per_ton - discount
    vat_amount = total_amount * 0.07 if vat_mode == "NORMAL" else 0
    grand_total = total_amount + vat_amount if vat_mode == "NORMAL" else total_amount

    st.markdown("---")
    st.subheader("📊 สรุปก่อนบันทึก")
    st.write(f"น้ำหนักสุทธิคิดเงิน: {net_billable:,.2f} kg")
    st.write(f"มูลค่าก่อน VAT: {total_amount:,.2f} บาท")
    if vat_mode == "NORMAL":
        st.write(f"VAT 7%: {vat_amount:,.2f} บาท")
    st.write(f"**รวมทั้งสิ้น: {grand_total:,.2f} บาท**")
    st.write(f"ประเภทบิล: {sale_type}")

    if st.button("✅ ยืนยันเคลียร์บิล"):
        # TODO: บันทึก sales_clearing, ถ้า NORMAL ตัด REPORTING stock, ถ้า NO_VAT ไม่ตัด
        # TODO: คำนวณ transit loss, penalty ในภายหลัง
        st.success("บันทึกเคลียร์บิลเรียบร้อย!")
        st.balloons()
else:
    st.info("กรุณากรอกน้ำหนักปลายทางและสิ่งเจือปนเพื่อคำนวณ")