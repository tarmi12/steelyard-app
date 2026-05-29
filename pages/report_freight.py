import streamlit as st
import pandas as pd
from supabase import create_client, Client

st.header("📉 รายงานค่าขนส่ง, ค่าปรับ และส่วนต่างน้ำหนักขาด")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

try:
    # ดึงข้อมูลประวัติการจ่ายค่าขนส่งทั้งหมด
    payments_res = supabase.table("freight_payments").select("id, calculated_freight, transit_loss_kg, penalty, net_pay, paid_date, load_orders(trucks(plate))").eq("status", "PAID").execute()
    payments_data = payments_res.data
except Exception as e:
    st.error(f"ไม่สามารถดึงข้อมูลรายงานค่าขนส่งได้: {e}")
    payments_data = []

if not payments_data:
    st.info("ยังไม่มีข้อมูลประวัติการจ่ายค่าขนส่งในระบบ")
else:
    total_freight = sum(float(p["calculated_freight"]) for p in payments_data)
    total_penalty = sum(float(p["penalty"]) for p in payments_data)
    total_net_pay = sum(float(p["net_pay"]) for p in payments_data)
    total_loss_kg = sum(p["transit_loss_kg"] for p in payments_data)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🚛 ยอดค่าขนส่งตั้งต้น", f"{total_freight:,.2f} บาท")
    col2.metric("🚨 ยอดรวมค่าปรับสิบล้อ", f"{total_penalty:,.2f} บาท")
    col3.metric("💵 ค่าขนส่งจ่ายสุทธิ", f"{total_net_pay:,.2f} บาท")
    col4.metric("⚖️ น้ำหนักขาดรวมทั้งหมด", f"{total_loss_kg:,} kg")

    st.markdown("---")
    st.subheader("📜 บันทึกรายการหักเงินค่าขนส่งแยกรายเที่ยว")
    
    df = pd.DataFrame([{
        "รหัสจ่ายเงิน": f"FP-{p['id']}",
        "วันที่จ่ายเงิน": p["paid_date"],
        "ทะเบียนรถ": p["load_orders"]["trucks"]["plate"],
        "ค่าขนส่งเต็ม": f"{float(p['calculated_freight']):,.2f}",
        "น้ำหนักขาด (kg)": p["transit_loss_kg"],
        "โดนหักค่าปรับ (บาท)": f"{float(p['penalty']):,.2f}",
        "ยอดจ่ายจริง": f"{float(p['net_pay']):,.2f}"
    } for p in payments_data])
    st.dataframe(df, use_container_width=True, hide_index=True)