import streamlit as st
import pandas as pd
from supabase import create_client, Client

st.header("👥 จัดการผู้ใช้และระดับสิทธิ์พนักงาน (สิทธิ์เจ้าของระบบ)")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# ---- 1. ดึงรายชื่อพนักงานทั้งหมดจากตาราง profiles ----
try:
    profiles_res = supabase.table("profiles").select("*").order("created_at").execute()
    profiles_list = profiles_res.data
except Exception as e:
    st.error(f"ไม่สามารถเรียกดูรายชื่อพนักงานได้: {e}")
    profiles_list = []

# ---- 2. แสดงตารางผู้ใช้ปัจจุบัน ----
st.subheader("📋 รายชื่อพนักงานในระบบปัจจุบัน")
if not profiles_list:
    st.info("ยังไม่มีข้อมูลพนักงานในตาราง profiles")
else:
    df_users = pd.DataFrame([{
        "รหัสผู้ใช้ (UUID)": p["id"],
        "ชื่อที่แสดง": p["display_name"],
        "ตำแหน่ง/ระดับสิทธิ์": p["role"],
        "วันที่เพิ่มเข้าระบบ": p["created_at"][:10] if p["created_at"] else "-"
    } for p in profiles_list])
    st.dataframe(df_users, use_container_width=True, hide_index=True)

st.markdown("---")

# ---- 3. ฟอร์มเพิ่มหรือปรับปรุงสิทธิ์พนักงาน ----
st.subheader("⚙️ เพิ่ม / ปรับปรุงตำแหน่งพนักงาน")
st.caption("หมายเหตุ: รหัส UUID ต้องตรงกับไอดีที่ลงทะเบียนในระบบ auth.users ของ Supabase")

with st.form("real_user_management_form"):
    user_id_input = st.text_input("รหัสผู้ใช้งาน (User UUID) *")
    display_name = st.text_input("ชื่อ-นามสกุล หรือ ชื่อเรียกของพนักงาน *")
    role_option = st.selectbox("กำหนดระดับสิทธิ์การใช้งานระบบ", ["clerk", "manager", "admin"], 
                               format_func=lambda x: "🧾 เสมียนลาน (clerk)" if x=="clerk" else ("👨‍💼 ผู้จัดการ (manager)" if x=="manager" else "🧑‍💼 เจ้าของระบบ (admin)"))
    
    submitted = st.form_submit_button("💾 บันทึกข้อมูลพนักงาน")
    if submitted:
        if not user_id_input or not display_name:
            st.error("❌ กรุณากรอกรหัส UUID และชื่อพนักงานให้ครบถ้วน")
        else:
            profile_data = {
                "id": user_id_input.strip(),
                "display_name": display_name.strip(),
                "role": role_option
            }
            try:
                # ใช้คำสั่ง upsert (ถ้าไม่มีให้เพิ่ม ถ้ามีรหัสเดิมอยู่แล้วให้แก้ไขสิทธิ์)
                supabase.table("profiles").upsert(profile_data).execute()
                st.success(f"🎉 บันทึกข้อมูลและสิทธิ์ของพนักงาน '{display_name}' เรียบร้อยแล้ว!")
                st.rerun()
            except Exception as e:
                st.error(f"ไม่สามารถบันทึกข้อมูลได้: {e}")