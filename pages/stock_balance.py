import streamlit as st
import pandas as pd
from supabase import create_client, Client

st.header("📦 ยอดสินค้าสต็อกคงเหลือจริง ณ ลานเหล็กไทย (คำนวณแบบ Real-time)")
st.info("📊 ข้อมูลด้านล่างนี้คำนวณโดยตรงจากประวัติการซื้อ ซื้อเข้าสิ้นวัน ชั่งออก และการปรับยอดสต็อกมือในฐานข้อมูล")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

try:
    # 1. ดึงข้อมูลประวัติธุรกรรมสต็อกทั้งหมดเพื่อคำนวณยอดคงเหลือหลัก
    tx_res = supabase.table("inventory_transactions").select("stock_type, quantity").execute()
    transactions = tx_res.data
    
    # 2. ดึงข้อมูลประเภทสินค้าจริงทั้งหมดจากฐานข้อมูลมาทำตัวแปรอ้างอิง (Master Mapping)
    prod_types_res = supabase.table("product_types").select("id, name").execute()
    product_dict = {p["id"]: p["name"] for p in prod_types_res.data}
    
    # 3. ดึงข้อมูลรายการซื้อ (purchase_lines) เพื่อเอาไปเชื่อมหาประเภทเหล็กเวลาเป็นงาน PURCHASE
    p_lines_res = supabase.table("purchase_lines").select("id, product_type_id").execute()
    p_lines_map = {p["id"]: product_dict.get(p["product_type_id"], "ไม่ระบุเกรด") for p in p_lines_res.data}
    
    # 4. ดึงข้อมูลใบสั่งโหลด (load_orders) เพื่อเอาไปเชื่อมหาประเภทเหล็กเวลาเป็นงาน SALE (ชั่งออก/เคลียร์บิล)
    # เชื่อมผ่าน weigh_out_id -> load_orders หรือตรงจาก load_orders
    lo_res = supabase.table("load_orders").select("id, product_type_id").execute()
    lo_map = {l["id"]: product_dict.get(l["product_type_id"], "ไม่ระบุเกรด") for l in lo_res.data}
    
    # ดึงข้อมูล weigh_out เพื่อหาจุดเชื่อมระหว่าง SC/WO ไปยังคิวรถหลัก
    wo_res = supabase.table("weigh_out").select("id, load_order_id").execute()
    wo_to_lo_map = {w["id"]: w["load_order_id"] for w in wo_res.data}
    
except Exception as e:
    st.error(f"ไม่สามารถคำนวณยอดสต็อกคงเหลือได้เนื่องจาก: {e}")
    transactions = []
    p_lines_map = {}
    lo_map = {}
    wo_to_lo_map = {}

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

# ---- 2. ดึงล็อกประวัติธุรกรรมเพื่อกระจายลงแท็บพร้อมระบุประเภทเหล็ก ----
st.subheader("📜 รายงานประวัติความเคลื่อนไหวสต็อกล่าสุด (แยกฝั่งตรวจสอบ)")

try:
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

# ฟังก์ชันอัจฉริยะช่วยแกะหาชื่อประเภทเหล็กตามประเภทเอกสารอ้างอิง
def ดึงชื่อประเภทเหล็ก(ref_type, ref_id):
    if not ref_id:
        return "ปรับยอดสต็อกมือ"
        
    if ref_type == "PURCHASE_LINE":
        # ดึงจากตาราง purchase_lines
        return p_lines_map.get(ref_id, "ไม่พบเกรดเหล็ก")
        
    elif ref_type == "WEIGH_OUT":
        # ตาราง weigh_out ผูกกับ load_orders เพื่อดูสินค้า
        lo_id = wo_to_lo_map.get(ref_id)
        return lo_map.get(lo_id, "ไม่พบเกรดเหล็ก") if lo_id else "ไม่พบเกรดเหล็ก"
        
    elif ref_type == "SALES_CLEARING":
        # ตาราง sales_clearing ผูกกับ weigh_out -> load_orders เพื่อดูสินค้า
        # ต้องไปดึงข้อมูลบิล sales_clearing เพื่อหา weigh_out_id ก่อน
        try:
            sc_res = supabase.table("sales_clearing").select("weigh_out_id").eq("id", ref_id).execute()
            if sc_res.data:
                wo_id = sc_res.data[0]["weigh_out_id"]
                lo_id = wo_to_lo_map.get(wo_id)
                return lo_map.get(lo_id, "ไม่พบเกรดเหล็ก") if lo_id else "ไม่พบเกรดเหล็ก"
        except Exception:
            pass
        return "เหล็กขาออก"
        
    return "ปรับปรุงระบบ"

# สร้างแท็บให้เสมียนกดเลือกดูอย่างชัดเจน
tab_p, tab_r = st.tabs(["🔴 ประวัติสต็อกกองจริงหน้าลาน (Physical)", "🔵 ประวัติสต็อกบัญชี/ภาษี (Reporting)"])

with tab_p:
    if not phys_logs:
        st.info("ยังไม่มีประวัติความเคลื่อนไหวในระบบสต็อก Physical")
    else:
        df_p = pd.DataFrame([{
            "เลขธุรกรรม": l["id"],
            "ประเภทงาน": "📥 ซื้อเหล็กเข้า" if l["transaction_type"] == "PURCHASE" else ("📤 ชั่งออกขาย" if l["transaction_type"] == "SALE" else "🔧 ปรับยอดมือ"),
            "ประเภทเหล็ก": ดึงชื่อประเภทเหล็ก(l["reference_type"], l["reference_id"]), # คอลัมน์ที่เพิ่มใหม่
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
            "ประเภทเหล็ก": ดึงชื่อประเภทเหล็ก(l["reference_type"], l["reference_id"]), # คอลัมน์ที่เพิ่มใหม่
            "น้ำหนัก บัญชี (kg)": f"{l['quantity']:,}",
            "วันที่ทำรายการ": l["transaction_date"],
            "ประเภทเอกสาร": l["reference_type"],
            "เลขที่เอกสารอ้างอิง": f"ID-{l['reference_id']}" if l['reference_id'] else "-"
        } for l in rep_logs])
        st.dataframe(df_r, use_container_width=True, hide_index=True)