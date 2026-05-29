import streamlit as st
from datetime import date
from supabase import create_client, Client

st.header("💵 ตรวจสอบและบันทึกเงินโอนจากโรงงาน (ปิดยอดลูกหนี้)")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# ---- 1. ดึงรายการเคลียร์บิลที่ "ยังไม่ได้รับเงิน" หรือค้างจ่าย ----
try:
    # ดึงรายการ sales_clearing ทั้งหมด
    clearing_res = supabase.table("sales_clearing").select("id, weigh_out_id, total_amount, vat_amount, clearing_date, weigh_out(load_orders(trucks(plate)), factories(name))").execute()
    
    # ดึงรายการที่รับเงินไปแล้วในตาราง receipts
    receipts_res = supabase.table("receipts").select("sales_clearing_id").eq("status", "RECEIVED").execute()
    paid_clearing_ids = [r["sales_clearing_id"] for r in receipts_res.data]
    
    # กรองเฉพาะรายการที่ยังไม่ได้รับเงิน
    unpaid_bills = {
        f"บิลเคลียร์ยอด SC-{c['id']} | รถ {c['weigh_out']['load_orders']['trucks']['plate']} ({c['weigh_out']['factories']['name']}) - ยอด {float(c['total_amount'])+float(c['vat_amount']):,.2f} บาท": c
        for c in clearing_res.data if c["id"] not in paid_clearing_ids
    }
except Exception as e:
    st.error(f"ไม่สามารถดึงข้อมูลบิลค้างรับเงินได้: {e}")
    unpaid_bills = {}

# ---- 2. แสดงรายการและฟอร์มบันทึกเงินโอน ----
if not unpaid_bills:
    st.success("✅ ยอดเยี่ยม! โรงงานปลายทางชำระเงินครบทุกบิลแล้ว ไม่มีค้างยอด")
else:
    selected_bill_label = st.selectbox("เลือกบิลเคลียร์ยอดที่โรงงานโอนเงินเข้ามา", list(unpaid_bills.keys()))
    
    if selected_bill_label:
        bill = unpaid_bills[selected_bill_label]
        net_amount = float(bill["total_amount"])
        vat_amount = float(bill["vat_amount"])
        grand_total = net_amount + vat_amount
        
        st.markdown("---")
        st.subheader("💰 รายละเอียดการรับเงิน")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**โรงงานปลายทาง:** {bill['weigh_out']['factories']['name']}")
            st.write(f"**วันที่เคลียร์บิลต้นทาง:** {bill['clearing_date']}")
            st.write(f"**มูลค่าสินค้าก่อน VAT:** {net_amount:,.2f} บาท")
            st.write(f"**ภาษีมูลค่าเพิ่ม VAT (7%):** {vat_amount:,.2f} บาท")
        with col2:
            st.metric("ยอดรวมสุทธิที่ต้องได้รับ (Grand Total)", f"{grand_total:,.2f} บาท")
            
        with st.form("real_receipt_form"):
            received_amount = st.number_input("จำนวนเงินที่โอนเข้าจริง (บาท)", min_value=0.0, value=grand_total, step=100.0)
            bank_ref = st.text_input("เลขที่อ้างอิงธนาคาร / รหัสสลิปโอนเงิน")
            receipt_date = st.date_input("วันที่เงินเข้าบัญชี", date.today())
            
            submitted = st.form_submit_button("✅ ยืนยันเงินเข้าบัญชีและปิดบิลลูกหนี้")
            if submitted:
                try:
                    receipt_data = {
                        "sales_clearing_id": bill["id"],
                        "received_amount": received_amount,
                        "bank_ref": bank_ref if bank_ref else None,
                        "receipt_date": str(receipt_date),
                        "status": "RECEIVED",
                        "created_by": st.session_state.user_id
                    }
                    
                    supabase.table("receipts").insert(receipt_data).execute()
                    st.success(f"🎉 บันทึกรับเงินโอนจำนวน {received_amount:,.2f} บาท สำหรับบิล SC-{bill['id']} เรียบร้อย!")
                    st.rerun()
                except Exception as e:
                    st.error(f"ไม่สามารถบันทึกรับเงินโอนได้: {e}")