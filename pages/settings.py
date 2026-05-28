import streamlit as st
import pandas as pd

st.header("⚙️ ตั้งค่าระบบ")

tab1, tab2 = st.tabs(["ค่าทั่วไป", "🏭 โรงงานปลายทาง"])

with tab1:
    with st.form("general_settings_form"):
        st.subheader("เกณฑ์น้ำหนักขาด (Transit Loss)")
        transit_pct = st.number_input("เกณฑ์ % ของน้ำหนักต้นทาง", min_value=0.0, max_value=10.0, step=0.1, value=st.session_state.transit_loss_pct)
        transit_kg = st.number_input("เกณฑ์น้ำหนักขาดสูงสุด (กก.)", min_value=0, step=1, value=st.session_state.transit_loss_kg)

        st.subheader("อัตราค่าปรับน้ำหนักเกินเกณฑ์")
        penalty_rate = st.number_input("ค่าปรับต่อกิโลกรัม (บาท)", min_value=0.0, step=1.0, value=st.session_state.penalty_rate_per_kg, help="ตั้งสูงมากถ้ายังไม่ต้องการหัก")

        st.subheader("อัตราค่าขนส่งเริ่มต้น")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            flat_rate = st.number_input("เหมาเที่ยว (บาท/เที่ยว)", min_value=0.0, step=100.0, value=st.session_state.freight_flat_rate)
        with col_f2:
            per_ton_rate = st.number_input("ต่อตัน (บาท/ตัน)", min_value=0.0, step=10.0, value=st.session_state.freight_per_ton_rate)
        base_weight = st.radio("ฐานน้ำหนักเริ่มต้นสำหรับ PER_TON", ["ต้นทาง", "ปลายทาง"], index=0 if st.session_state.default_base_weight=="ต้นทาง" else 1)

        st.markdown("---")
        st.subheader("🔗 การเชื่อมต่อภายนอก")
        google_drive = st.text_input("Google Drive Folder ID", value=st.session_state.google_drive_folder_id)
        line_token = st.text_input("LINE Channel Access Token", value=st.session_state.line_channel_token, type="password")
        line_oa = st.text_input("LINE OA URL", value=st.session_state.line_oa_url)

        submitted = st.form_submit_button("💾 บันทึกการตั้งค่า")
        if submitted:
            st.session_state.transit_loss_pct = transit_pct
            st.session_state.transit_loss_kg = transit_kg
            st.session_state.penalty_rate_per_kg = penalty_rate
            st.session_state.freight_flat_rate = flat_rate
            st.session_state.freight_per_ton_rate = per_ton_rate
            st.session_state.default_base_weight = base_weight
            st.session_state.google_drive_folder_id = google_drive
            st.session_state.line_channel_token = line_token
            st.session_state.line_oa_url = line_oa
            st.success("บันทึกการตั้งค่าเรียบร้อย!")
            st.balloons()

with tab2:
    st.subheader("🏭 จัดการโรงงานปลายทาง")
    if "factory_list" not in st.session_state:
        st.session_state.factory_list = [{"id": 1, "name": "โรงงาน A", "code": "A"}, {"id": 2, "name": "โรงงาน B", "code": "B"}]

    df = pd.DataFrame(st.session_state.factory_list)
    st.dataframe(df[["id", "name", "code"]], use_container_width=True, hide_index=True)

    with st.expander("➕ เพิ่ม / แก้ไข โรงงาน"):
        col1, col2 = st.columns(2)
        with col1:
            factory_name = st.text_input("ชื่อโรงงาน")
        with col2:
            factory_code = st.text_input("รหัสย่อ")
        edit_id = st.number_input("ID (0=เพิ่มใหม่)", min_value=0, step=1)
        if st.button("บันทึกโรงงาน"):
            if edit_id == 0:
                new_id = max([f["id"] for f in st.session_state.factory_list], default=0) + 1
                st.session_state.factory_list.append({"id": new_id, "name": factory_name, "code": factory_code})
                st.success(f"เพิ่มโรงงาน {factory_name} แล้ว")
            else:
                for f in st.session_state.factory_list:
                    if f["id"] == edit_id:
                        f["name"] = factory_name
                        f["code"] = factory_code
                        break
                st.success("อัปเดตข้อมูลแล้ว")
            st.rerun()

    delete_id = st.selectbox("เลือก ID โรงงานที่ต้องการลบ", [f["id"] for f in st.session_state.factory_list])
    if st.button("ลบโรงงาน"):
        st.session_state.factory_list = [f for f in st.session_state.factory_list if f["id"] != delete_id]
        st.success("ลบเรียบร้อย")
        st.rerun()