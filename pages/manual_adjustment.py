import streamlit as st
from datetime import date

st.header("🔧 ปรับยอดสต็อกด้วยมือ (เฉพาะผู้จัดการ/เจ้าของ)")

st.warning("การปรับยอดนี้จะถูกบันทึกถาวรและมีผลต่อบัญชี")

stock_type = st.radio("ประเภทสต็อกที่ต้องการปรับ", ["Physical", "Reporting"])

adjustment_qty = st.number_input("จำนวนที่ปรับ (kg) ใส่ติดลบเพื่อลด", value=0, step=100)
reason = st.text_area("เหตุผลการปรับยอด")

adjustment_date = st.date_input("วันที่ปรับ", date.today())

if st.button("✅ Preview & ยืนยัน"):
    if adjustment_qty == 0:
        st.error("กรุณาระบุจำนวนที่ปรับ (ไม่ใช่ 0)")
    else:
        st.subheader("สรุปก่อนบันทึก")
        st.write(f"ประเภท: {stock_type}")
        st.write(f"จำนวน: {adjustment_qty:+,} kg")
        st.write(f"เหตุผล: {reason}")
        st.write(f"วันที่: {adjustment_date}")
        st.info("กดยืนยันอีกครั้งเพื่อบันทึก")

        if st.button("ยืนยันบันทึกการปรับยอด"):
            # TODO: INSERT manual_adjustments + inventory_transactions
            st.success("ปรับยอดสต็อกเรียบร้อย!")
            st.rerun()