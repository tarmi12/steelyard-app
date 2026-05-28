import streamlit as st
from datetime import date

st.header("📥 บันทึกซื้อเข้าสิ้นวัน (เพิ่มสต็อก Physical / Reporting แยกตามเกรด)")

# ชนิดสินค้าตัวอย่าง (ภายหลังดึงจาก product_types)
product_types = ["เหล็กเกรด A", "เหล็กเกรด B", "เศษเหล็กผสม"]

with st.form("purchase_entry_form"):
    purchase_date = st.date_input("วันที่ซื้อ", date.today())
    st.markdown("---")

    if "purchase_rows" not in st.session_state:
        st.session_state.purchase_rows = []

    add_row = st.form_submit_button("➕ เพิ่มแถวสินค้า")
    if add_row:
        st.session_state.purchase_rows.append({
            "product": product_types[0],
            "physical_weight": 0,
            "physical_price": 0.0,
            "reporting_weight": 0,
            "reporting_price": 0.0
        })
        st.rerun()

    for i, row in enumerate(st.session_state.purchase_rows):
        cols = st.columns([2, 1.2, 1.2, 1.2, 1.2, 0.8])
        with cols[0]:
            row["product"] = st.selectbox("ประเภท", product_types, key=f"prod_{i}")
        with cols[1]:
            row["physical_weight"] = st.number_input("นน.Physical (kg)", min_value=0, step=100, key=f"pw_{i}", value=row["physical_weight"])
        with cols[2]:
            row["physical_price"] = st.number_input("ราคา/ตัน Phys", min_value=0.0, step=10.0, key=f"pp_{i}", value=row["physical_price"])
        with cols[3]:
            row["reporting_weight"] = st.number_input("นน.Reporting (kg)", min_value=0, step=100, key=f"rw_{i}", value=row["reporting_weight"])
        with cols[4]:
            row["reporting_price"] = st.number_input("ราคา/ตัน Rep", min_value=0.0, step=10.0, key=f"rp_{i}", value=row["reporting_price"])
        with cols[5]:
            if st.form_submit_button("🗑️", key=f"del_{i}"):
                del st.session_state.purchase_rows[i]
                st.rerun()

    st.markdown("---")

    preview_btn = st.form_submit_button("🔍 ตรวจสอบข้อมูล (Preview)")
    if preview_btn:
        if not st.session_state.purchase_rows:
            st.warning("กรุณาเพิ่มรายการสินค้าอย่างน้อย 1 รายการ")
        else:
            st.subheader("📋 ตัวอย่างข้อมูลก่อนบันทึก")
            total_phys_kg = sum(r["physical_weight"] for r in st.session_state.purchase_rows)
            total_rep_kg = sum(r["reporting_weight"] for r in st.session_state.purchase_rows)
            st.write(f"**วันที่ซื้อ:** {purchase_date}  |  **รายการ:** {len(st.session_state.purchase_rows)}")
            st.dataframe(
                [{
                    "ประเภท": r["product"],
                    "Physical kg": r["physical_weight"],
                    "ราคา/ตัน": r["physical_price"],
                    "Reporting kg": r["reporting_weight"],
                    "ราคา/ตัน": r["reporting_price"]
                } for r in st.session_state.purchase_rows]
            )
            st.info(f"รวม Physical: {total_phys_kg:,} กก.  |  Reporting: {total_rep_kg:,} กก.")
            st.warning("กรุณากด 'ยืนยันบันทึก' เพื่อบันทึกจริง")

    confirm_btn = st.form_submit_button("✅ ยืนยันบันทึกข้อมูล")
    if confirm_btn:
        if not st.session_state.purchase_rows:
            st.error("ไม่มีรายการสินค้า")
        else:
            # TODO: INSERT purchase_orders + purchase_lines + inventory_transactions
            st.success(f"บันทึกใบซื้อวันที่ {purchase_date} เรียบร้อย! (เพิ่มสต็อกทั้ง 2 ถัง)")
            st.balloons()
            st.session_state.purchase_rows = []
            st.rerun()

if st.button("🖨️ พิมพ์สลิปสรุปการซื้อ"):
    # TODO: INSERT print_logs
    st.write("พิมพ์สลิปแล้ว (จำลอง)")