import streamlit as st
from datetime import date
from supabase import create_client, Client

st.header("🔧 ปรับยอดสินค้าสต็อกด้วยมือ (เฉพาะผู้บริหาร)")
st.info("⚠️ การปรับยอดตรงนี้จะส่งผลต่อยอดคงเหลือสุทธิทันที และจะถูกบันทึกประวัติผู้ทำรายการไว้ตรวจสอบย้อนหลัง")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

with st.form("real_adjustment_form"):
    col1, col2 = st.columns(2)
    with col1:
        stock_type = st.radio("เลือกประเภทสต็อกที่ต้องการปรับปรุง", ["PHYSICAL", "REPORTING"],
                              format_func=lambda x: "🔴 สต็อกกองจริงหน้าลาน (Physical)" if x=="PHYSICAL" else "🔵 สต็อกทางบัญชี/ภาษี (Reporting)")
    with col2:
        adj_type = st.radio("รูปแบบการปรับปรุง", ["PLUS", "MINUS"],
                            format_func=lambda x: "➕ ปรับเพิ่มสต็อก (บวกเข้า)" if x=="PLUS" else "➖ ปรับลดสต็อก (หักออก)")

    adj_qty = st.number_input("จำนวนน้ำหนักเหล็กที่ต้องการปรับ (กิโลกรัม) *", min_value=1, step=1)
    reason = st.text_area("ระบุสาเหตุหรือเหตุผลในการปรับปรุงยอดสต็อกครั้งนี้ *")
    adj_date = st.date_input("วันที่ปรับยอด", date.today())

    submitted = st.form_submit_button("⚙️ ยืนยันการปรับยอดสต็อกจริง")
    if submitted:
        if not reason.strip():
            st.error("❌ กรุณาระบุสาเหตุในการปรับยอดสต็อกเพื่อใช้เป็นหลักฐาน")
        else:
            # แปลงค่าเป็นบวกหรือลบตามเงื่อนไขที่เลือก
            final_qty = adj_qty if adj_type == "PLUS" else -adj_qty
            
            try:
                # 1. บันทึกเข้าตารางหลักฐานการปรับมือ
                adj_res = supabase.table("manual_adjustments").insert({
                    "stock_type": stock_type,
                    "adjustment_quantity": final_qty,
                    "reason": reason,
                    "adjustment_date": str(adj_date),
                    "created_by": st.session_state.user_id
                }).execute()
                
                adj_id = adj_res.data[0]["id"]
                
                # 2. บันทึกเข้าตารางประวัติธุรกรรมสต็อกคู่เพื่อให้น้ำหนักเปลี่ยนทันที
                supabase.table("inventory_transactions").insert({
                    "stock_type": stock_type,
                    "transaction_type": "ADJUSTMENT",
                    "quantity": final_qty,
                    "unit_cost": 0.0,
                    "reference_type": "MANUAL_ADJUSTMENT",
                    "reference_id": adj_id,
                    "transaction_date": str(adj_date),
                    "created_by": st.session_state.user_id
                }).execute()
                
                st.success("🎉 บันทึกการปรับยอดสต็อกด้วยมือและอัปเดตประวัติธุรกรรมเรียบร้อยแล้ว!")
                st.rerun()
            except Exception as e:
                st.error(f"ไม่สามารถปรับยอดสต็อกได้: {e}")