import streamlit as st
import pandas as pd
from supabase import create_client, Client

st.header("📈 รายงานสรุปยอดการขาย, กำไร และภาษี (ข้อมูลจริง)")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

try:
    # 1. ดึงข้อมูลฝั่งซื้อมาหาต้นทุนเฉลี่ย
    purchase_res = supabase.table("purchase_lines").select("physical_weight, physical_price_per_ton").execute()
    total_buy_kg = sum(p["physical_weight"] for p in purchase_res.data)
    total_buy_value = sum((p["physical_weight"] / 1000) * float(p["physical_price_per_ton"]) for p in purchase_res.data)
    avg_cost_per_kg = total_buy_value / total_buy_kg if total_buy_kg > 0 else 0.0

    # 2. ดึงข้อมูลฝั่งขายจริง
    sales_res = supabase.table("sales_clearing").select("id, total_amount, vat_amount, discount, clearing_date, weigh_out(net_weight)").execute()
    sales_data = sales_res.data
except Exception as e:
    st.error(f"ไม่สามารถดึงข้อมูลรายงานได้: {e}")
    sales_data = []

if not sales_data:
    st.info("ยังไม่มีข้อมูลการเคลียร์บิลขายในระบบ")
else:
    # คำนวณยอดรวมเชิงบริหาร
    total_sales_before_vat = sum(float(s["total_amount"]) for s in sales_data)
    total_vat = sum(float(s["vat_amount"]) for s in sales_data)
    total_discount = sum(float(s["discount"]) for s in sales_data)
    total_sales_gross = total_sales_before_vat + total_vat
    
    # คำนวณต้นทุนขาย (น้ำหนักที่ขายได้หน้าลาน x ต้นทุนเฉลี่ย)
    total_sold_kg = sum(s["weigh_out"]["net_weight"] for s in sales_data)
    total_cost_of_goods = total_sold_kg * avg_cost_per_kg
    estimated_profit = total_sales_before_vat - total_cost_of_goods

    # ---- แสดงผล Dashboard 📊 ----
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("💰 รายรับรวม (รวม VAT)", f"{total_sales_gross:,.2f} บาท")
    col2.metric("📉 ส่วนลดให้โรงงาน", f"{total_discount:,.2f} บาท")
    col3.metric("🧾 ภาษีขายสะสม (VAT 7%)", f"{total_vat:,.2f} บาท")
    col4.metric("📈 กำไรขั้นต้นโดยประมาณ", f"{estimated_profit:,.2f} บาท", delta=f"{((estimated_profit/total_sales_before_vat)*100 if total_sales_before_vat>0 else 0):.1f}%")

    st.markdown("---")
    st.subheader("📋 ประวัติรายการบิลขายและภาษี")
    
    report_df = pd.DataFrame([{
        "เลขที่บิลขาย": f"SC-{s['id']}",
        "วันที่เคลียร์บิล": s["clearing_date"],
        "น้ำหนักชั่งออก (kg)": f"{s['weigh_out']['net_weight']:,}",
        "มูลค่าสินค้า (ก่อน VAT)": f"{float(s['total_amount']):,.2f}",
        "ภาษีขาย (VAT)": f"{float(s['vat_amount']):,.2f}",
        "ส่วนลด (บาท)": f"{float(s['discount']):,.2f}",
        "ยอดรวมสุทธิ": f"{float(s['total_amount'])+float(s['vat_amount']):,.2f}"
    } for s in sales_data])
    st.dataframe(report_df, use_container_width=True, hide_index=True)