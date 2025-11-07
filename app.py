import streamlit as st
import cv2
import pytesseract
import numpy as np
import tempfile
import os
from PIL import Image

# ======== CONFIGURE TESSERACT OCR ========
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
os.environ['TESSDATA_PREFIX'] = r"C:\Program Files\Tesseract-OCR\tessdata"

# ======== STREAMLIT PAGE CONFIG ========
st.set_page_config(page_title="License Plate Detection", page_icon="🚗", layout="centered")

st.title("🚗 License Plate Recognition using OpenCV + Tesseract")
st.markdown("Upload a **vehicle image**, and the app will detect and extract the **license plate number** using OCR.")

# ======== FILE UPLOAD ========
uploaded_file = st.file_uploader("📤 Upload an image (jpg, jpeg, png)", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # Save uploaded image temporarily
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(uploaded_file.read())
        image_path = temp_file.name

    # ======== LOAD IMAGE ========
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 11, 17, 17)
    edges = cv2.Canny(gray, 30, 200)

    # ======== FIND CONTOURS ========
    contours, _ = cv2.findContours(edges.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

    plate_contour = None
    for contour in contours:
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.018 * peri, True)
        if len(approx) == 4:
            plate_contour = approx
            break

    if plate_contour is None:
        st.error("❌ License plate not detected. Try uploading a clearer image.")
    else:
        # ======== MASK AND CROP LICENSE PLATE ========
        mask = np.zeros(gray.shape, np.uint8)
        cv2.drawContours(mask, [plate_contour], 0, 255, -1)
        new_img = cv2.bitwise_and(img, img, mask=mask)

        (x, y) = np.where(mask == 255)
        (topx, topy) = (np.min(x), np.min(y))
        (bottomx, bottomy) = (np.max(x), np.max(y))
        cropped = gray[topx:bottomx+1, topy:bottomy+1]

        # ======== OCR TEXT EXTRACTION ========
        text = pytesseract.image_to_string(cropped, lang='eng', config='--psm 8').strip()

        # ======== DISPLAY RESULTS ========
        st.subheader("📸 Original Image")
        st.image(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), use_column_width=True)

        st.subheader("🔍 Detected License Plate")
        st.image(cropped, caption="Cropped License Plate", use_column_width=False)

        if text:
            st.success(f"🧾 **Detected Plate Number:** `{text}`")
        else:
            st.warning("⚠️ No text detected from the plate. Try another image.")

        # ======== SAVE CROPPED IMAGE ========
        os.makedirs("output", exist_ok=True)
        output_path = os.path.join("output", "detected_plate.jpg")
        cv2.imwrite(output_path, cropped)
        st.download_button(
            label="📥 Download Detected Plate Image",
            data=open(output_path, "rb").read(),
            file_name="detected_plate.jpg",
            mime="image/jpeg"
        )

        # Clean up temporary file
        os.remove(image_path)
