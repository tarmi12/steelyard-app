import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client, Client

st.set_page_config(layout="wide")

st.header("📊 รายงานมูลค่าธุรกิจฝั่งขายออกโรงงาน (Sales Financial Report)")
st.info("💰 สรุปภาพรวมเม็ดเงินสด บาทต่อบาท จากใบงานที่ชั่งออกส่งขายโรงงานใหญ่ เพื่อตรวจสอบยอดรายรับของลานเหล็ก")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# ---- 1. ส่วนกรอกตัวเลือกกรองข้อมูลด้วยวันที่ ----
col_f1, col_f2 = st.columns(2)
with col_f1:
    start_date = st.date_input("📆 ตั้งแต่วันที่", date(date.today().year, date.today().month, 1))
with col_f2:
    end_date = st.date_input("📆 ถึงวันที่", date.today())

st.markdown("---")

try:
    # 📥 ----------------------------------------------------
    # ดึงและคำนวณฝั่งขายออก (Weigh Out / Sell Value) อิงตามตารางที่มีจริงหลังบ้าน
    # ----------------------------------------------------
    wo_res = supabase.table("weigh_out")\
        .select("id, net_weight, vat_mode, date, load_orders(product_type_id, freight_rate, price_unit), factories(name)")\
        .gte("date", str(start_date))\
        .lte("date", str(end_date))\
        .execute()
        
    # ดึง Master ประเภทเหล็กมาแมตช์ชื่อฝั่งขาย
    prod_res = supabase.table("product_types").select("id, name").execute()
    prod_map = {p["id"]: p["name"] for p in prod_res.data}
    
    total_sell_kg = 0
    total_sell_baht = 0.0
    sell_rows = []
    
    for wo in wo_res.data:
        net_kg = int(wo.get("net_weight", 0) or 0)
        lo_data = wo.get("load_orders", {}) or {}
        
        # ค้นหาราคาขายที่ตกลงกันไว้ในใบสั่งโหลด
        price_unit = lo_data.get("price_unit", "PER_TON")
        price_rate = float(lo_data.get("freight_rate", 0) or 0)
        
        # 🌟 สูตรแปลงหน่วยอัจฉริยะ: กิโลกรัม -> ตัน -> คูณเงินบาท
        if price_unit == "PER_TON":
            amount_baht = (net_kg / 1000) * price_rate
        else:
            amount_baht = net_kg * price_rate
            
        total_sell_kg += net_kg
        total_sell_baht += amount_baht
        
        p_id = lo_data.get("product_type_id")
        prod_name = prod_map.get(p_id, "ไม่ระบุ")
        fac_name = wo["factories"]["name"] if wo.get("factories") else "ไม่ระบุ"
        
        sell_rows.append({
            "รหัสตั๋วชั่ง (ID)": wo.get("id"),
            "วันที่ชั่งออก": wo.get("date"),
            "ส่งโรงงานปลายทาง": fac_name,
            "ประเภทเนื้อเหล็ก": prod_name,
            "น้ำหนักสุทธิหน้าลาน (kg)": f"{net_kg:,}",
            "ข้อตกลงราคาขาย": f"{price_rate:,} บาท / {price_unit}",
            "มูลค่าซื้อขายสุทธิ (บาท)": amount_baht
        })

except Exception as e:
    st.error(f"เกิดข้อผิดพลาดในการดึงรายงานการเงิน: {e}")
    sell_rows = []
    total_sell_kg = 0
    total_sell_baht = 0.0

# ---- 2. แผงควบคุมแสดงตัวเลขสรุป (Dashboard Metrics) ----
st.subheader("💵 สรุปยอดเงินรายรับสะสมประจำช่วงเวลา")
col_m1, col_m2 = st.columns(2)

with col_m1:
    st.metric(
        label="📦 ยอดน้ำหนักเหล็กส่งออกรวมทั้งหมด (กิโลกรัม)", 
        value=f"{total_sell_kg:,} kg",
        delta="ปริมาณเนื้อเหล็กที่ตัดสต็อก"
    )
with col_m2:
    st.metric(
        label="💰 ยอดมูลค่าเงินรวมที่ต้องจัดเก็บโรงงานใหญ่ (บาท)", 
        value=f"{total_sell_baht:,.2f} บาท",
        delta="คำนวณอิงตามราคาต่อตัน/ต่อกิโลกรัมจริง"
    )

st.markdown("---")

# ---- 3. ส่วนกางตารางแจกแจงรายบิลให้บัญชีตรวจสอบ ----
st.caption("🏭 ตารางตรวจสอบรายละเอียดตั๋วรถชั่งออกและมูลค่าเงินบาทรายเที่ยววิ่ง")
if not sell_rows:
    st.warning("⚠️ ไม่พบข้อมูลประวัติตั๋วชั่งออกในช่วงวันที่เลือกข้างต้นครับ")
else:
    df_sell = pd.DataFrame(sell_rows)
    # ปรับฟอร์แมตจัดแสดงตัวเลขเงินบาทให้สวยงามอ่านง่าย
    df_sell["มูลค่าซื้อขายสุทธิ (บาท)"] = df_sell["มูลค่าซื้อขายสุทธิ (บาท)"].map('{:,.2f}'.format)
    st.dataframe(df_sell, use_container_width=True, hide_index=True)