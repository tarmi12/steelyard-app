import streamlit as st
import pandas as pd
from supabase import create_client, Client

st.header("📊 แดชบอร์ดวิเคราะห์สรุปผลงานลานเหล็กไทย (ข้อมูลจริง)")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

try:
    # 1. คำนวณหาจำนวนรถวิ่งงานทั้งหมด
    load_orders_res = supabase.table("load_orders").select("status").execute()
    total_trucks_jobs = len(load_orders_res.data)
    pending_jobs = len([l for l in load_orders_res.data if l["status"] == "PENDING"])
    completed_jobs = len([l for l in load_orders_res.data if l["status"] == "COMPLETED"])

    # 2. ดึงยอดเงินรายได้และภาษีจากการขายจริงมาสรุปผล
    sales_res = supabase.table("sales_clearing").select("total_amount, vat_amount, clearing_date").execute()
    sales_data = sales_res.data
except Exception as e:
    st.error(f"ไม่สามารถเชื่อมข้อมูลแดชบอร์ดบริหารได้: {e}")
    sales_data = []

# คำนวณสถิติการเงินจริง
total_revenue = sum(float(s["total_amount"]) for s in sales_data)
total_vat_collected = sum(float(s["vat_amount"]) for s in sales_data)

# ---- สรุปสถิติสำคัญด้านบน (KPI Cards) ----
col_m1, col_m2, col_m3, col_m4 = st.columns(4)
col_m1.metric("💰 ยอดขายสะสมหน้าลาน", f"{total_revenue:,.2f} บาท")
col_m2.metric("🧾 ภาษีขายสะสม", f"{total_vat_collected:,.2f} บาท")
col_m3.metric("🚚 จำนวนเที่ยวรถวิ่งงานทั้งหมด", f"{total_trucks_jobs:,} เที่ยว")
col_m4.metric("✅ ปิดงานสำเร็จแล้ว", f"{completed_jobs:,} เที่ยว", delta=f"รอชั่งออกอยู่ {pending_jobs} คัน")

st.markdown("---")

# ---- ส่วนกราฟสถิติสดจากการขายจริง ----
st.subheader("📈 กราฟแสดงแนวโน้มรายได้แยกตามวันที่เคลียร์บิลจริง")

if not sales_data:
    st.info("ยังไม่มีประวัติยอดการเคลียร์บิลขายมาแสดงผลกราฟ")
else:
    # นำข้อมูลมาแปลงเป็นตารางเพื่อรวมกลุ่มยอดรายวัน (Groupby Date)
    raw_df = pd.DataFrame(sales_data)
    raw_df["total_amount"] = raw_df["total_amount"].astype(float)
    
    # รวมผลยอดรายวัน
    chart_df = raw_df.groupby("clearing_date")["total_amount"].sum().reset_index()
    chart_df = chart_df.rename(columns={"clearing_date": "วันที่เคลียร์บิล", "total_amount": "ยอดรายได้ก่อน VAT (บาท)"})
    
    # แสดงกราฟแท่งบน Streamlit
    st.bar_chart(data=chart_df, x="วันที่เคลียร์บิล", y="ยอดรายได้ก่อน VAT (บาท)")