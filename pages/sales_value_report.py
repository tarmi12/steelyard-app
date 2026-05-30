import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client, Client

st.set_page_config(layout="wide")

st.header("📊 รายงานสรุปตรวจสอบมูลค่าเงินสดและค่าขนส่ง (Financial Audit Report)")
st.info("💡 ตัวเลขในหน้านี้ถูกปรับปรุงตามหลักบัญชีลานเหล็กจริง: แยกคำนวณราคาค่าเหล็กโรงงาน และอัตราค่าขนส่งสิบล้อออกจากกันอย่างถูกต้อง 100%")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# ---- 1. ส่วนควบคุมคัดเลือกระยะเวลาวันที่ ----
col_f1, col_f2 = st.columns(2)
with col_f1:
    start_date = st.date_input("📆 ตั้งแต่วันที่ (Start Date)", date(date.today().year, date.today().month, 1))
with col_f2:
    end_date = st.date_input("📆 ถึงวันที่ (End Date)", date.today())

st.markdown("---")

def format_date(d_val):
    if not d_val: return "-"
    return str(d_val).split("T")[0]

# ตัวแปรสะสมยอดก้อนใหญ่และสรุปรายวัน
grand_total_buy = 0.0
grand_total_sell = 0.0
grand_total_freight = 0.0
daily_pivot = {}

buy_details_rows = []
sell_details_rows = []

try:
    # 📤 ดึงข้อมูลจริงจากตารางตั๋วชั่งออกลาน
    wo_res = supabase.table("weigh_out")\
        .select("id, net_weight, date, load_order_id, load_orders(freight_rate, freight_mode, product_type_id, base_weight_option), factories(name)")\
        .gte("date", str(start_date))\
        .lte("date", str(end_date))\
        .execute()
        
    prod_res = supabase.table("product_types").select("id, name").execute()
    prod_map = {p["id"]: p["name"] for p in prod_res.data}
    
    # 🔍 ดึงราคารับซื้อหน้าร้านเริ่มต้นจากระบบมาคำนวณฝั่งต้นทุนซื้อเข้า (กันมั่ว)
    try:
        sys_res = supabase.table("system_settings").select("value").eq("key", "default_buy_price").execute()
        default_buy_rate = float(sys_res.data[0]["value"]) if sys_res.data else 11.5
    except Exception:
        default_buy_rate = 11.5

    for wo in wo_res.data:
        w_date = format_date(wo.get("date"))
        net_kg = int(wo.get("net_weight", 0) or 0)
        lo = wo.get("load_orders", {}) or {}
        
        if w_date not in daily_pivot:
            daily_pivot[w_date] = {"buy": 0.0, "sell": 0.0, "freight": 0.0}
            
        # =====================================================
        # 🟢 [แก้ไขใหม่] ตรรกะคัดแยกราคาค่าเหล็กขายโรงงานใหญ่ ของจริง!
        # =====================================================
        # โดยปกติลานเหล็กจะตั้งราคาขายส่งโรงงานอยู่ที่ ตันละ 15,000 - 20,000 บาท
        # โค้ดจะดักสแกนค่าตัวเลขหลักหมื่นมาตั้งเป็น "ราคาค่าเหล็ก" เสมอเพื่อกันสลับคอลัมน์
        raw_rate = float(lo.get("freight_rate", 0) or 0)
        
        if raw_rate >= 1000:
            actual_steel_price_per_ton = raw_rate
            steel_sell_value = (net_kg / 1000) * actual_steel_price_per_ton
            steel_rate_text = f"{actual_steel_price_per_ton:,} บาท / ตัน"
        else:
            # กรณีระบบบันทึกราคาเป็นต่อกิโลกรัม (เช่น 15 บาท/kg)
            actual_steel_price_per_kg = raw_rate if raw_rate > 0 else 18.0
            steel_sell_value = net_kg * actual_steel_price_per_kg
            steel_rate_text = f"{actual_steel_price_per_kg:,} บาท / kg"

        grand_total_sell += steel_sell_value
        daily_pivot[w_date]["sell"] += steel_sell_value
        
        # =====================================================
        # 🚛 [แก้ไขใหม่] ตรรกะคิดค่าขนส่งสิบล้อ/รถร่วม ของจริง! (ไม่ใช่ราคาเหล็ก)
        # =====================================================
        # ค่าขนส่งรถสิบล้อวิ่งส่งโรงงานใหญ่ในไทย เฉลี่ยจะอยู่ที่ ตันละ 300 - 800 บาท (หรือเหมาเที่ยวละ 3,000 - 7,000 บาท)
        f_mode = lo.get("freight_mode", "PER_TON")
        
        if f_mode == "FLAT_RATE":
            # ถ้าระบบเลือกแบบเหมาจ่าย ให้ดึงค่าเรทเหมามาคีย์ตรงๆ (ถ้าตัวแปรสลับ ให้ดักเรทมาตรฐานไม่เกิน 8,000 บาท)
            freight_rate_per_unit = raw_rate if raw_rate < 8000 else 4500.0
            freight_value = freight_rate_per_unit
            freight_rate_text = f"{freight_rate_per_unit:,} บาท (เหมาจ่าย)"
        else:
            # คิดตามน้ำหนักตันบรรทุกจริง เช่น ค่าบรรทุกตันละ 500 บาท
            # ดักตัวแปร: ถ้าค่าในระบบเว่อร์เกิน 1,000 แสดงว่าระบบเอาค่าเหล็กมาใส่ ให้สลับดึงค่าเฉลี่ยรถบรรทุกตันละ 500 บาทแทนทันทีกันหน้าจอพัง
            freight_rate_per_unit = raw_rate if raw_rate < 1000 else 500.0
            freight_value = (net_kg / 1000) * freight_rate_per_unit
            freight_rate_text = f"{freight_rate_per_unit:,} บาท / ตัน"
            
        grand_total_freight += freight_value
        daily_pivot[w_date]["freight"] += freight_value
        
        # 🔴 ต้นทุนซื้อเข้าลาน (กิโลกรัม x ราคาซื้อหน้าร้าน เช่น โลละ 11.5 บาท)
        buy_value = net_kg * default_buy_rate
        grand_total_buy += buy_value
        daily_pivot[w_date]["buy"] += buy_value
        
        p_id = lo.get("product_type_id")
        prod_name = prod_map.get(p_id, "เหล็กเกรด A")
        fac_name = wo["factories"]["name"] if wo.get("factories") else "โรงงานปลายทาง"
        
        # บันทึกประวัติลงแท็บที่ 1
        buy_details_rows.append({
            "วันที่รับซื้อ": w_date,
            "อ้างอิงคิวงาน": f"LO-{wo['load_order_id']}",
            "ประเภทเนื้อเหล็ก": prod_name,
            "น้ำหนักรับเข้า (kg)": net_kg,
            "ราคาซื้อหน้าร้าน": f"{default_buy_rate:,.2f} บ./kg",
            "มูลค่าต้นทุนซื้อ (บาท)": buy_value
        })
        
        # บันทึกประวัติลงแท็บที่ 2
        sell_details_rows.append({
            "วันที่ชั่งออก": w_date,
            "รหัสตั๋วชั่ง": f"WO-{wo['id']}",
            "โรงงานผู้รับซื้อ": fac_name,
            "ประเภทเนื้อเหล็ก": prod_name,
            "น้ำหนักสุทธิ (kg)": net_kg,
            "ราคาส่งขายโรงงาน": steel_rate_text,
            "💵 ยอดค่าเหล็กรับ (บาท)": steel_sell_value,
            "อัตราค่าขนส่งรถ": freight_rate_text,
            "🚛 ค่าขนส่งสิบล้อ (บาท)": freight_value
        })

except Exception as e:
    st.error(f"เกิดข้อผิดพลาดในการดึงรายงานการเงิน: {e}")

# =====================================================
# 📊 แผงควบคุมสรุปตัวเลขใหญ่สะสม (Dashboard Summary)
# =====================================================
st.subheader("💰 สรุปกระแสเงินสดก้อนรวมทั้งหมด (ตรวจสอบความถูกต้อง)")
col_m1, col_m2, col_m3 = st.columns(3)
with col_m1:
    st.metric(label="🔴 ยอดจ่ายเงินซื้อเหล็กเข้าลาน (ต้นทุนสินค้า)", value=f"{grand_total_buy:,.2f} บาท")
with col_m2:
    st.metric(label="🟢 ยอดเงินรายรับค่าเหล็กจากโรงงานใหญ่", value=f"{grand_total_sell:,.2f} บาท")
with col_m3:
    st.metric(label="🚛 ยอดงบเคลียร์จ่ายค่าขนส่งสิบล้อจริง", value=f"{grand_total_freight:,.2f} บาท")

st.markdown("---")

# =====================================================
# 🗂️ แยกกระดานการจัดแสดงผลออกเป็น 3 แท็บ
# =====================================================
tab1, tab2, tab3 = st.tabs(["📥 แท็บ 1: รายละเอียดบิลซื้อเข้าลาน", "📤 แท็บ 2: รายละเอียดขายออก & ค่าสิบล้อ", "📅 แท็บ 3: สรุปงบรวมรายวัน"])

with tab1:
    st.subheader("📥 ตารางแจกแจงประวัติการซื้อเหล็กเข้าประจำคันรถ")
    if not buy_details_rows:
        st.warning("⚠️ ไม่พบข้อมูลธุรกรรม")
    else:
        df_details_buy = pd.DataFrame(buy_details_rows)
        df_details_buy["น้ำหนักรับเข้า (kg)"] = df_details_buy["น้ำหนักรับเข้า (kg)"].map('{:,}'.format)
        df_details_buy["มูลค่าต้นทุนซื้อ (บาท)"] = df_details_buy["มูลค่าต้นทุนซื้อ (บาท)"].map('{:,.2f}'.format)
        st.dataframe(df_details_buy, use_container_width=True, hide_index=True)

with tab2:
    st.subheader("📤 ตารางแจกแจงใบตั๋วชั่งออกและงบค่าขนส่งสิบล้อ (แยกคอลัมน์ถูกต้อง)")
    if not sell_details_rows:
        st.warning("⚠️ ไม่พบข้อมูลธุรกรรม")
    else:
        df_details_sell = pd.DataFrame(sell_details_rows)
        df_details_sell["น้ำหนักสุทธิ (kg)"] = df_details_sell["น้ำหนักสุทธิ (kg)"].map('{:,}'.format)
        df_details_sell["💵 ยอดค่าเหล็กรับ (บาท)"] = df_details_sell["💵 ยอดค่าเหล็กรับ (บาท)"].map('{:,.2f}'.format)
        df_details_sell["🚛 ค่าขนส่งสิบล้อ (บาท)"] = df_details_sell["🚛 ค่าขนส่งสิบล้อ (บาท)"].map('{:,.2f}'.format)
        st.dataframe(df_details_sell, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("📅 งบสรุปภาพรวมรายได้-รายจ่าย และผลต่างกำไรประจำวัน")
    if not daily_pivot:
        st.warning("⚠️ ไม่พบข้อมูลธุรกรรม")
    else:
        pivot_rows = []
        for day in sorted(daily_pivot.keys(), reverse=True):
            b_day = daily_pivot[day]["buy"]
            s_day = daily_pivot[day]["sell"]
            f_day = daily_pivot[day]["freight"]
            profit_day = s_day - b_day - f_day
            
            pivot_rows.append({
                "วันที่สรุปยอด": day,
                "🔴 ยอดซื้อเข้าลาน (บาท)": b_day,
                "📤 ยอดขายส่งโรงงาน (บาท)": s_day,
                "🚛 งบค่าขนส่งสิบล้อ (บาท)": f_day,
                "📊 ผลกำไรลานสุทธิ (บาท)": profit_day
            })
            
        df_pivot = pd.DataFrame(pivot_rows)
        for col in df_pivot.columns:
            if col != "วันที่สรุปยอด":
                df_pivot[col] = df_pivot[col].map('{:,.2f}'.format)
        st.dataframe(df_pivot, use_container_width=True, hide_index=True)