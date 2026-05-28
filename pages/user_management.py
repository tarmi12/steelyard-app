import streamlit as st

st.header("👥 จัดการผู้ใช้ (เจ้าของเท่านั้น)")

st.subheader("เพิ่มผู้ใช้ใหม่")
with st.form("add_user_form"):
    email = st.text_input("อีเมล")
    display_name = st.text_input("ชื่อที่แสดง")
    role = st.selectbox("บทบาท", ["clerk", "manager", "owner"])
    password = st.text_input("รหัสผ่าน", type="password")
    if st.form_submit_button("เพิ่มผู้ใช้"):
        # TODO: ใช้ Supabase Auth สร้าง user และเพิ่มในตาราง profiles
        st.success(f"เพิ่มผู้ใช้ {display_name} ({role}) เรียบร้อย!")

st.subheader("รายชื่อผู้ใช้ปัจจุบัน (ตัวอย่าง)")
users = [
    {"อีเมล": "owner@test.com", "ชื่อ": "เจ้าของ", "บทบาท": "owner"},
    {"อีเมล": "manager@test.com", "ชื่อ": "ผู้จัดการ", "บทบาท": "manager"},
    {"อีเมล": "clerk@test.com", "ชื่อ": "เสมียน", "บทบาท": "clerk"},
]
st.table(users)

if st.button("🗑️ ลบผู้ใช้ (เลือก)"):
    st.write("ฟังก์ชันลบผู้ใช้จะมาในภายหลัง")