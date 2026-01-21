import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- PAGE CONFIG ---
st.set_page_config(page_title="Picking Verification System", layout="wide")

# --- GOOGLE SHEETS CONNECTION ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

try:
    # Secrets වලින් credentials ලබා ගැනීම
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)

    # Sheet එක සම්බන්ධ කරගැනීම (නම: streamlit_DB, Worksheet: Sheet1)
    sheet = client.open("streamlit_DB").worksheet("Sheet1")
except Exception as e:
    st.error(f"Error connecting to Google Sheets: {e}")
    st.stop()

# --- UI HEADER ---
st.title("📦 Picking Verification System")
st.markdown("---")

# --- FILE UPLOADER ---
uploaded_file = st.file_uploader("Excel file එක මෙතනට Upload කරන්න", type=["xlsx", "xls"])

if uploaded_file:
    # Upload කළ file එක කියවීම
    new_df = pd.read_excel(uploaded_file)
    
    # දැනට Sheet එකේ ඇති data ලබා ගැනීම
    existing_rows = sheet.get_all_records()
    existing_df = pd.DataFrame(existing_rows)

    # පරීක්ෂා කළ යුතු Column එක: 'Pallet'
    if 'Pallet' in new_df.columns:
        
        # Duplicate තිබේදැයි පරීක්ෂා කිරීම
        duplicate_pallets = []
        if not existing_df.empty and 'Pallet' in existing_df.columns:
            duplicate_pallets = existing_df[existing_df['Pallet'].isin(new_df['Pallet'])]

        if len(duplicate_pallets) > 0:
            # Duplicate හමු වූ විට පණිවිඩය පෙන්වීම
            st.warning("⚠️ Duplicate Pallet එකක් හමු වුණා!")
            
            # අවශ්‍ය Headers පමණක් පෙන්වීම: Pallet, Actual Qty, Uom, Load Id
            display_cols = ['Pallet', 'Actual Qty', 'Uom', 'Load Id']
            # එම columns Sheet එකේ තිබේදැයි තහවුරු කර පෙන්වීම
            available_cols = [col for col in display_cols if col in duplicate_pallets.columns]
            st.write("කලින් ඇතුළත් කළ දත්ත:")
            st.dataframe(duplicate_pallets[available_cols], use_container_width=True)
            
            st.info("ඔබට මෙම අලුත් දත්ත ඇතුළත් කිරීමට (Save) අවශ්‍යද?")
            
            # Yes/No Buttons
            col1, col2 = st.columns([0.1, 0.1])
            with col1:
                if st.button("Yes", key="btn_yes"):
                    sheet.append_rows(new_df.astype(str).values.tolist())
                    st.success("✅ දත්ත සාර්ථකව Save කළා!")
            with col2:
                if st.button("No", key="btn_no"):
                    st.error("❌ දත්ත Save කළේ නැත.")
        
        else:
            # Duplicate නැතිනම් කෙලින්ම Save කිරීම
            if st.button("Save Data"):
                sheet.append_rows(new_df.astype(str).values.tolist())
                st.success("✅ අලුත් දත්ත සාර්ථකව ඇතුළත් කළා!")
    else:
        st.error("වැරදි File එකක්! කරුණාකර 'Pallet' header එක සහිත file එකක් ලබාදෙන්න.")

# --- FOOTER ---
st.markdown("---")
st.caption("Developed by Ishanka Madusanka")
