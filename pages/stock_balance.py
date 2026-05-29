import streamlit as st
import pandas as pd
from supabase import create_client, Client

st.header("📦 ยอดสินค้าสต็อกคงเหลือจริง ณ ลานเหล็กไทย (คำนวณแบบ Real-time)")
st.info("📊 ข้อมูลด้านล่างนี้คำนวณโดยตรงจากประวัติการซื้อ ซื้อเข้าสิ้นวัน ชั่งออก และการปรับยอดสต็อกมือในฐานข้อมูล")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

try:
    # แก้ไขจุดที่มีปัญหา: ดึงเฉพาะข้อมูลพื้นฐานจาก inventory_transactions โดยไม่ Join ข้ามไป product_types
    tx_res = supabase.table("inventory_transactions").select("stock_type, quantity").execute()
    transactions = tx_res.data
    
except Exception as e:
    st.error(f"ไม่สามารถคำนวณยอดสต็อกคงเหลือได้เนื่องจาก: {e}")
    transactions = []

# ---- 1. คำนวณหาตัวเลขรวมหน้าบอร์ดสถิติ ----
total_physical = sum(t["quantity"] for t in transactions if t["stock_type"] == "PHYSICAL")
total_reporting = sum(t["quantity"] for t in transactions if t["stock_type"] == "REPORTING")

col1, col2 = st.columns(2)
with col1:
    st.markdown("<div style='background-color:#ffe6e6; padding:20px; border-radius:10px; border-left:8px solid #cc0000;'>", unsafe_allow_html=True)
    st.metric("🔴 ยอดสต็อกสินค้าจริงหน้าลาน (Physical Stock)", f"{total_physical:,} กิโลกรัม")
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown("<div style='background-color:#e6f0ff; padding:20px; border-radius:10px; border-left:8px solid #0044cc;'>", unsafe_allow_html=True)
    st.metric("🔵 ยอดสต็อกทางบัญชี/ภาษี (Reporting Stock)", f"{total_reporting:,} กิโลกรัม")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")

# ---- 2. แสดงตารางประวัติธุรกรรมเพื่อความโปร่งใส ตรวจสอบย้อนกลับได้ ----
st.subheader("📜 รายงานประวัติความเคลื่อนไหวสต็อก 50 รายการล่าสุด")
try:
    log_query = supabase.table("inventory_transactions")\
        .select("id, stock_type, transaction_type, quantity, transaction_date, reference_type")\
        .order("id", desc=True).limit(50).execute()
        
    if not log_query.data:
        st.info("ยังไม่มีประวัติการซื้อหรือขายในตารางธุรกรรมสต็อก")
    else:
        log_df = pd.DataFrame([{
            "เลขธุรกรรม": l["id"],
            "ระบบสต็อก": "🔴 Physical" if l["stock_type"] == "PHYSICAL" else "🔵 Reporting",
            "ประเภทงาน": l["transaction_type"],
            "จำนวนน้ำหนัก (kg)": f"{l['quantity']:,}",
            "วันที่ทำรายการ": l["transaction_date"],
            "เอกสารอ้างอิง": l["reference_type"]
        } for l in log_query.data])
        st.dataframe(log_df, use_container_width=True, hide_index=True)
except Exception as e:
    st.write(f"ไม่สามารถแสดงตารางล็อกประวัติได้เนื่องจาก: {e}")