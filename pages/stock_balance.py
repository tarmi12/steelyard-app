import streamlit as st
import pandas as pd
from supabase import create_client, Client

st.header("📦 ยอดสินค้าสต็อกคงเหลือจริง ณ ลานเหล็กไทย (คำนวณแบบ Real-time)")
st.info("📊 ข้อมูลด้านล่างนี้คำนวณโดยตรงจากประวัติการซื้อ ซื้อเข้าสิ้นวัน ชั่งออก และการปรับยอดสต็อกมือในฐานข้อมูล")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

try:
    # ดึงข้อมูลมาคำนวณยอดรวมยอดคงเหลือ
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

# ---- 2. ปรับปรุงจุดนี้: แยกกระดานประวัติเพื่อแก้ปัญหาข้อมูลซ้ำซ้อนสายตา ----
st.subheader("📜 รายงานประวัติความเคลื่อนไหวสต็อกล่าสุด (แยกฝั่งตรวจสอบ)")

try:
    # ดึงประวัติธุรกรรมสต็อกลึก 100 รายการล่าสุดมาเพื่อกระจายลงแท็บ
    log_query = supabase.table("inventory_transactions")\
        .select("id, stock_type, transaction_type, quantity, transaction_date, reference_type, reference_id")\
        .order("id", desc=True).limit(100).execute()
    
    raw_logs = log_query.data
except Exception as e:
    st.error(f"ไม่สามารถดึงล็อกประวัติได้: {e}")
    raw_logs = []

# แยกค่ายอดล็อกออกตามประเภทสต็อกคู่
phys_logs = [l for l in raw_logs if l["stock_type"] == "PHYSICAL"]
rep_logs = [l for l in raw_logs if l["stock_type"] == "REPORTING"]

# สร้างแท็บให้เสมียนกดเลือกดูอย่างชัดเจน
tab_p, tab_r = st.tabs(["🔴 ประวัติสต็อกกองจริงหน้าลาน (Physical)", "🔵 ประวัติสต็อกบัญชี/ภาษี (Reporting)"])

with tab_p:
    if not phys_logs:
        st.info("ยังไม่มีประวัติความเคลื่อนไหวในระบบสต็อก Physical")
    else:
        df_p = pd.DataFrame([{
            "เลขธุรกรรม": l["id"],
            "ประเภทงาน": "📥 ซื้อเหล็กเข้า" if l["transaction_type"] == "PURCHASE" else ("📤 ชั่งออกขาย" if l["transaction_type"] == "SALE" else "🔧 ปรับยอดมือ"),
            "น้ำหนัก ข้อมูล (kg)": f"{l['quantity']:,}",
            "วันที่ทำรายการ": l["transaction_date"],
            "ประเภทเอกสาร": l["reference_type"],
            "เลขที่เอกสารอ้างอิง": f"ID-{l['reference_id']}" if l['reference_id'] else "-"
        } for l in phys_logs])
        st.dataframe(df_p, use_container_width=True, hide_index=True)

with tab_r:
    if not rep_logs:
        st.info("ยังไม่มีประวัติความเคลื่อนไหวในระบบสต็อก Reporting")
    else:
        df_r = pd.DataFrame([{
            "เลขธุรกรรม": l["id"],
            "ประเภทงาน": "📥 ซื้อเหล็กเข้า" if l["transaction_type"] == "PURCHASE" else ("📤 เคลียร์บิลขายจบ" if l["transaction_type"] == "SALE" else "🔧 ปรับยอดมือ"),
            "น้ำหนัก บัญชี (kg)": f"{l['quantity']:,}",
            "วันที่ทำรายการ": l["transaction_date"],
            "ประเภทเอกสาร": l["reference_type"],
            "เลขที่เอกสารอ้างอิง": f"ID-{l['reference_id']}" if l['reference_id'] else "-"
        } for l in rep_logs])
        st.dataframe(df_r, use_container_width=True, hide_index=True)