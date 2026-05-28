import streamlit as st
from datetime import date

st.markdown("""
<style>
    .phys-input input {
        background-color: #ffe6e6 !important;
        border: 1px solid #cc0000;
    }
    .rep-input input {
        background-color: #e6f0ff !important;
        border: 1px solid #0044cc;
    }
</style>
""", unsafe_allow_html=True)

st.header("📥 บันทึกซื้อเข้าสิ้นวัน (เพิ่มสต็อก Physical / Reporting แยกตามเกรด)")
st.info("🔴 **สีแดง** = Physical | 🔵 **สีน้ำเงิน** = Reporting (ตรวจสอบให้ดีก่อนบันทึก)")

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
            st.markdown('<div class="phys-input">', unsafe_allow_html=True)
            row["physical_weight"] = st.number_input("🔴 นน.Physical (kg)", min_value=0, step=100, key=f"pw_{i}", value=row["physical_weight"])
            st.markdown('</div>', unsafe_allow_html=True)
        with cols[2]:
            st.markdown('<div class="phys-input">', unsafe_allow_html=True)
            row["physical_price"] = st.number_input("🔴 ราคา/ตัน Phys", min_value=0.0, step=10.0, key=f"pp_{i}", value=row["physical_price"])
            st.markdown('</div>', unsafe_allow_html=True)

        with cols[3]:
            st.markdown('<div class="rep-input">', unsafe_allow_html=True)
            row["reporting_weight"] = st.number_input("🔵 นน.Reporting (kg)", min_value=0, step=100, key=f"rw_{i}", value=row["reporting_weight"])
            st.markdown('</div>', unsafe_allow_html=True)
        with cols[4]:
            st.markdown('<div class="rep-input">', unsafe_allow_html=True)
            row["reporting_price"] = st.number_input("🔵 ราคา/ตัน Rep", min_value=0.0, step=10.0, key=f"rp_{i}", value=row["reporting_price"])
            st.markdown('</div>', unsafe_allow_html=True)

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
            total_phys_kg = sum(r["physical_weight"] for r in st.session_state.purchase_rows)
            total_rep_kg = sum(r["reporting_weight"] for r in st.session_state.purchase_rows)
            st.subheader("📋 ตัวอย่างข้อมูลก่อนบันทึก")
            st.write(f"**วันที่ซื้อ:** {purchase_date}  |  **รายการ:** {len(st.session_state.purchase_rows)}")
            st.dataframe([{
                "ประเภท": r["product"],
                "🔴 Phys kg": r["physical_weight"],
                "🔴 ราคา/t": r["physical_price"],
                "🔵 Rep kg": r["reporting_weight"],
                "🔵 ราคา/t": r["reporting_price"]
            } for r in st.session_state.purchase_rows])
            st.info(f"รวม Physical: {total_phys_kg:,} กก.  |  Reporting: {total_rep_kg:,} กก.")
            st.warning("กรุณากด 'ยืนยันบันทึก' เพื่อบันทึกจริง")

    confirm_btn = st.form_submit_button("✅ ยืนยันบันทึกข้อมูล")
    if confirm_btn:
        if not st.session_state.purchase_rows:
            st.error("ไม่มีรายการสินค้า")
        else:
            # TODO: INSERT purchase_orders + purchase_lines + inventory_transactions
            st.success(f"บันทึกใบซื้อวันที่ {purchase_date} เรียบร้อย!")
            st.balloons()
            st.session_state.purchase_rows = []
            st.rerun()

if st.button("🖨️ พิมพ์สลิปสรุปการซื้อ"):
    st.write("พิมพ์สลิปแล้ว (จำลอง)")