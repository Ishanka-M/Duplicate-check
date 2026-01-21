import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import io
import time

# --- PAGE CONFIG ---
st.set_page_config(page_title="Picking Verification System", page_icon="📦", layout="wide")

# --- HELPER FUNCTION: CONVERT DF TO EXCEL ---
# DataFrame එක Excel file එකක් බවට පත් කරන function එක
def to_excel(df):
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Sheet1')
    writer.close()
    processed_data = output.getvalue()
    return processed_data

# --- GOOGLE SHEETS CONNECTION ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# Spinner එකක් දාමු connect වෙන අතරතුර
with st.spinner('Connecting to Google Sheets...'):
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        # Sheet එක සහ Worksheet එක තෝරාගැනීම
        spreadsheet = client.open("streamlit_DB")
        sheet = spreadsheet.worksheet("Sheet1")
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        st.stop()

# --- UI HEADER ---
st.title("📦 Picking Verification System")
st.markdown("Verification Portal")
st.markdown("---")

# --- FILE UPLOADER ---
uploaded_file = st.file_uploader("Excel file එක මෙතනට Upload කරන්න", type=["xlsx", "xls"], help="Drag and drop your daily picking excel file here.")

if uploaded_file:
    # Upload කරන අතරතුර animation එකක්
    with st.spinner('Processing File... 🔄'):
        time.sleep(1) # පොඩි delay එකක් animation එක පේන්න
        new_df = pd.read_excel(uploaded_file)
        existing_rows = sheet.get_all_records()
        existing_df = pd.DataFrame(existing_rows)

    # පරීක්ෂා කළ යුතු Column එක: 'Pallet'
    if 'Pallet' in new_df.columns:
        
        duplicate_pallets = []
        if not existing_df.empty and 'Pallet' in existing_df.columns:
            duplicate_pallets = existing_df[existing_df['Pallet'].isin(new_df['Pallet'])]

        if len(duplicate_pallets) > 0:
            # --- DUPLICATE FOUND SECTION ---
            st.error("⚠️ Duplicate Pallets හමු වුණා! (Duplicate Pallets Found)")
            st.markdown("පහත දැක්වෙන්නේ දැනටමත් පද්ධතියේ ඇති Pallets වේ.")
            
            display_cols = ['Pallet', 'Actual Qty', 'Uom', 'Load Id']
            available_cols = [col for col in display_cols if col in duplicate_pallets.columns]
            
            # Duplicate Data පෙන්වීම
            st.dataframe(duplicate_pallets[available_cols], use_container_width=True, height=200)

            # --- EXCEL DOWNLOAD BUTTON ---
            # මෙම duplicate දත්ත ටික Excel එකක් ලෙස download කරගැනීමට
            excel_data = to_excel(duplicate_pallets[available_cols])
            st.download_button(
                label="📥 Download Duplicate Data as Excel",
                data=excel_data,
                file_name='duplicate_pallets.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            st.markdown("---")
            st.info("💡 ඔබට මෙම අලුත් දත්ත ඇතුළත් කිරීමට (Save) අවශ්‍යද?")
            
            col1, col2 = st.columns([0.2, 0.8])
            with col1:
                if st.button("✅ Yes, Save Data", type="primary"):
                    with st.spinner('Saving data...'):
                        sheet.append_rows(new_df.astype(str).values.tolist())
                    st.balloons() # Success animation
                    st.success("දත්ත සාර්ථකව Save කළා!")
            with col2:
                if st.button("❌ No, Cancel"):
                    st.warning("දත්ත Save කිරීම අවලංගු කළා.")
        
        else:
            # --- NO DUPLICATES SECTION ---
            st.success("✅ No Duplicates Found. Ready to save.")
            if st.button("Save Data Now", type="primary"):
                 with st.spinner('Saving data...'):
                    sheet.append_rows(new_df.astype(str).values.tolist())
                 st.balloons() # Success animation
                 st.success("අලුත් දත්ත සාර්ථකව ඇතුළත් කළා!")
    else:
        st.error("🚫 වැරදි File Format එකක්! කරුණාකර 'Pallet' header එක සහිත file එකක් ලබාදෙන්න.")

# --- FOOTER ---
st.markdown("---")
# යටින්ම පෙන්වන නම dark theme එකට ගැලපෙන ලෙස
st.markdown("""
    <style>
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #222831;
        color: #888888;
        text-align: center;
        padding: 10px;
        font-size: 12px;
    }
    </style>
    <div class="footer">
        Developed by Ishanka Madusanka | 2026
    </div>
    """, unsafe_allow_html=True)
