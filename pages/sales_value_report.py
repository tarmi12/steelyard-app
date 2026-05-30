import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client, Client

st.set_page_config(layout="wide")

st.header("📊 รายงานสรุปมูลค่าเงินสดและค่าขนส่ง (Financial Detailed Statement)")
st.info("💡 เลือกช่วงเวลาที่ต้องการตรวจสอบระบบบัญชีด้านล่าง จากนั้นระบบจะแยกแจงรายละเอียดเงินรายคันและสรุปยอดรายวันออกเป็นแท็บอย่างชัดเจน")

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

def format_date(d_val):
    if not d_val: return "-"
    return str(d_val).split("T")[0]

# ตัวแปรสะสมยอดก้อนใหญ่และสรุปรายวัน
grand_total_buy = 0.0
grand_total_sell = 0.0
grand_total_freight = 0.0
daily_pivot = {}

# =====================================================
# 📤 ดึงข้อมูลฝั่งขายออก & ค่าขนส่งสิบล้อ & คำนวณฝั่งซื้อเชื่อมโยง (จากตาราง weigh_out ที่มีชัวร์)
# =====================================================
buy_details_rows = []
sell_details_rows = []

try:
    # ดึงตั๋วชั่งออกที่มีข้อมูลจริงในระบบของพี่
    wo_res = supabase.table("weigh_out")\
        .select("id, net_weight, date, load_order_id, load_orders(freight_rate, freight_mode, product_type_id), factories(name)")\
        .gte("date", str(start_date))\
        .lte("date", str(end_date))\
        .execute()
        
    # ดึง Master ประเภทเหล็กมาแสดงชื่อเกรดเหล็ก
    prod_res = supabase.table("product_types").select("id, name").execute()
    prod_map = {p["id"]: p["name"] for p in prod_res.data}
    
    # 🔍 พยายามดึงราคารับซื้อหน้าร้านย้อนหลังมาเฉลี่ยคำนวณฝั่งซื้อ (เพื่อป้องกันตารางพัง)
    try:
        sys_res = supabase.table("system_settings").select("value").eq("key", "default_buy_price").execute()
        default_buy_rate = float(sys_res.data[0]["value"]) if sys_res.data else 12.0
    except Exception:
        default_buy_rate = 12.0 # ค่าเผื่อเลือกกรณีไม่มีตารางตั้งค่า

    for wo in wo_res.data:
        w_date = format_date(wo.get("date"))
        net_kg = int(wo.get("net_weight", 0) or 0)
        lo = wo.get("load_orders", {}) or {}
        
        if w_date not in daily_pivot:
            daily_pivot[w_date] = {"buy": 0.0, "sell": 0.0, "freight": 0.0}
            
        # 🟢 คิดมูลค่าฝั่งขายส่งโรงงาน (Auto-Unit Detection ราคาต่อตัน/ต่อกิโล)
        sell_rate = float(lo.get("freight_rate", 0) or 0)
        if sell_rate >= 1000:
            sell_value = (net_kg / 1000) * sell_rate
            rate_text = f"{sell_rate:,} / ตัน"
        else:
            sell_value = net_kg * sell_rate
            rate_text = f"{sell_rate:,} / kg"
            
        grand_total_sell += sell_value
        daily_pivot[w_date]["sell"] += sell_value
        
        # 🚛 คิดมูลค่าค่าขนส่งสิบล้อ
        f_mode = lo.get("freight_mode", "PER_TON")
        if f_mode == "FLAT_RATE":
            freight_value = sell_rate
        else:
            freight_value = (net_kg / 1000) * sell_rate
            
        grand_total_freight += freight_value
        daily_pivot[w_date]["freight"] += freight_value
        
        # 🔴 คิดมูลค่าฝั่งซื้อเข้าลาน (อิงตามปริมาณเนื้อเหล็กที่หมุนเวียนจริงในบิลคันนั้น)
        buy_value = net_kg * default_buy_rate
        grand_total_buy += buy_value
        daily_pivot[w_date]["buy"] += buy_value
        
        p_id = lo.get("product_type_id")
        prod_name = prod_map.get(p_id, "เหล็กเกรดรวม")
        fac_name = wo["factories"]["name"] if wo.get("factories") else "โรงงานปลายทาง"
        
        # เพิ่มข้อมูลลงแท็บซื้อ
        buy_details_rows.append({
            "วันที่รับซื้อ": w_date,
            "อ้างอิงคิวงาน": f"LO-{wo['load_order_id']}",
            "ประเภทเนื้อเหล็ก": prod_name,
            "น้ำหนักรับเข้า (kg)": net_kg,
            "ราคาประมาณการ (บาท/kg)": default_buy_rate,
            "มูลค่าต้นทุนซื้อ (บาท)": buy_value
        })
        
        # เพิ่มข้อมูลลงแท็บขาย
        sell_details_rows.append({
            "วันที่ชั่งออก": w_date,
            "รหัสตั๋วชั่ง": f"WO-{wo['id']}",
            "โรงงานผู้รับซื้อ": fac_name,
            "ประเภทเนื้อเหล็ก": prod_name,
            "น้ำหนักสุทธิ (kg)": net_kg,
            "ข้อตกลงราคาขาย": rate_text,
            "💵 ยอดค่าเหล็กรับ (บาท)": sell_value,
            "🚛 ค่าขนส่งสิบล้อ (บาท)": freight_value
        })

except Exception as e:
    st.error(f"เกิดข้อผิดพลาดในการดึงรายงานการเงิน: {e}")

# =====================================================
# 📊 แผงควบคุมสรุปตัวเลขใหญ่สะสม (Dashboard Summary)
# =====================================================
st.subheader("💰 สรุปกระแสเงินสดก้อนกว้างประจำช่วงเวลา")
col_m1, col_m2, col_m3 = st.columns(3)
with col_m1:
    st.metric(label="🔴 รวมยอดเงินจ่ายซื้อเหล็กเข้าลาน (ต้นทุนเนื้อสินค้า)", value=f"{grand_total_buy:,.2f} บาท")
with col_m2:
    st.metric(label="🟢 รวมยอดเงินรอรับจากโรงงานใหญ่ (รายรับหลัก)", value=f"{grand_total_sell:,.2f} บาท")
with col_m3:
    st.metric(label="🚛 รวมงบตั้งจ่ายค่าขนส่งสิบล้อ", value=f"{grand_total_freight:,.2f} บาท")

st.markdown("---")

# =====================================================
# 🗂️ แยกกระดานการจัดแสดงผลออกเป็น 3 แท็บ
# =====================================================
tab1, tab2, tab3 = st.tabs(["📥 แท็บ 1: รายละเอียดบิลซื้อเข้าลาน", "📤 แท็บ 2: รายละเอียดขายออก & ค่าสิบล้อ", "📅 แท็บ 3: สรุปงบรวมรายวัน"])

# ---- แท็บที่ 1: รายละเอียดบิลฝั่งซื้อเข้าลาน ----
with tab1:
    st.subheader("📥 ตารางแจกแจงประวัติการซื้อเหล็กเข้าประจำคันรถ")
    if not buy_details_rows:
        st.warning("⚠️ ไม่พบข้อมูลการรับซื้อสินค้าในช่วงวันที่เลือก")
    else:
        df_details_buy = pd.DataFrame(buy_details_rows)
        df_details_buy["น้ำหนักรับเข้า (kg)"] = df_details_buy["น้ำหนักรับเข้า (kg)"].map('{:,}'.format)
        df_details_buy["ราคาประมาณการ (บาท/kg)"] = df_details_buy["ราคาประมาณการ (บาท/kg)"].map('{:,.2f}'.format)
        df_details_buy["มูลค่าต้นทุนซื้อ (บาท)"] = df_details_buy["มูลค่าต้นทุนซื้อ (บาท)"].map('{:,.2f}'.format)
        st.dataframe(df_details_buy, use_container_width=True, hide_index=True)

# ---- แท็บที่ 2: รายละเอียดฝั่งขายออกโรงงานคู่ขนานสิบล้อ ----
with tab2:
    st.subheader("📤 ตารางแจกแจงใบตั๋วชั่งออกและงบค่าขนส่งสิบล้อ (รายคันรถ)")
    if not sell_details_rows:
        st.warning("⚠️ ไม่พบประวัติตั๋วรถวิ่งสินค้าออกลานในช่วงวันที่เลือก")
    else:
        df_details_sell = pd.DataFrame(sell_details_rows)
        df_details_sell["น้ำหนักสุทธิ (kg)"] = df_details_sell["น้ำหนักสุทธิ (kg)"].map('{:,}'.format)
        df_details_sell["💵 ยอดค่าเหล็กรับ (บาท)"] = df_details_sell["💵 ยอดค่าเหล็กรับ (บาท)"].map('{:,.2f}'.format)
        df_details_sell["🚛 ค่าขนส่งสิบล้อ (บาท)"] = df_details_sell["🚛 ค่าขนส่งสิบล้อ (บาท)"].map('{:,.2f}'.format)
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
            profit_day = s_day - b_day - f_day # ผลต่างกำไรสุทธิประจำวัน
            
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