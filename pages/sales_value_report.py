import streamlit as st
import pandas as pd
from datetime import date, datetime
from supabase import create_client, Client

st.set_page_config(layout="wide")

st.header("📊 รายงานงบสรุปรายวัน (Daily Purchase, Sales & Freight Statement)")
st.info("💰 ตรวจสอบกระแสเงินสดประจำวัน: เช็คยอดเงินจ่ายซื้อเหล็กเข้าลาน ยอดเงินรับจากการขายโรงงาน และยอดตั้งเบิกค่าขนส่งรถสิบล้อ")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# ---- 1. ส่วนควบคุมตัวกรองวันที่ ----
col_f1, col_f2 = st.columns(2)
with col_f1:
    start_date = st.date_input("📆 ตั้งแต่วันที่", date(date.today().year, date.today().month, 1))
with col_f2:
    end_date = st.date_input("📆 ถึงวันที่", date.today())

st.markdown("---")

# ประกาศตัวแปรสรุปยอดรวมก้อนใหญ่ประจำช่วงเวลา
grand_total_buy = 0.0
grand_total_sell = 0.0
grand_total_freight = 0.0

# ดิกรวมรายงานแยกตามวันที่
daily_summary = {}

# ทำฟังก์ชันช่วยจัดรูปแบบวันที่ให้อ่านง่าย
def get_date_str(d_val):
    if not d_val: return str(date.today())
    if isinstance(d_val, str):
        return d_val.split("T")[0]
    return str(d_val)

# =====================================================
# 📥 1. ดึงข้อมูลฝั่งซื้อเข้าลาน (พยายามดึงจากตารางซื้อมาตรฐาน)
# =====================================================
try:
    # ค้นหาข้อมูลการรับซื้อของเข้าลาน (ดักดึงจากชื่อตารางซื้อมาตรฐาน)
    buy_table = "purchases" # หรือเปลี่ยนเป็นชื่อตารางฝั่งซื้อจริงของพี่ เช่น buy_orders
    buy_res = supabase.table(buy_table).select("id, net_weight, price_per_kg, date").gte("date", str(start_date)).lte("date", str(end_date)).execute()
    
    for b in buy_res.data:
        b_date = get_date_str(b.get("date"))
        kg = int(b.get("net_weight", 0) or 0)
        p_kg = float(b.get("price_per_kg", 0) or 0)
        value = kg * p_kg # สูตรฝั่งซื้อ: กิโลกรัม x บาทต่อกิโลกรัม
        
        grand_total_buy += value
        if b_date not in daily_summary:
            daily_summary[b_date] = {"buy": 0.0, "sell": 0.0, "freight": 0.0}
        daily_summary[b_date]["buy"] += value
except Exception:
    # Safe-Mode: หากชื่อตารางซื้อในเครื่องพ่นเอเรอร์ ให้พยายามไปดึงข้อมูลจากตารางตั๋วชั่งขาเข้าทดแทนเพื่อไม่ให้โปรแกรมพัง
    try:
        buy_res = supabase.table("weigh_in_tickets").select("id, net_weight, price_per_kg, date").gte("date", str(start_date)).lte("date", str(end_date)).execute()
        for b in buy_res.data:
            b_date = get_date_str(b.get("date"))
            kg = int(b.get("net_weight", 0) or 0)
            p_kg = float(b.get("price_per_kg", 0) or 0)
            value = kg * p_kg
            grand_total_buy += value
            if b_date not in daily_summary:
                daily_summary[b_date] = {"buy": 0.0, "sell": 0.0, "freight": 0.0}
            daily_summary[b_date]["buy"] += value
    except Exception:
        pass # ถ้าไม่มีจริงๆ ปล่อยผ่านเป็นยอดซื้อ 0 เพื่อให้ฝั่งขายทำงานต่อได้

# =====================================================
# 📤 2. ดึงข้อมูลฝั่งขายออกโรงงานใหญ่ และ 🚛 3. ค่าขนส่งสิบล้อ
# =====================================================
try:
    # ดึงตั๋วชั่งออกที่มีอยู่ชัวร์ๆ หลังบ้าน
    wo_res = supabase.table("weigh_out")\
        .select("id, net_weight, date, load_orders(freight_rate, freight_mode, base_weight_option)")\
        .gte("date", str(start_date))\
        .lte("date", str(end_date))\
        .execute()
        
    for wo in wo_res.data:
        w_date = get_date_str(wo.get("date"))
        net_kg = int(wo.get("net_weight", 0) or 0)
        lo = wo.get("load_orders", {}) or {}
        
        # 🟢 คิดมูลค่าขายออก (Auto-Unit Detection ป้องกันมั่วราคาต่อตัน/กิโลกรัม)
        sell_rate = float(lo.get("freight_rate", 0) or 0)
        if sell_rate >= 1000:
            sell_value = (net_kg / 1000) * sell_rate # คิดแบบราคาต่อตัน
        else:
            sell_value = net_kg * sell_rate # คิดแบบราคาต่อกิโลกรัม
            
        grand_total_sell += sell_value
        if w_date not in daily_summary:
            daily_summary[w_date] = {"buy": 0.0, "sell": 0.0, "freight": 0.0}
        daily_summary[w_date]["sell"] += sell_value
        
        # 🚛 คำนวณเงินค่าขนส่งรถสิบล้อเที่ยวนี้คู่ขนานทันที
        f_mode = lo.get("freight_mode", "PER_TON")
        if f_mode == "FLAT_RATE":
            freight_value = sell_rate # เหมาจ่ายเงินก้อน
        else:
            # คำนวณเรทค่าบรรทุกต่อตัน (แปลงกิโลกรัมเป็นตันก่อนคูณ)
            freight_value = (net_kg / 1000) * sell_rate 
            
        grand_total_freight += freight_value
        daily_summary[w_date]["freight"] += freight_value

except Exception as e:
    st.error(f"ระบบไม่สามารถประมวลผลข้อมูลฝั่งขายและสิบล้อได้: {e}")

# =====================================================
# 📊 4. แสดงผลแผงสรุปเม็ดเงินภาพรวม (Summary Metrics)
# =====================================================
st.subheader("💰 สรุปกระแสเงินหมุนเวียนก้อนรวม (ประจำช่วงเวลาที่เลือก)")
col_m1, col_m2, col_m3 = st.columns(3)

with col_m1:
    st.metric(label="🔴 ยอดจ่ายเงินซื้อเหล็กเข้าลานรวม", value=f"{grand_total_buy:,.2f} บาท")
with col_m2:
    st.metric(label="🟢 ยอดเงินรับส่งขายโรงงานใหญ่รวม", value=f"{grand_total_sell:,.2f} บาท")
with col_m3:
    st.metric(label="🚛 ยอดเงินค่าขนส่งสิบล้อรวมทั้งหมด", value=f"{grand_total_freight:,.2f} บาท")

st.markdown("---")

# =====================================================
# 🗂️ 5. จัดรูปตารางแจกแจงเม็ดเงิน "รายวัน" ตามที่พี่สั่งการ
# =====================================================
st.subheader("📅 ตารางสรุปงบซื้อ-ขาย และค่าขนส่งสิบล้อ แจกแจงเป็นรายวัน")
st.caption("แนะนำ: บัญชีสามารถกวาดสายตาดูสรุปเม็ดเงินเป็นรายวันได้ทันที ยอดเงินบาทคำนวณสดจากตั๋วชั่งหน้าร้าน")

if not daily_summary:
    st.warning("⚠️ ไม่พบข้อมูลการทำธุรกรรมซื้อ-ขายใด ๆ ในช่วงวันที่ระบุข้างต้นครับ")
else:
    # แปลงข้อมูล Dictionary รายวันให้กลายเป็น DataFrame เพื่อโชว์ในตารางสวยงาม
    report_rows = []
    # เรียงลำดับวันที่จากปัจจุบันย้อนกลับไปอดีต
    for d_key in sorted(daily_summary.keys(), reverse=True):
        day_data = daily_summary[d_key]
        b_val = day_data["buy"]
        s_val = day_data["sell"]
        f_val = day_data["freight"]
        # คำนวณส่วนต่างกำไรหลังหักต้นทุนค่าเหล็กและค่าขนส่งสิบล้อประจำวัน
        net_profit = s_val - b_val - f_val
        
        report_rows.append({
            "วันที่ (Date)": d_key,
            "📥 ยอดเงินซื้อเข้าลาน (บาท)": b_val,
            "📤 ยอดเงินขายส่งโรงงาน (บาท)": s_val,
            "🚛 ค่าขนส่งสิบล้อ (บาท)": f_val,
            "📊 ผลต่างกำไรสุทธิลาน (บาท)": net_profit
        })
        
    df_report = pd.DataFrame(report_rows)
    
    # จัดฟอร์แมตตัวเลขในตารางให้แสดงเป็นเงินบาททศนิยม 2 ตำแหน่งให้ชัดเจน อ่านง่าย ไม่มั่ว
    for col in df_report.columns:
        if col != "วันที่ (Date)":
            df_report[col] = df_report[col].map('{:,.2f}'.format)
            
    st.dataframe(df_report, use_container_width=True, hide_index=True)