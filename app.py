import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# Google Sheet එකට සම්බන්ධ වීම
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds_dict = st.secrets["gcp_service_account"]
creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)

# ඔයාගේ Sheet එකේ නම මෙතන දාන්න
SHEET_NAME = "Your_Google_Sheet_Name"
sheet = client.open(SHEET_NAME).sheet1

st.title("📦 Picking Verification System")

uploaded_file = st.file_uploader("Excel file එක upload කරන්න", type=["xlsx"])

if uploaded_file:
    new_data = pd.read_excel(uploaded_file)
    # දැනට Sheet එකේ ඇති දත්ත ලබාගැනීම
    existing_data = pd.DataFrame(sheet.get_all_records())

    duplicates = []
    if not existing_data.empty:
        # Pallet header එකෙන් duplicate පරීක්ෂාව
        duplicates = existing_data[existing_data['Pallet'].isin(new_data['Pallet'])]

    if len(duplicates) > 0:
        st.warning("⚠️ Duplicate Pallets හමු වුණා!")
        # අවශ්‍ය Headers පමණක් පෙන්වීම
        st.write(duplicates[['Pallet', 'Actual Qty', 'Uom', 'Load Id']])
        st.info("ඔබට මෙම දත්ත ඇතුළත් කිරීමට අවශ්‍යද?")

        col1, col2 = st.columns(2)
        if col1.button("Yes"):
            sheet.append_rows(new_data.values.tolist())
            st.success("දත්ත සාර්ථකව Save කළා!")
        
        if col2.button("No"):
            st.error("දත්ත Save කළේ නැත.")
            
    else:
        # Duplicate නැතිනම් කෙලින්ම save කිරීම
        if st.button("Save Data"):
            sheet.append_rows(new_data.values.tolist())
            st.success("අලුත් දත්ත සාර්ථකව ඇතුළත් කළා!")
