import streamlit as st
import pandas as pd
from supabase import create_client, Client

st.header("📑 รายงานสถานะลูกหนี้การค้า (ยอดเงินที่โรงงานยังค้างจ่าย)")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

try:
    # 1. ดึงยอดเคลียร์บิลขายทั้งหมด
    clearing_res = supabase.table("sales_clearing").select("id, total_amount, vat_amount, clearing_date, weigh_out(factories(name))").execute()
    # 2. ดึงยอดที่รับเงินไปแล้ว
    receipts_res = supabase.table("receipts").select("sales_clearing_id, received_amount").eq("status", "RECEIVED").execute()
    paid_map = {r["sales_clearing_id"]: float(r["received_amount"]) for r in receipts_res.data}
except Exception as e:
    st.error(f"ไม่สามารถประมวลผลข้อมูลลูกหนี้ได้: {e}")
    clearing_res = None

if not clearing_res or not clearing_res.data:
    st.info("ไม่มีประวัติธุรกรรมลูกหนี้ในระบบ")
else:
    debtor_rows = []
    total_pending_debt = 0.0
    
    for c in clearing_res.data:
        grand_total = float(c["total_amount"]) + float(c["vat_amount"])
        received = paid_map.get(c["id"], 0.0)
        balance = grand_total - received
        
        if balance > 0: # ค้างจ่ายเงิน
            total_pending_debt += balance
            debtor_rows.append({
                "รหัสบิล": f"SC-{c['id']}",
                "โรงงาน": c["weigh_out"]["factories"]["name"],
                "วันที่ตั้งหนี้": c["clearing_date"],
                "ยอดตามบิลสุทธิ": f"{grand_total:,.2f}",
                "รับแล้วบางส่วน": f"{received:,.2f}",
                "ยอดคงค้างชำระ": f"{balance:,.2f}"
            })
            
    st.subheader("📊 สรุปยอดหนี้คงค้างรวม")
    st.markdown("<div style='background-color:#fff3cd; padding:20px; border-radius:10px; border-left:8px solid #ffc107;'>", unsafe_allow_html=True)
    st.metric("💸 ยอดเงินรวมที่โรงงานค้างชำระทั้งหมด", f"{total_pending_debt:,.2f} บาท", delta=f"ค้าง {len(debtor_rows)} บิล")
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("📋 รายละเอียดบิลที่ยังค้างเงิน")
    if not debtor_rows:
        st.success("🎉 ยอดเยี่ยม! ลูกหนี้การค้าชำระเงินครบหมดแล้ว 100%")
    else:
        st.dataframe(pd.DataFrame(debtor_rows), use_container_width=True, hide_index=True)