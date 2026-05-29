import streamlit as st
import pandas as pd
from supabase import create_client, Client

st.header("⚙️ ตั้งค่าระบบส่วนกลาง (ระบบใช้งานจริงบนฐานข้อมูล)")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

tab1, tab2 = st.tabs(["⚙️ อัตราและเกณฑ์ควบคุม", "🏭 จัดการโรงงานปลายทาง"])

with tab1:
    st.subheader("ปรับเปลี่ยนเกณฑ์คำนวณและค่าปรับสิบล้อ")
    
    # ดึงค่าปัจจุบันจากฐานข้อมูลมาแสดงในฟอร์ม
    try:
        settings_res = supabase.table("system_settings").select("*").execute()
        current_settings = {s["key"]: s["value"] for s in settings_res.data}
    except Exception as e:
        st.error(f"ไม่สามารถดึงการตั้งค่าได้: {e}")
        current_settings = {}

    with st.form("real_settings_form"):
        st.write("**เกณฑ์น้ำหนักขาดระหว่างทาง (Transit Loss)**")
        transit_pct = st.number_input("เกณฑ์เปอร์เซ็นต์น้ำหนักขาดที่ยอมรับได้ (%)", min_value=0.0, max_value=10.0, step=0.1, 
                                      value=float(current_settings.get("transit_loss_threshold_percent", 0.5)))
        transit_kg = st.number_input("เกณฑ์น้ำหนักขาดสูงสุดที่ยอมรับได้ (กิโลกรัม)", min_value=0, step=1, 
                                     value=int(current_settings.get("transit_loss_threshold_kg", 50)))

        st.write("---")
        st.write("**อัตราค่าปรับและค่าขนส่งตั้งต้น**")
        penalty_rate = st.number_input("อัตราค่าปรับน้ำหนักขาดเกินเกณฑ์ (บาท / กิโลกรัม)", min_value=0.0, step=1.0, 
                                       value=float(current_settings.get("penalty_rate_per_kg", 10.0)))
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            flat_rate = st.number_input("อัตราเหมาเที่ยวเริ่มต้น (บาท / เที่ยว)", min_value=0.0, step=100.0, 
                                        value=float(current_settings.get("freight_flat_rate", 3000.0)))
        with col_f2:
            per_ton_rate = st.number_input("อัตราต่อตันเริ่มต้น (บาท / ตัน)", min_value=0.0, step=10.0, 
                                           value=float(current_settings.get("freight_per_ton_rate", 100.0)))
            
        base_weight = st.radio("ฐานน้ำหนักเริ่มต้นสำหรับคิดเงินแบบต่อตัน", ["ORIGIN", "DESTINATION"], 
                               format_func=lambda x: "น้ำหนักต้นทาง (ลานเหล็ก)" if x=="ORIGIN" else "น้ำหนักปลายทาง (โรงงานรับซื้อ)",
                               index=0 if current_settings.get("default_base_weight", "ORIGIN") == "ORIGIN" else 1)

        submitted = st.form_submit_button("💾 บันทึกการตั้งค่าลงฐานข้อมูลจริง")
        if submitted:
            try:
                # อัปเดตข้อมูลทีละ Key เข้าตาราง system_settings
                updates = [
                    {"key": "transit_loss_threshold_percent", "value": str(transit_pct)},
                    {"key": "transit_loss_threshold_kg", "value": str(transit_kg)},
                    {"key": "penalty_rate_per_kg", "value": str(penalty_rate)},
                    {"key": "freight_flat_rate", "value": str(flat_rate)},
                    {"key": "freight_per_ton_rate", "value": str(per_ton_rate)},
                    {"key": "default_base_weight", "value": base_weight}
                ]
                for u in updates:
                    supabase.table("system_settings").upsert(u).execute()
                
                st.success("🎉 บันทึกการตั้งค่าระบบและเกณฑ์คำนวณใหม่เรียบร้อยแล้ว!")
                # อัปเดตเซสชันปัจจุบันทันที
                st.session_state.transit_loss_threshold_percent = str(transit_pct)
                st.session_state.transit_loss_threshold_kg = str(transit_kg)
                st.session_state.penalty_rate_per_kg = str(penalty_rate)
                st.rerun()
            except Exception as e:
                st.error(f"ไม่สามารถบันทึกค่าระบบได้: {e}")

with tab2:
    st.subheader("🏬 รายชื่อโรงงานคู่ค้าปลายทาง")
    
    # ดึงข้อมูลโรงงานจริงจากฐานข้อมูล
    try:
        factory_res = supabase.table("factories").select("*").order("id").execute()
        factories_list = factory_res.data
    except Exception as e:
        factories_list = []

    if factories_list:
        df_fac = pd.DataFrame([{"ID": f["id"], "ชื่อโรงงานปลายทาง": f["name"], "รหัสย่อโรงงาน": f["code"] or "-"} for f in factories_list])
        st.dataframe(df_fac, use_container_width=True, hide_index=True)

    with st.expander("➕ เพิ่มโรงงานปลายทางแห่งใหม่"):
        with st.form("add_factory_form"):
            f_name = st.text_input("ชื่อโรงงานซื้อเหล็ก *")
            f_code = st.text_input("รหัสย่อโรงงาน (ถ้ามี)")
            
            if st.form_submit_button("🏭 บันทึกโรงงานใหม่"):
                if not f_name.strip():
                    st.error("กรุณาระบุชื่อโรงงาน")
                else:
                    try:
                        supabase.table("factories").insert({"name": f_name.strip(), "code": f_code.strip() or None}).execute()
                        st.success(f"เพิ่มโรงงาน {f_name} เรียบร้อย!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาด: {e}")