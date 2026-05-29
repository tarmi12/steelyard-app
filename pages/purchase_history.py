import streamlit as st
import pandas as pd
from supabase import create_client, Client

st.header("📋 ประวัติการบันทึกบิลซื้อเข้าลาน (สต็อกคู่จริง)")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

try:
    # ดึงประวัติใบซื้อและคำนวณยอดรวมของแต่ละบิล
    orders_res = supabase.table("purchase_orders").select("id, purchase_date, profiles(display_name), purchase_lines(physical_weight, reporting_weight)").execute()
    orders_data = orders_res.data
except Exception as e:
    st.error(f"ไม่สามารถดึงข้อมูลประวัติการซื้อได้: {e}")
    orders_data = []

if not orders_data:
    st.info("ยังไม่มีข้อมูลประวัติการบันทึกซื้อเข้าในฐานข้อมูล")
else:
    # จัดรูปตารางเพื่อแสดงผลหน้ารวม
    summary_rows = []
    for o in orders_data:
        lines = o.get("purchase_lines", [])
        total_phys = sum(l["physical_weight"] for l in lines)
        total_rep = sum(l["reporting_weight"] for l in lines)
        
        summary_rows.append({
            "เลขที่ใบซื้อ": f"PO-{o['id']}",
            "วันที่ซื้อสินค้า": o["purchase_date"],
            "รวม 🔴 Physical (kg)": f"{total_phys:,}",
            "รวม 🔵 Reporting (kg)": f"{total_rep:,}",
            "จำนวนรายการ": len(lines),
            "ผู้บันทึกรายการ": o["profiles"]["display_name"] if o["profiles"] else "ไม่ระบุชื่อ"
        })
        
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)