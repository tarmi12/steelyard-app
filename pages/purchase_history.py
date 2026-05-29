import streamlit as st
import pandas as pd
from datetime import date, timedelta
from supabase import create_client, Client

st.header("📋 รายงานประวัติบิลซื้อเข้าลาน (ระบบจัดการและแก้ไขสต็อกจริง)")
st.info("🔴 สีแดง = Physical | 🔵 สีน้ำเงิน = Reporting (สิทธิ์ Admin เจ้าของระบบสามารถแก้ไขข้อมูลย้อนหลังได้จากหน้านี้)")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# ตัวแปรควบคุมการส่งข้อมูลซ้ำ (Anti-Duplicate Switch)
if "is_saving" not in st.session_state:
    st.session_state.is_saving = False

# ---- 1. ส่วนตัวกรองข้อมูล (Filters) ----
col_f1, col_f2 = st.columns(2)
with col_f1:
    date_from = st.date_input("จากวันที่", date.today() - timedelta(days=30))
with col_f2:
    date_to = st.date_input("ถึงวันที่", date.today())

# ดึงประเภทสินค้าจริง
try:
    prod_types_res = supabase.table("product_types").select("id, name").execute()
    product_mapping = {p["id"]: p["name"] for p in prod_types_res.data}
    search_product_options = ["ทั้งหมด"] + list(product_mapping.values())
except Exception:
    product_mapping = {}
    search_product_options = ["ทั้งหมด"]

selected_search_prod = st.selectbox("กรองเฉพาะประเภทเหล็ก", search_product_options)

st.markdown("---")

# ---- 2. ดึงข้อมูลจากฐานข้อมูล ----
try:
    query = supabase.table("purchase_lines").select(
        "id, physical_weight, physical_price_per_ton, reporting_weight, reporting_price_per_ton, product_type_id, purchase_order_id, "
        "purchase_orders(id, purchase_date, profiles(display_name))"
    )\
    .gte("purchase_orders.purchase_date", str(date_from))\
    .lte("purchase_orders.purchase_date", str(date_to))\
    .order("id", desc=True)
    
    res = query.execute()
    raw_lines = res.data
except Exception as e:
    st.error(f"ไม่สามารถดึงข้อมูลได้: {e}")
    raw_lines = []

# ---- 3. จัดรูปข้อมูลเพื่อแสดงผลในตาราง ----
display_rows = []
raw_mapping_by_id = {} # เก็บข้อมูลดิบไว้ใช้อ้างอิงตอนแก้ไข

for line in raw_lines:
    po = line.get("purchase_orders")
    if not po:
        continue
        
    prod_name = product_mapping.get(line["product_type_id"], "ไม่ระบุประเภท")
    if selected_search_prod != "ทั้งหมด" and prod_name != selected_search_prod:
        continue
        
    raw_mapping_by_id[str(line["id"])] = line
    
    phys_value = (line["physical_weight"] / 1000) * float(line["physical_price_per_ton"])
    rep_value = (line["reporting_weight"] / 1000) * float(line["reporting_price_per_ton"])
    
    display_rows.append({
        "รหัสรายการ (Line ID)": line["id"],
        "วันที่เข้าลาน": po["purchase_date"],
        "เลขที่บิลบอร์ด": f"PO-{po['id']}",
        "ประเภทเหล็ก": prod_name,
        "🔴 นน. Phys (kg)": line["physical_weight"],
        "🔴 ราคา/ตัน Phys": float(line["physical_price_per_ton"]),
        "🔴 รวมเงิน Phys": phys_value,
        "🔵 นน. Rep (kg)": line["reporting_weight"],
        "🔵 ราคา/ตัน Rep": float(line["reporting_price_per_ton"]),
        "🔵 รวมเงิน Rep": rep_value,
        "ผู้บันทึก": po["profiles"]["display_name"] if po["profiles"] else "ไม่ระบุชื่อ"
    })

# แสดงตารางรายงาน
if not display_rows:
    st.warning("⚠️ ไม่พบข้อมูลการซื้อเหล็กตรงตามเงื่อนไข")
else:
    df_report = pd.DataFrame(display_rows)
    st.subheader(f"📋 รายการเหล็กเข้าลานทั้งหมด ({len(df_report)} รายการ)")
    st.dataframe(df_report, use_container_width=True, hide_index=True)

    # ---- 4. ระบบแก้ไขข้อมูลสต็อกสำหรับเจ้าของลาน (Admin Only) ----
    if st.session_state.role == "admin":
        st.markdown("---")
        st.subheader("🛠️ แผงควบคุมการแก้ไขสต็อกและราคา (เฉพาะเจ้าของ)")
        
        # เลือก Line ID ที่ต้องการแก้ไขจากตารางด้านบน
        selected_edit_id = st.selectbox("เลือก รหัสรายการ (Line ID) ที่ต้องการแก้ไขข้อมูล", [str(row["รหัสรายการ (Line ID)"]) for row in display_rows])
        
        if selected_edit_id:
            target_line = raw_mapping_by_id[selected_edit_id]
            
            # เปิดฟอร์มสำหรับแก้ไขข้อมูล
            with st.form("edit_stock_form"):
                st.warning(f"กำลังแก้ไขรายการ รหัส: {selected_edit_id} (บิลเลขที่: PO-{target_line['purchase_orders']['id']})")
                
                col1, col2 = st.columns(2)
                with col1:
                    new_prod_name = st.selectbox("แก้ไขประเภทเหล็ก", list(product_mapping.values()), 
                                                 index=list(product_mapping.keys()).index(target_line["product_type_id"]))
                    new_pw = st.number_input("แก้ไข 🔴 นน.Physical (kg)", min_value=0, value=int(target_line["physical_weight"]), step=10)
                    new_pp = st.number_input("แก้ไข 🔴 ราคา/ตัน Phys", min_value=0.0, value=float(target_line["physical_price_per_ton"]), step=100.0)
                with col2:
                    st.write("") # เว้นช่องว่างให้สมดุล
                    new_rw = st.number_input("แก้ไข 🔵 นน.Reporting (kg)", min_value=0, value=int(target_line["reporting_weight"]), step=10)
                    new_rp = st.number_input("แก้ไข 🔵 ราคา/ตัน Rep", min_value=0.0, value=float(target_line["reporting_price_per_ton"]), step=100.0)
                
                # ปุ่มบันทึกการแก้ไขพร้อมระบบป้องกันการกดย้ำ
                submit_disabled = st.session_state.is_saving
                btn_label = "⌛ กำลังบันทึกและปรับยอดสต็อก..." if st.session_state.is_saving else "💾 ยืนยันการอัปเดตข้อมูลและปรับสต็อกจริง"
                
                edited_submitted = st.form_submit_button(btn_label, disabled=submit_disabled)
                
                if edited_submitted:
                    st.session_state.is_saving = True
                    st.rerun() # สั่งรีรันเพื่อให้ปุ่มปิดการใช้งานทันที ป้องกันการกดย้ำ

# ---- 5. ส่วนประมวลผลการบันทึกข้อมูลแก้ไขลงฐานข้อมูลจริง ----
if st.session_state.is_saving:
    try:
        # เตรียมไอดีสินค้าใหม่
        new_prod_id = [k for k, v in product_mapping.items() if v == new_prod_name][0]
        
        # 1. อัปเดตข้อมูลที่ตาราง purchase_lines
        supabase.table("purchase_lines").update({
            "product_type_id": new_prod_id,
            "physical_weight": new_pw,
            "physical_price_per_ton": new_pp,
            "reporting_weight": new_rw,
            "reporting_price_per_ton": new_rp
        }).eq("id", selected_edit_id).execute()
        
        # 2. อัปเดตข้อมูลธุรกรรมสต็อกคู่ (inventory_transactions) ที่ผูกกับรายการนี้ให้เปลี่ยนตามจริง
        # อัปเดตฝั่ง PHYSICAL
        supabase.table("inventory_transactions").update({
            "quantity": new_pw,
            "unit_cost": (new_pp / 1000)
        }).eq("reference_type", "PURCHASE_LINE").eq("reference_id", selected_edit_id).eq("stock_type", "PHYSICAL").execute()
        
        # อัปเดตฝั่ง REPORTING
        supabase.table("inventory_transactions").update({
            "quantity": new_rw,
            "unit_cost": (new_rp / 1000)
        }).eq("reference_type", "PURCHASE_LINE").eq("reference_id", selected_edit_id).eq("stock_type", "REPORTING").execute()
        
        # 3. บันทึกประวัติการแก้ไขลง Audit Log
        change_log_text = f"เจ้าของแก้ไขรายการสินค้า Line ID {selected_edit_id}: ปรับ นน. Phys เป็น {new_pw} kg, Rep เป็น {new_rw} kg"
        supabase.table("purchase_edit_logs").insert({
            "purchase_order_id": target_line["purchase_order_id"],
            "edited_by": st.session_state.user_id,
            "changes": change_log_text
        }).execute()
        
        st.success("🎉 อัปเดตข้อมูลบิลซื้อและปรับยอดสต็อกคู่เรียบร้อยอย่างปลอดภัย!")
    except Exception as error:
        st.error(f"เกิดข้อผิดพลาดในการอัปเดตข้อมูล: {error}")
    finally:
        # ปลดล็อกปุ่มให้กลับมาทำงานปกติ
        st.session_state.is_saving = False
        st.rerun()