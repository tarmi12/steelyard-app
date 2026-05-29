import streamlit as st
import pandas as pd
from supabase import create_client, Client

st.header("🎯 ระบบติดตามสถานะคิวรถและสิ่งตกค้าง (Real-time Monitor)")
st.info("📊 หน้าจอสรุปสถานะรถวิ่งงานในระบบ เพื่อสแกนดูได้ทันทีโดยไม่ต้องไล่ตรวจเช็คเอกสารมือ")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# ---- 1. ดึงข้อมูลรถที่วิ่งงานค้างทั้งหมดในระบบแบบยิงสอบถามครั้งเดียว (Single Query Multi-Join) ----
try:
    # ดึงคิวงานสั่งโหลดทั้งหมด พร้อมเชื่อมข้อมูลรถ ประเภทเหล็ก ผลชั่งออก และผลปลายทาง
    query_res = supabase.table("load_orders").select(
        "id, order_date, status, freight_mode, freight_rate, "
        "trucks(plate, driver_name, company), "
        "product_types(name), "
        "weigh_out(id, net_weight, destination_factory_id, factories(name), "
        "destination_weigh_in(received_weight), "
        "sales_clearing(id))"
    ).order("id", desc=True).execute()
    
    all_jobs = query_res.data

    # ดึงประวัติการจ่ายเงินค่าขนส่งมาจับคู่ตรวจสอบ
    freight_paid_res = supabase.table("freight_payments").select("load_order_id").eq("status", "PAID").execute()
    paid_load_ids = [p["load_order_id"] for p in freight_paid_res.data]

except Exception as e:
    st.error(f"ไม่สามารถดึงข้อมูลสถานะรถยนต์ได้: {e}")
    all_jobs = []
    paid_load_ids = []

# ---- 2. แยกกลุ่มข้อมูลรถออกเป็น 3 หมวดหมู่ตามสั่งการ ----
loading_list = []      # 1. รถที่กำลังโหลดของ
in_transit_list = []   # 2. รถที่กำลังเดินทางไปโรงงาน
unpaid_freight_list = [] # 3. รถที่ลงสินค้าเสร็จแล้ว (เคลียร์บิลขายแล้ว) แต่ลานยังไม่ได้จ่ายค่าขนส่ง

for job in all_jobs:
    truck = job.get("trucks", {}) or {}
    product = job.get("product_types", {}) or {}
    
    # ดึงข้อมูลการชั่งออก (ถ้ามี)
    wo_array = job.get("weigh_out", [])
    wo = wo_array[0] if wo_array else None
    
    # 🚚 กลุ่มที่ 1: รถกำลังโหลดของ (จองคิวแล้วแต่ยังไม่ผ่านเครื่องชั่งออก สถานะเป็น PENDING)
    if job["status"] == "PENDING" and not wo:
        loading_list.append({
            "คิวสั่งโหลด": f"LO-{job['id']}",
            "วันที่สั่งคิว": job["order_date"],
            "ทะเบียนรถ": truck.get("plate", "-"),
            "คนขับ": truck.get("driver_name", "-"),
            "บริษัทขนส่ง": truck.get("company", "-"),
            "สินค้าที่รอโหลด": product.get("name", "-")
        })
        
    # 🛣️ กลุ่มที่ 2: รถกำลังเดินทาง (ชั่งออกแล้ว สถานะตัดสต็อก Physical แล้ว แต่โรงงานปลายทางยังไม่เคลียร์บิล)
    elif wo and not (wo.get("sales_clearing") and wo["sales_clearing"]):
        loading_list_factory = wo.get("factories", {}) or {}
        in_transit_list.append({
            "รหัสชั่งออก": f"WO-{wo['id']}",
            "ทะเบียนรถ": truck.get("plate", "-"),
            "คนขับ": truck.get("driver_name", "-"),
            "สินค้าบนรถ": product.get("name", "-"),
            "🔴 นน.ต้นทาง (kg)": f"{wo['net_weight']:,}",
            "โรงงานปลายทาง": loading_list_factory.get("name", "-"),
            "วันที่ชั่งออก": job["order_date"]
        })
        
    # 💰 กลุ่มที่ 3: ลงสินค้าเสร็จแล้ว (เคลียร์บิลโรงงานจบแล้ว) แต่ลานยังไม่ได้โอนจ่ายค่าขนส่งให้สิบล้อ
    elif job["status"] == "COMPLETED" and job["id"] not in paid_load_ids:
        if wo and wo.get("destination_weigh_in"):
            dest = wo["destination_weigh_in"][0]
            loading_list_factory = wo.get("factories", {}) or {}
            unpaid_freight_list.append({
                "คิวงานหลัก": f"LO-{job['id']}",
                "ทะเบียนรถ": truck.get("plate", "-"),
                "คนขับ": truck.get("driver_name", "-"),
                "บริษัทขนส่ง": truck.get("company", "-"),
                "โรงงานที่ไปลง": loading_list_factory.get("name", "-"),
                "🔴 นน.ต้นทาง (kg)": f"{wo['net_weight']:,}",
                "🟢 นน.ปลายทาง (kg)": f"{dest['received_weight']:,}" if dest['received_weight'] else "-",
                "วิธีคิดค่าขนส่ง": "เหมา" if job["freight_mode"] == "FLAT_RATE" else "ต่อตัน",
                "เรทราคา": f"{float(job['freight_rate']):,.2f}"
            })

# ---- 3. จัดทำหน้าต่างแสดงผลแยก 3 แผงควบคุม (Tabs) ----
tab1, tab2, tab3 = st.tabs([
    f"🚚 1. รถที่กำลังโหลดของ ({len(loading_list)} คัน)", 
    f"🛣️ 2. รถที่กำลังเดินทางไปโรงงาน ({len(in_transit_list)} คัน)", 
    f"💰 3. ลงของเสร็จ/ค้างจ่ายค่าขนส่ง ({len(unpaid_freight_list)} คัน)"
])

with tab1:
    st.subheader("📦 รายการรถจองคิว สแตนด์บายรอชั่งน้ำหนักออก")
    if not loading_list:
        st.success("ไม่มีรถยนต์ตกค้างในกระบวนการโหลดของ")
    else:
        st.dataframe(pd.DataFrame(loading_list), use_container_width=True, hide_index=True)

with tab2:
    st.subheader("🚛 รายการรถเหล็กวิ่งออกจากลานแล้ว อยู่ระหว่างเดินทางไปโรงงานปลายทาง")
    if not in_transit_list:
        st.success("ไม่มีรถยนต์อยู่ระหว่างการเดินทาง (โรงงานปลายทางทำการเคลียร์บิลครบหมดแล้ว)")
    else:
        st.dataframe(pd.DataFrame(in_transit_list), use_container_width=True, hide_index=True)

with tab3:
    st.subheader("💸 รายการรถสิบล้อที่ส่งของถึงเป้าหมายแล้ว รอเสมียนกดทำเรื่องโอนเงินจ่ายค่าขนส่ง")
    if not unpaid_freight_list:
        st.success("อนุมัติจ่ายเงินค่าน้ำมันและค่าขนส่งครบถ้วนแล้ว ไม่มีรายการค้างจ่าย")
    else:
        st.dataframe(pd.DataFrame(unpaid_freight_list), use_container_width=True, hide_index=True)
        st.caption("💡 แนะนำ: คุณสามารถไปตรวจสอบรายละเอียดตัวเลขส่วนหักค่าปรับอย่างละเอียดได้ที่เมนู 'จ่ายค่าขนส่ง'")