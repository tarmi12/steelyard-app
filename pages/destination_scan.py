import streamlit as st
import pandas as pd
from datetime import datetime

if "destination_scans" not in st.session_state:
    st.session_state.destination_scans = [
        {"id": 1, "weigh_out_id": "WO0001", "truck_plate": "80-1234", "scan_method": "LINE", "timestamp": datetime(2026, 5, 27, 14, 35), "image_url": "https://drive.google.com/uc?export=view&id=1abc123", "remark": ""},
        {"id": 2, "weigh_out_id": "WO0002", "truck_plate": "80-5678", "scan_method": "Manual", "timestamp": datetime(2026, 5, 27, 16, 10), "image_url": "", "remark": "รูปไม่ชัด"}
    ]

st.header("📸 หลักฐานปลายทาง (Destination Evidence)")

with st.expander("➕ อัปโหลดหลักฐานด้วยตนเอง (Manual)"):
    with st.form("manual_upload"):
        wo_id = st.text_input("เลขที่ชั่งออก (Weigh Out ID)")
        truck = st.text_input("ทะเบียนรถ")
        uploaded_file = st.file_uploader("รูปใบชั่งปลายทาง", type=["jpg", "png", "jpeg"])
        remark_manual = st.text_input("หมายเหตุ")
        submitted = st.form_submit_button("อัปโหลด")
        if submitted and uploaded_file and wo_id:
            new_id = max([r["id"] for r in st.session_state.destination_scans], default=0) + 1
            st.session_state.destination_scans.append({
                "id": new_id,
                "weigh_out_id": wo_id,
                "truck_plate": truck,
                "scan_method": "Manual",
                "timestamp": datetime.now(),
                "image_url": "",
                "remark": remark_manual
            })
            st.success("อัปโหลดหลักฐานเรียบร้อย (บันทึกชั่วคราว)")
            st.rerun()

st.subheader("📋 ประวัติการสแกนหลักฐาน")

col1, col2 = st.columns(2)
with col1:
    filter_wo = st.text_input("ค้นหาจากเลขที่ชั่งออก", "")
with col2:
    filter_date = st.date_input("วันที่", value=None)

scans = st.session_state.destination_scans
if filter_wo:
    scans = [s for s in scans if filter_wo.lower() in s["weigh_out_id"].lower()]
if filter_date:
    scans = [s for s in scans if s["timestamp"].date() == filter_date]

if not scans:
    st.info("ไม่มีข้อมูลในช่วงนี้")
else:
    selected_row_index = st.selectbox(
        "เลือกแถวเพื่อดูรายละเอียด",
        range(len(scans)),
        format_func=lambda i: f"{scans[i]['weigh_out_id']} - {scans[i]['truck_plate']} ({scans[i]['timestamp'].strftime('%d/%m/%Y %H:%M')})"
    )
    selected_scan = scans[selected_row_index]

    colA, colB, colC = st.columns(3)
    colA.metric("เลขที่ชั่งออก", selected_scan["weigh_out_id"])
    colB.metric("ทะเบียนรถ", selected_scan["truck_plate"])
    colC.metric("เวลา", selected_scan["timestamp"].strftime("%d/%m/%Y %H:%M:%S"))
    st.write(f"**วิธีส่ง:** {selected_scan['scan_method']}")
    if selected_scan["remark"]:
        st.write(f"**หมายเหตุ:** {selected_scan['remark']}")
    if selected_scan["image_url"]:
        st.image(selected_scan["image_url"], caption="หลักฐานปลายทาง", use_container_width=True)
        st.markdown(f"[🔗 เปิดรูปใน Google Drive]({selected_scan['image_url']})")
    else:
        st.warning("ยังไม่มีไฟล์รูป")

    st.markdown("---")
    df = pd.DataFrame([{
        "เลขที่ชั่งออก": s["weigh_out_id"],
        "ทะเบียน": s["truck_plate"],
        "วันที่/เวลา": s["timestamp"].strftime("%Y-%m-%d %H:%M"),
        "วิธีส่ง": s["scan_method"],
        "หมายเหตุ": s["remark"],
        "รูป": "📷" if s["image_url"] else "❌"
    } for s in scans])
    st.dataframe(df, use_container_width=True, hide_index=True)

total_scans = len(st.session_state.destination_scans)
line_scans = len([s for s in st.session_state.destination_scans if s["scan_method"] == "LINE"])
manual_scans = total_scans - line_scans
st.write(f"📊 **สถิติ:** รับหลักฐานทั้งหมด {total_scans} ครั้ง (ผ่าน LINE {line_scans} / Manual {manual_scans})")