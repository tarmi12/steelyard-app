import streamlit as st
from datetime import date

st.header("💰 เคลียร์บิลปลายทาง (เปรียบเทียบน้ำหนักต้นทาง-ปลายทาง)")

weigh_out_options = [
    {"id": "WO0001", "load_order": "LO0001", "truck": "80-1234", "product": "เหล็กเกรด A",
     "gross_origin": 21000, "tare_origin": 5700, "net_origin": 15300, "destination": "โรงงาน A", "date": date.today()},
    {"id": "WO0002", "load_order": "LO0002", "truck": "80-5678", "product": "เหล็กเกรด B",
     "gross_origin": 22000, "tare_origin": 5800, "net_origin": 16200, "destination": "โรงงาน B", "date": date.today()},
]
wo_dict = {f"{wo['id']} ({wo['truck']})": wo for wo in weigh_out_options}

selected_wo_label = st.selectbox("เลือก Weigh Out ที่ต้องการเคลียร์บิล", list(wo_dict.keys()))
selected_wo = wo_dict[selected_wo_label]

st.subheader("🚛 ข้อมูลต้นทาง (Weigh Out)")
col1, col2, col3, col4 = st.columns(4)
col1.metric("ทะเบียนรถ", selected_wo["truck"])
col2.metric("สินค้า", selected_wo["product"])
col3.metric("โรงงานปลายทาง", selected_wo["destination"])
col4.metric("วันที่ชั่งออก", str(selected_wo["date"]))

st.markdown("---")
st.subheader("⚖️ เปรียบเทียบน้ำหนักต้นทาง – ปลายทาง")

with st.form("sales_clearing_form"):
    st.write("**น้ำหนัก ณ ต้นทาง (ลานเหล็กไทย)**")
    col_o1, col_o2, col_o3 = st.columns(3)
    col_o1.metric("Gross (kg)", f"{selected_wo['gross_origin']:,}")
    col_o2.metric("Tare (kg)", f"{selected_wo['tare_origin']:,}")
    col_o3.metric("Net (kg)", f"{selected_wo['net_origin']:,}")

    st.write("**น้ำหนัก ณ ปลายทาง (กรอกจากใบชั่งโรงงาน)**")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        gross_dest = st.number_input("Gross ปลายทาง (kg)", min_value=0, value=20000)
    with col_d2:
        tare_dest = st.number_input("Tare ปลายทาง (kg)", min_value=0, value=5500)
    net_dest = gross_dest - tare_dest if gross_dest >= tare_dest else 0
    st.metric("Net ปลายทาง (kg)", f"{net_dest:,}")

    transit_loss = selected_wo["net_origin"] - net_dest
    if transit_loss >= 0:
        st.warning(f"🚨 น้ำหนักหายระหว่างทาง: {transit_loss:,} kg")
    else:
        st.success(f"✅ น้ำหนักเพิ่มขึ้น: {abs(transit_loss):,} kg")

    impurity_kg = st.number_input("น้ำหนักสิ่งเจือปน (kg) (หักจาก Net ปลายทาง)", min_value=0, value=0, step=10)
    net_billable = max(net_dest - impurity_kg, 0)
    st.metric("น้ำหนักสุทธิที่คิดเงิน (Net Billable)", f"{net_billable:,} kg")

    remarks = st.text_area("หมายเหตุ (สาเหตุน้ำหนักหาย / ข้อมูลเพิ่มเติม)")

    sale_type = st.radio("ประเภทบิล (VAT)", ["ปกติ (มี VAT)", "นอกระบบ (No VAT)"])
    price_per_ton = st.number_input("ราคาขายต่อตัน (บาท)", min_value=0.0, value=8000.0, step=100.0)
    discount = st.number_input("ส่วนลด (บาท)", min_value=0.0, value=0.0)

    total_amount = (net_billable / 1000) * price_per_ton - discount
    vat_amount = 0
    if sale_type == "ปกติ (มี VAT)":
        vat_amount = round(total_amount * 0.07, 2)
    grand_total = total_amount + vat_amount

    st.markdown("---")
    st.subheader("📋 ตัวอย่างก่อนบันทึก (Preview)")
    col_p1, col_p2, col_p3 = st.columns(3)
    col_p1.metric("มูลค่าก่อน VAT", f"{total_amount:,.2f} บาท")
    col_p2.metric("VAT (7%)", f"{vat_amount:,.2f} บาท")
    col_p3.metric("รวมสุทธิ", f"{grand_total:,.2f} บาท")

    submitted = st.form_submit_button("✅ ยืนยันเคลียร์บิล")
    if submitted:
        # TODO: บันทึก sales_clearing, destination_weigh_in, inventory_transactions
        st.success(f"เคลียร์บิล {selected_wo['id']} เรียบร้อย!")
        st.balloons()

if st.button("🖨️ พิมพ์ใบเคลียร์บิล"):
    st.write("พิมพ์เอกสาร (จำลอง)")