import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client, Client

st.set_page_config(layout="wide")

st.header("📊 รายงานสรุปมูลค่าเงินสดและค่าขนส่ง (Financial Detailed Statement)")
st.info("💡 สามารถเลือกช่วงเวลาที่ต้องการตรวจสอบระบบบัญชีได้ จากนั้นระบบจะแยกรายละเอียดเงินรายวันและรายบิลออกเป็นแท็บอย่างชัดเจน")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# ---- 1. ส่วนควบคุมคัดเลือกระยะเวลาวันที่ (Date Range Filter) ----
col_f1, col_f2 = st.columns(2)
with col_f1:
    start_date = st.date_input("📆 ตั้งแต่วันที่ (Start Date)", date(date.today().year, date.today().month, 1))
with col_f2:
    end_date = st.date_input("📆 ถึงวันที่ (End Date)", date.today())

st.markdown("---")

# ฟังก์ชันช่วยแปลงฟอร์แมตวันที่จากฐานข้อมูลให้อ่านง่าย
def format_date(d_val):
    if not d_val: return "-"
    return str(d_val).split("T")[0]

# ตัวแปรสำหรับคำนวณสะสมยอดรวมใหญ่และสรุปรายวัน
grand_total_buy = 0.0
grand_total_sell = 0.0
grand_total_freight = 0.0
daily_pivot = {}

# =====================================================
# 📥 ดึงข้อมูลประวัติการรับซื้อเข้าลานจริง (ตาราง purchases)
# =====================================================
buy_details_rows = []
try:
    buy_res = supabase.table("purchases")\
        .select("id, net_weight, price_per_kg, date, product_types(name)")\
        .gte("date", str(start_date))\
        .lte("date", str(end_date))\
        .execute()
        
    for b in buy_res.data:
        b_date = format_date(b.get("date"))
        net_kg = int(b.get("net_weight", 0) or 0)
        p_kg = float(b.get("price_per_kg", 0) or 0)
        amount_baht = net_kg * p_kg # สูตรเงินสดฝั่งซื้อ
        
        grand_total_buy += amount_baht
        if b_date not in daily_pivot:
            daily_pivot[b_date] = {"buy": 0.0, "sell": 0.0, "freight": 0.0}
        daily_pivot[b_date]["buy"] += amount_baht
        
        p_name = b["product_types"]["name"] if b.get("product_types") else "ไม่ระบุเกรด"
        buy_details_rows.append({
            "วันที่ซื้อ": b_date,
            "เลขที่บิลซื้อ": f"P-{b['id']}",
            "เกรดสินค้า": p_name,
            "น้ำหนัก (kg)": net_kg,
            "ราคา (บาท/kg)": p_kg,
            "มูลค่าเงินจ่าย (บาท)": amount_baht
        })
except Exception:
    # กรณีโครงสร้างตารางหลักของพี่ใช้ชื่อ weigh_in_tickets สำรองระบบไว้ไม่ให้พัง
    try:
        buy_res = supabase.table("weigh_in_tickets").select("id, net_weight, price_per_kg, date").gte("date", str(start_date)).lte("date", str(end_date)).execute()
        for b in buy_res.data:
            b_date = format_date(b.get("date"))
            net_kg = int(b.get("net_weight", 0) or 0)
            p_kg = float(b.get("price_per_kg", 0) or 0)
            amount_baht = net_kg * p_kg
            grand_total_buy += amount_baht
            if b_date not in daily_pivot:
                daily_pivot[b_date] = {"buy": 0.0, "sell": 0.0, "freight": 0.0}
            daily_pivot[b_date]["buy"] += amount_baht
            buy_details_rows.append({
                "วันที่ซื้อ": b_date,
                "เลขที่บิลซื้อ": f"WI-{b['id']}",
                "เกรดสินค้า": "เหล็กหน้าร้าน",
                "น้ำหนัก (kg)": net_kg,
                "ราคา (บาท/kg)": p_kg,
                "มูลค่าเงินจ่าย (บาท)": amount_baht
            })
    except Exception:
        pass

# =====================================================
# 📤 ดึงข้อมูลประวัติการขายออก & 🚛 ค่าขนส่งสิบล้อ (ตาราง weigh_out)
# =====================================================
sell_details_rows = []
try:
    wo_res = supabase.table("weigh_out")\
        .select("id, net_weight, date, load_orders(freight_rate, freight_mode, product_type_id), factories(name)")\
        .gte("date", str(start_date))\
        .lte("date", str(end_date))\
        .execute()
        
    prod_res = supabase.table("product_types").select("id, name").execute()
    prod_map = {p["id"]: p["name"] for p in prod_res.data}
    
    for wo in wo_res.data:
        w_date = format_date(wo.get("date"))
        net_kg = int(wo.get("net_weight", 0) or 0)
        lo = wo.get("load_orders", {}) or {}
        
        # 🟢 1. คำนวณมูลค่าเงินขายโรงงาน (Auto-Unit ดักจับราคาต่อตัน)
        sell_rate = float(lo.get("freight_rate", 0) or 0)
        if sell_rate >= 1000:
            sell_value = (net_kg / 1000) * sell_rate # คิดแบบราคาต่อตัน
            rate_text = f"{sell_rate:,} / ตัน"
        else:
            sell_value = net_kg * sell_rate # คิดแบบราคาต่อโล
            rate_text = f"{sell_rate:,} / kg"
            
        grand_total_sell += sell_value
        if w_date not in daily_pivot:
            daily_pivot[w_date] = {"buy": 0.0, "sell": 0.0, "freight": 0.0}
        daily_pivot[w_date]["sell"] += sell_value
        
        # 🚛 2. คำนวณเงินค่าขนส่งรถสิบล้อร่วมเดินทาง
        f_mode = lo.get("freight_mode", "PER_TON")
        if f_mode == "FLAT_RATE":
            freight_value = sell_rate # เหมาเที่ยว
        else:
            freight_value = (net_kg / 1000) * sell_rate # คิดตามน้ำหนักบรรทุกจริง (ตัน)
            
        grand_total_freight += freight_value
        daily_pivot[w_date]["freight"] += freight_value
        
        p_id = lo.get("product_type_id")
        prod_name = prod_map.get(p_id, "ไม่ระบุประเภท")
        fac_name = wo["factories"]["name"] if wo.get("factories") else "ไม่ระบุโรงงาน"
        
        sell_details_rows.append({
            "วันที่ขาย": w_date,
            "รหัสคิวตั๋ว": f"LO-{wo['id']}",
            "โรงงานผู้รับซื้อ": fac_name,
            "ประเภทเหล็ก": prod_name,
            "น้ำหนักสุทธิ (kg)": net_kg,
            "ราคาข้อตกลง": rate_text,
            "💵 ยอดรับค่าเหล็ก (บาท)": sell_value,
            "🚛 ยอดค่าขนส่งรถ (บาท)": freight_value
        })
except Exception as e:
    st.error(f"ระบบขัดข้องในการคำนวณฝั่งขาย: {e}")

# =====================================================
# 📊 แผงควบคุมสรุปตัวเลขใหญ่สะสม (Dashboard Summary)
# =====================================================
st.subheader("💰 สรุปกระแสเงินสดก้อนกว้างประจำช่วงเวลา")
col_m1, col_m2, col_m3 = st.columns(3)
with col_m1:
    st.metric(label="🔴 รวมยอดเงินจ่ายซื้อเหล็กเข้าลาน", value=f"{grand_total_buy:,.2f} บาท")
with col_m2:
    st.metric(label="🟢 รวมยอดเงินรอรับจากโรงงานใหญ่", value=f"{grand_total_sell:,.2f} บาท")
with col_m3:
    st.metric(label="🚛 รวมงบตั้งจ่ายค่าขนส่งสิบล้อ", value=f"{grand_total_freight:,.2f} บาท")

st.markdown("---")

# =====================================================
# 🗂️ แยกกระดานการจัดแสดงผลออกเป็น 3 แท็บตามสั่งการ
# =====================================================
tab1, tab2, tab3 = st.tabs(["📥 แท็บ 1: รายละเอียดบิลซื้อเข้าลาน", "📤 แท็บ 2: รายละเอียดขายออก & ค่าสิบล้อ", "📅 แท็บ 3: สรุปงบรวมรายวัน"])

# ---- แท็บที่ 1: รายละเอียดบิลฝั่งซื้อเข้าลาน ----
with tab1:
    st.subheader("📥 ตารางแจกแจงประวัติการจ่ายเงินซื้อเหล็กหน้าร้าน (รายบิล)")
    if not buy_details_rows:
        st.warning("⚠️ ไม่พบตั๋วข้อมูลการรับซื้อของเข้าลานในช่วงวันที่เลือก")
    else:
        df_details_buy = pd.DataFrame(buy_details_rows)
        # จัดฟอร์แมตตัวเลขให้อ่านง่าย
        df_details_buy["น้ำหนัก (kg)"] = df_details_buy["น้ำหนัก (kg)"].map('{:,}'.format)
        df_details_buy["ราคา (บาท/kg)"] = df_details_buy["ราคา (บาท/kg)"].map('{:,.2f}'.format)
        df_details_buy["มูลค่าเงินจ่าย (บาท)"] = df_details_buy["มูลค่าเงินจ่าย (บาท)"].map('{:,.2f}'.format)
        st.dataframe(df_details_buy, use_container_width=True, hide_index=True)

# ---- แท็บที่ 2: รายรายละเอียดฝั่งขายออกโรงงานคู่ขนานสิบล้อ ----
with tab2:
    st.subheader("📤 ตารางแจกแจงใบตั๋วชั่งออกส่งขายโรงงานใหญ่ และ ค่าขนส่งสิบล้อ (รายคันรถ)")
    if not sell_details_rows:
        st.warning("⚠️ ไม่พบประวัติตั๋วรถวิ่งสินค้าออกลานในช่วงวันที่เลือก")
    else:
        df_details_sell = pd.DataFrame(sell_details_rows)
        df_details_sell["น้ำหนักสุทธิ (kg)"] = df_details_sell["น้ำหนักสุทธิ (kg)"].map('{:,}'.format)
        df_details_sell["💵 ยอดรับค่าเหล็ก (บาท)"] = df_details_sell["💵 ยอดรับค่าเหล็ก (บาท)"].map('{:,.2f}'.format)
        df_details_sell["🚛 ยอดค่าขนส่งรถ (บาท)"] = df_details_sell["🚛 ยอดค่าขนส่งรถ (บาท)"].map('{:,.2f}'.format)
        st.dataframe(df_details_sell, use_container_width=True, hide_index=True)

# ---- แท็บที่ 3: ตารางงบกระแสรวมรายวันบรรทัดเดียว ----
with tab3:
    st.subheader("📅 งบสรุปภาพรวมรายได้-รายจ่าย และผลต่างกำไรประจำวัน")
    if not daily_pivot:
        st.warning("⚠️ ไม่มีข้อมูลการทำธุรกรรมหมุนเวียนเงินในช่วงวันที่เลือก")
    else:
        pivot_rows = []
        for day in sorted(daily_pivot.keys(), reverse=True):
            b_day = daily_pivot[day]["buy"]
            s_day = daily_pivot[day]["sell"]
            f_day = daily_pivot[day]["freight"]
            profit_day = s_day - b_day - f_day # ผลต่างกำไรรายวันสุทธิ
            
            pivot_rows.append({
                "วันที่สรุปยอด": day,
                "🔴 ยอดซื้อเข้าลาน (บาท)": b_day,
                "📤 ยอดขายส่งโรงงาน (บาท)": s_day,
                "🚛 งบค่าน้ำมันสิบล้อ (บาท)": f_day,
                "📊 ผลกำไรลานสุทธิ (บาท)": profit_day
            })
            
        df_pivot = pd.DataFrame(pivot_rows)
        # เติมคอมม่าตัวเลขการเงินทุกช่องเพื่อความชัดเจน
        for col in df_pivot.columns:
            if col != "วันที่สรุปยอด":
                df_pivot[col] = df_pivot[col].map('{:,.2f}'.format)
        st.dataframe(df_pivot, use_container_width=True, hide_index=True)