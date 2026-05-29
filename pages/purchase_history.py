import streamlit as st
import pandas as pd
from datetime import date, timedelta
from supabase import create_client, Client

st.header("📋 รายงานประวัติบิลซื้อเข้าลาน (แยกรายละเอียดตามประเภทเหล็ก)")
st.info("🔴 สีแดง = Physical | 🔵 สีน้ำเงิน = Reporting (แสดงรายละเอียดแยกรายแถวสินค้าจริงจากฐานข้อมูล)")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# ---- 1. ส่วนตัวกรองข้อมูล (Filters) หน้าจอ ----
col_f1, col_f2 = st.columns(2)
with col_f1:
    date_from = st.date_input("จากวันที่", date.today() - timedelta(days=30))
with col_f2:
    date_to = st.date_input("ถึงวันที่", date.today())

# ดึงประเภทสินค้าจริงมาทำตัวเลือกค้นหา
try:
    prod_types_res = supabase.table("product_types").select("id, name").execute()
    product_mapping = {p["id"]: p["name"] for p in prod_types_res.data}
    search_product_options = ["ทั้งหมด"] + list(product_mapping.values())
except Exception:
    product_mapping = {}
    search_product_options = ["ทั้งหมด"]

selected_search_prod = st.selectbox("กรองเฉพาะประเภทเหล็ก", search_product_options)

st.markdown("---")

# ---- 2. ดึงข้อมูลและเชื่อมโยงตาราง (Query & Relations) ----
try:
    # ดึงข้อมูลใบซื้อ (Header) ไลน์สินค้า (Lines) และชื่อคนบันทึก (Profiles)
    query = supabase.table("purchase_lines").select(
        "id, physical_weight, physical_price_per_ton, reporting_weight, reporting_price_per_ton, product_type_id, "
        "purchase_orders(id, purchase_date, profiles(display_name))"
    )\
    .gte("purchase_orders.purchase_date", str(date_from))\
    .lte("purchase_orders.purchase_date", str(date_to))\
    .order("id", desc=True)
    
    res = query.execute()
    raw_lines = res.data
except Exception as e:
    st.error(f"ไม่สามารถดึงข้อมูลประวัติการซื้อได้: {e}")
    raw_lines = []

# ---- 3. กรองและจัดรูปข้อมูลเพื่อแสดงผลในตาราง ----
display_rows = []

for line in raw_lines:
    # ตรวจสอบโครงสร้างกรณีเชื่อมตารางความสัมพันธ์ (Join Table)
    po = line.get("purchase_orders")
    if not po: # ข้ามหากไม่มีข้อมูลใบซื้อผูกอยู่
        continue
        
    prod_name = product_mapping.get(line["product_type_id"], "ไม่ระบุประเภท")
    
    # กรองตามประเภทเหล็กที่เลือกบนหน้าจอ
    if selected_search_prod != "ทั้งหมด" and prod_name != selected_search_prod:
        continue
        
    # คำนวณมูลค่ารวมแต่ละแถว (น้ำหนัก กก. / 1000 * ราคาต่อตัน)
    phys_value = (line["physical_weight"] / 1000) * float(line["physical_price_per_ton"])
    rep_value = (line["reporting_weight"] / 1000) * float(line["reporting_price_per_ton"])
    
    display_rows.append({
        "วันที่เข้าลาน": po["purchase_date"],
        "เลขที่บิล": f"PO-{po['id']}",
        "ประเภทเหล็ก": prod_name,
        "🔴 นน. Phys (kg)": f"{line['physical_weight']:,}",
        "🔴 ราคา/ตัน Phys": f"{float(line['physical_price_per_ton']):,.2f}",
        "🔴 รวมเงิน Phys": f"{phys_value:,.2f}",
        "🔵 นน. Rep (kg)": f"{line['reporting_weight']:,}",
        "🔵 ราคา/ตัน Rep": f"{float(line['reporting_price_per_ton']):,.2f}",
        "🔵 รวมเงิน Rep": f"{rep_value:,.2f}",
        "ผู้บันทึก": po["profiles"]["display_name"] if po["profiles"] else "ไม่ระบุชื่อ"
    })

# ---- 4. แสดงผลลัพธ์ออกหน้าจอ ----
if not display_rows:
    st.warning("⚠️ ไม่พบข้อมูลการซื้อเหล็กตรงตามเงื่อนไขที่เลือกในช่วงเวลานี้")
else:
    df_report = pd.DataFrame(display_rows)
    
    # แสดงตารางแยกรายละเอียดให้เห็นชัดเจนรายแถว
    st.subheader(f"📋 รายการเหล็กเข้าลานทั้งหมด ({len(df_report)} รายการ)")
    st.dataframe(df_report, use_container_width=True, hide_index=True)
    
    # ส่วนสรุปยอดน้ำหนักและมูลค่ารวมตามตัวกรองด้านล่างตาราง
    st.markdown("---")
    st.subheader("📊 สรุปยอดรวมตามเงื่อนไขค้นหาปัจจุบัน")
    
    # แปลงค่าน้ำหนักกลับเป็นตัวเลขเพื่อคำนวณยอดรวมสุทธิ (ลบเครื่องหมายจุลภาคออกก่อนรวม)
    total_phys_kg = sum(int(row["🔴 นน. Phys (kg)"].replace(',', '')) for row in display_rows)
    total_phys_money = sum(float(row["🔴 รวมเงิน Phys"].replace(',', '')) for row in display_rows)
    total_rep_kg = sum(int(row["🔵 นน. Rep (kg)"].replace(',', '')) for row in display_rows)
    total_rep_money = sum(float(row["🔵 รวมเงิน Rep"].replace(',', '')) for row in display_rows)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div style='background-color:#ffe6e6; padding:15px; border-radius:8px;'>", unsafe_allow_html=True)
        st.write("**🔴 ยอดรวมระบบ Physical (หน้าลานจริง)**")
        st.write(f"• น้ำหนักเหล็กรวม: **{total_phys_kg:,}** กิโลกรัม")
        st.write(f"• มูลค่าต้นทุนรวม: **{total_phys_money:,.2f}** บาท")
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col2:
        st.markdown("<div style='background-color:#e6f0ff; padding:15px; border-radius:8px;'>", unsafe_allow_html=True)
        st.write("**🔵 ยอดรวมระบบ Reporting (บัญชี/ภาษี)**")
        st.write(f"• น้ำหนักเหล็กรวม: **{total_rep_kg:,}** กิโลกรัม")
        st.write(f"• มูลค่าต้นทุนรวม: **{total_rep_money:,.2f}** บาท")
        st.markdown("</div>", unsafe_allow_html=True)