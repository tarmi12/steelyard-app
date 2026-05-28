import streamlit as st
from datetime import date

# =====================================================
# 💰 เคลียร์บิลปลายทาง (Sales Clearing)
# =====================================================
st.header("💰 เคลียร์บิลปลายทาง (คำนวณเงิน, ตรวจสอบน้ำหนักหาย)")

# --- จำลองรายการ Weigh Out ที่ยังไม่ได้เคลียร์ (ภายหลังดึงจาก Supabase) ---
weigh_out_options = [
    {"id": "WO0001", "load_order": "LO0001", "truck": "80-1234", "product": "เหล็กเกรด A",
     "net_origin": 15300, "destination": "โรงงาน A", "date": date.today()},
    {"id": "WO0002", "load_order": "LO0002", "truck": "80-5678", "product": "เหล็กเกรด B",
     "net_origin": 16200, "destination": "โรงงาน B", "date": date.today()},
]
wo_dict = {f"{wo['id']} ({wo['truck']})": wo for wo in weigh_out_options}

selected_wo_label = st.selectbox("เลือก Weigh Out ที่ต้องการเคลียร์บิล", list(wo_dict.keys()))
selected_wo = wo_dict[selected_wo_label]

# แสดงข้อมูลต้นทาง
col1, col2, col3 = st.columns(3)
col1.metric("ทะเบียนรถ", selected_wo["truck"])
col2.metric("สินค้า", selected_wo["product"])
col3.metric("น้ำหนักสุทธิต้นทาง (Net Origin)", f"{selected_wo['net_origin']:,} kg")

st.markdown("---")
st.subheader("ข้อมูลปลายทาง (ชั่งที่โรงงาน)")

with st.form("sales_clearing_form"):
    col_dest1, col_dest2 = st.columns(2)
    with col_dest1:
        gross_dest = st.number_input("น้ำหนักเข้า (Gross) ปลายทาง (kg)", min_value=0, value=15000)
    with col_dest2:
        tare_dest = st.number_input("น้ำหนักออก (Tare) ปลายทาง (kg)", min_value=0, value=5000)

    net_dest = gross_dest - tare_dest if gross_dest >= tare_dest else 0
    st.metric("น้ำหนักสุทธิปลายทาง (Net Destination)", f"{net_dest:,} kg")

    # Transit Loss
    transit_loss = selected_wo["net_origin"] - net_dest if selected_wo["net_origin"] >= net_dest else 0
    st.write(f"🚚 **Transit Loss:** {transit_loss:,} kg  (หายระหว่างทาง)")

    # Impurity
    impurity_pct = st.number_input("% สิ่งเจือปน (Impurity)", min_value=0.0, max_value=100.0, step=0.1, value=0.0)
    net_billable = net_dest * (1 - impurity_pct / 100) if net_dest > 0 else 0
    st.metric("น้ำหนักสุทธิที่คิดเงิน (Net Billable)", f"{net_billable:,.0f} kg")

    # ราคาและภาษี
    sale_type = st.radio("ประเภทบิล (VAT)", ["ปกติ (มี VAT)", "นอกระบบ (No VAT)"])
    price_per_ton = st.number_input("ราคาขายต่อตัน (บาท)", min_value=0.0, value=8000.0, step=100.0)
    discount = st.number_input("ส่วนลด (บาท)", min_value=0.0, value=0.0)

    # คำนวณเงิน
    total_amount = (net_billable / 1000) * price_per_ton - discount
    vat_amount = 0
    if sale_type == "ปกติ (มี VAT)":
        vat_amount = round(total_amount * 0.07, 2)
    grand_total = total_amount + vat_amount

    st.markdown("---")
    st.subheader("📋 ตัวอย่างข้อมูลก่อนบันทึก (Preview)")
    col_prev1, col_prev2, col_prev3 = st.columns(3)
    col_prev1.metric("มูลค่าก่อน VAT", f"{total_amount:,.2f} บาท")
    col_prev2.metric("VAT (7%)", f"{vat_amount:,.2f} บาท")
    col_prev3.metric("รวมสุทธิ", f"{grand_total:,.2f} บาท")

    # ปุ่มยืนยัน
    submitted = st.form_submit_button("✅ ยืนยันเคลียร์บิล")
    if submitted:
        # TODO: บันทึก sales_clearing, เพิ่ม inventory_transactions (REPORTING ถ้ามี VAT)
        # และบันทึก destination_weigh_in ถ้ายังไม่มี
        st.success(f"เคลียร์บิล {selected_wo['id']} เรียบร้อย!")
        st.balloons()

# ปุ่มพิมพ์ (นอกฟอร์ม)
if st.button("🖨️ พิมพ์ใบเคลียร์บิล"):
    st.write("พิมพ์เอกสาร (จำลอง)")