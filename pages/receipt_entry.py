import streamlit as st
from datetime import date

st.header("💵 ตรวจสอบและบันทึกเงินโอน")

# จำลองรายการ Sales Clearing ที่รอรับเงิน (ภายหลังดึงจาก Supabase)
demo_data = [
    {"เลขที่บิล": "SC0001", "วันที่เคลียร์": "2026-05-27", "ปลายทาง": "โรงงาน A", "ยอดเงิน": 85000.00, "สถานะ": "ยังไม่ได้รับ"},
    {"เลขที่บิล": "SC0002", "วันที่เคลียร์": "2026-05-28", "ปลายทาง": "โรงงาน B", "ยอดเงิน": 72000.00, "สถานะ": "ยังไม่ได้รับ"},
]

st.subheader("รายการที่รอรับเงิน")
st.dataframe(demo_data, use_container_width=True)

st.markdown("---")
st.subheader("บันทึกการรับเงิน")

# เลือกบิลที่จะรับเงิน
selected_bills = st.multiselect("เลือกรายการที่ได้รับเงินแล้ว", [d["เลขที่บิล"] for d in demo_data])

if selected_bills:
    total_amount = sum([d["ยอดเงิน"] for d in demo_data if d["เลขที่บิล"] in selected_bills])
    st.write(f"ยอดรวมที่รับ: **{total_amount:,.2f} บาท**")

    receipt_date = st.date_input("วันที่รับเงิน", date.today())
    bank_ref = st.text_input("เลขที่อ้างอิง / หมายเหตุการโอน")
    receipt_image = st.file_uploader("แนบสลิปโอน (ถ้ามี)", type=["jpg", "png"])

    if st.button("✅ ยืนยันการรับเงิน"):
        # TODO: อัปเดต receipts, เปลี่ยนสถานะใน sales_clearing
        st.success(f"บันทึกรับเงิน {len(selected_bills)} รายการ รวม {total_amount:,.2f} บาท เรียบร้อย!")
        # สามารถพิมพ์สรุปการรับเงินได้ (ฟังก์ชันพิมพ์)
else:
    st.info("เลือกรายการด้านบนเพื่อบันทึกการรับเงิน")

if st.button("🖨️ พิมพ์สรุปการรับเงิน"):
    st.write("พิมพ์เอกสารสรุปการรับเงินแล้ว (จำลอง)")