import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client, Client

st.set_page_config(layout="wide")

st.header("📊 รายงานมูลค่าธุรกิจและกำไรขั้นต้น (Financial & Value Report)")
st.info("💰 สรุปภาพรวมเม็ดเงินสด บาทต่อบาท ทั้งฝั่งจ่ายเงินซื้อเข้า และฝั่งรับเงินขายออกโรงงานใหญ่ เพื่อการบริหารจัดการลาน")

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
    # ----------------------------------------------------
    # 📥 ดึงและคำนวณฝั่งซื้อเข้า (Weigh In / Buy Value)
    # ----------------------------------------------------
    wi_res = supabase.table("weigh_in")\
        .select("id, net_weight, price_per_kg, date, product_types(name)")\
        .gte("date", str(start_date))\
        .lte("date", str(end_date))\
        .execute()
        
    total_buy_kg = 0
    total_buy_baht = 0.0
    buy_rows = []
    
    for wi in wi_res.data:
        net_kg = int(wi.get("net_weight", 0) or 0)
        price_kg = float(wi.get("price_per_kg", 0) or 0)
        # สูตรฝั่งซื้อ: กิโลกรัม x ราคาบาทต่อกิโลกรัม
        amount_baht = net_kg * price_kg
        
        total_buy_kg += net_kg
        total_buy_baht += amount_baht
        
        prod_name = wi["product_types"]["name"] if wi.get("product_types") else "ไม่ระบุ"
        buy_rows.append({
            "วันที่": wi.get("date"),
            "ประเภทเหล็ก": prod_name,
            "น้ำหนักสุทธิ (kg)": f"{net_kg:,}",
            "ราคาซื้อ (บาท/kg)": f"{price_kg:,.2f}",
            "มูลค่าซื้อรวม (บาท)": amount_baht
        })

    # ----------------------------------------------------
    # 📤 ดึงและคำนวณฝั่งขายออก (Weigh Out / Sell Value)
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
        
        # ค้นหาราคาขายที่ตกลงกันไว้ในใบสั่งโหลด (อิงตามโครงสร้างของลาน)
        price_unit = lo_data.get("price_unit", "PER_TON")
        price_rate = float(lo_data.get("freight_rate", 0) or 0) # ดึงพิกัดราคาตั้งขาย
        
        # 🌟 สูตรแปลงหน่วยอัจฉริยะตามที่เช็คในสคริปต์หลังบ้าน
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
            "วันที่": wo.get("date"),
            "ส่งโรงงาน": fac_name,
            "ประเภทเหล็ก": prod_name,
            "น้ำหนักสุทธิ (kg)": f"{net_kg:,}",
            "พิกัดราคาขาย": f"{price_rate:,} / {price_unit}",
            "มูลค่าขายรวม (บาท)": amount_baht
        })

except Exception as e:
    st.error(f"เกิดข้อผิดพลาดในการดึงรายงานการเงิน: {e}")
    buy_rows, sell_rows = [], []
    total_buy_kg, total_sell_kg = 0, 0
    total_buy_baht, total_sell_baht = 0.0, 0.0

# ---- 2. แผงควบคุมแสดงตัวเลขสรุป (Dashboard Metrics) ----
st.subheader("💵 สรุปดัชนีเม็ดเงินสดประจำช่วงเวลา")
col_m1, col_m2, col_m3 = st.columns(3)

with col_m1:
    st.metric(
        label="🔴 มูลค่าการจ่ายเงินซื้อเข้าลาน (บาท)", 
        value=f"{total_buy_baht:,.2f} บาท",
        delta=f"{total_buy_kg:,} kg", delta_color="inverse"
    )
with col_m2:
    st.metric(
        label="🟢 มูลค่าใบงานส่งขายโรงงานใหญ่ (บาท)", 
        value=f"{total_sell_baht:,.2f} บาท",
        delta=f"{total_sell_kg:,} kg"
    )
with col_m3:
    gross_profit = total_sell_baht - total_buy_baht
    # ดีดตัวเลขอัตรากำไรขั้นต้น
    st.metric(
        label="📊 ผลต่างมูลค่ากำไรขั้นต้นเบื้องต้น (บาท)", 
        value=f"{gross_profit:,.2f} บาท",
        delta="คำนวณจาก (ยอดขาย - ยอดซื้อ)"
    )

st.markdown("---")

# ---- 3. ส่วนกางตารางแจกแจงรายบิลให้บัญชีตรวจสอบ ----
tab_buy, tab_sell = st.tabs(["📥 รายละเอียดเงินฝั่งซื้อเข้าลาน", "📤 รายละเอียดเงินฝั่งขายออกโรงงาน"])

with tab_buy:
    st.caption("📝 ตารางแสดงรายการรับซื้อเนื้อเหล็กหน้าลานและเม็ดเงินที่จ่ายออกจริงต่อเที่ยว")
    if not buy_rows:
        st.warning("⚠️ ไม่มีข้อมูลการซื้อเข้าในช่วงวันที่เลือก")
    else:
        df_buy = pd.DataFrame(buy_rows)
        # ปรับการจัดรูปแบบแสดงตัวเลขเงินบาทในตาราง
        df_buy["มูลค่าซื้อรวม (บาท)"] = df_buy["มูลค่าซื้อรวม (บาท)"].map('{:,.2f}'.format)
        st.dataframe(df_buy, use_container_width=True, hide_index=True)

with tab_sell:
    st.caption("🏭 ตารางแสดงตั๋วรถชั่งออกส่งขายโรงงานใหญ่ และแปลงยอดพิกัดราคาคิดเงินบาท")
    if not sell_rows:
        st.warning("⚠️ ไม่มีข้อมูลการขายออกในช่วงวันที่เลือก")
    else:
        df_sell = pd.DataFrame(sell_rows)
        df_sell["มูลค่าขายรวม (บาท)"] = df_sell["มูลค่าขายรวม (บาท)"].map('{:,.2f}'.format)
        st.dataframe(df_sell, use_container_width=True, hide_index=True)