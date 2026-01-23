import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import io
import time
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="EFL Picking Verification", page_icon="📦", layout="wide")

# --- CUSTOM CSS FOR BETTER UI ---
st.markdown("""
    <style>
    .stDataFrame { border: 1px solid #393e46; border-radius: 10px; }
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; background-color: #222831; color: #888888; text-align: center; padding: 10px; font-size: 12px; z-index: 100; }
    .metric-card { background-color: #1e2129; padding: 15px; border-radius: 10px; text-align: center; }
    .stButton button { width: 100%; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- GOOGLE SHEETS CONNECTION ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

@st.cache_resource
def get_gspread_client():
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(creds)

try:
    client = get_gspread_client()
    spreadsheet = client.open("streamlit_DB")
    sheet = spreadsheet.worksheet("Sheet1")
except Exception as e:
    st.error(f"Error connecting to Google Sheets: {e}")
    st.stop()

# --- HELPER FUNCTION: DOWNLOAD TO EXCEL ---
def to_excel(df):
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Sheet1')
    writer.close()
    return output.getvalue()

# --- SIDEBAR NAVIGATION ---
st.sidebar.image("efl_logo.png", use_container_width=True)
st.sidebar.markdown("---")
# Navigation එකට "⚙️ Admin Panel" එකතු කළා
page = st.sidebar.radio("Navigation", ["📤 Upload Data", "🔍 Search & History", "🗑️ Manage Records", "⚙️ Admin Panel"])

# --- MAIN HEADER ---
col_logo, col_title = st.columns([0.15, 0.85])
with col_logo:
    st.image("efl_logo.png", width=100)
with col_title:
    st.title("Picking Verification System")
    st.write("EFL Logistics | Verification Portal")
st.markdown("---")

# --- PAGE 1: UPLOAD DATA ---
if page == "📤 Upload Data":
    uploaded_file = st.file_uploader("Daily Excel File එක මෙතනට දාන්න", type=["xlsx", "xls"])
    
    if uploaded_file:
        with st.spinner('Processing file...'):
            new_df = pd.read_excel(uploaded_file)
            existing_data = sheet.get_all_records()
            existing_df = pd.DataFrame(existing_data)

        if 'Pallet' in new_df.columns:
            duplicates = new_df[new_df['Pallet'].isin(existing_df['Pallet'])] if not existing_df.empty else pd.DataFrame()

            if not duplicates.empty:
                st.error(f"⚠️ Duplicate Pallets {len(duplicates)} ක් හමු වුණා!")
                st.dataframe(duplicates[['Pallet', 'Actual Qty', 'Load Id']], use_container_width=True)
                
                col_up1, col_up2 = st.columns(2)
                with col_up1:
                    if st.button("✅ Yes, Save Everything", type="primary"):
                        sheet.append_rows(new_df.astype(str).values.tolist())
                        st.balloons(); st.success("දත්ත ඇතුළත් කළා!")
                with col_up2:
                    st.download_button("📥 Download Duplicates", data=to_excel(duplicates), file_name="duplicates.xlsx")
            else:
                st.success("✅ No duplicates found.")
                if st.button("Save Data Now", type="primary"):
                    sheet.append_rows(new_df.astype(str).values.tolist())
                    st.balloons(); st.success("දත්ත ඇතුළත් කළා!")
        else:
            st.error("වැරදි Format එකක්! 'Pallet' column එක පරීක්ෂා කරන්න.")

# --- PAGE 2: SEARCH & HISTORY ---
elif page == "🔍 Search & History":
    st.subheader("🔍 Search & Day Summary")
    
    with st.spinner('Loading data from Google Sheets...'):
        all_data = pd.DataFrame(sheet.get_all_records())

    if not all_data.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Pallets", len(all_data))
        c2.metric("Total Actual Qty", int(all_data['Actual Qty'].sum()))
        c3.metric("Unique Load IDs", all_data['Load Id'].nunique())

        st.markdown("---")
        search_query = st.text_input("Pallet ID, Load ID හෝ ඕනෑම විස්තරයක් ඇතුළත් කර සොයන්න...")

        if search_query:
            filtered_df = all_data[all_data.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)]
            st.write(f"ප්‍රතිඵල: {len(filtered_df)}")
            st.dataframe(filtered_df, use_container_width=True)
        else:
            st.write("අද දවසේ පද්ධතියට ඇතුළත් කළ සියලුම දත්ත:")
            st.dataframe(all_data, use_container_width=True)

        download_df = filtered_df if search_query else all_data
        st.download_button("📥 Download Current View as Excel", data=to_excel(download_df), file_name="picking_report.xlsx")
    else:
        st.info("පද්ධතියේ තවමත් දත්ත කිසිවක් නැත.")

# --- PAGE 3: MANAGE RECORDS ---
elif page == "🗑️ Manage Records":
    st.subheader("🗑️ Delete Records")
    all_data = pd.DataFrame(sheet.get_all_records())
    
    if not all_data.empty:
        target_pallet = st.selectbox("මකා දැමිය යුතු Pallet ID එක තෝරන්න", ["-- Select --"] + all_data['Pallet'].astype(str).tolist())
        
        if target_pallet != "-- Select --":
            row_to_delete = all_data[all_data['Pallet'].astype(str) == target_pallet]
            st.table(row_to_delete)
            
            if st.button("🚨 Delete Permanently", type="secondary"):
                with st.spinner('Deleting...'):
                    cell = sheet.find(str(target_pallet))
                    sheet.delete_rows(cell.row)
                    st.success(f"Pallet {target_pallet} සාර්ථකව ඉවත් කළා!")
                    time.sleep(1)
                    st.rerun()
    else:
        st.info("මකා දැමීමට දත්ත නැත.")

# --- NEW PAGE: ADMIN PANEL (MANUAL BACKUP & CLEAR) ---
elif page == "⚙️ Admin Panel":
    st.subheader("⚙️ System Maintenance & Backup")
    st.markdown("GitHub Auto-Backup එක සිදු නොවී ඇත්නම් පමණක් මෙය භාවිතා කරන්න.")
    
    all_vals = sheet.get_all_values()
    
    if len(all_vals) > 1:
        st.info(f"දැනට පද්ධතියේ Rows **{len(all_vals)-1}** ක් පවතී.")
        
        st.warning("⚠️ මෙහිදී දැනට පවතින සියලුම දත්ත අලුත් Sheet එකකට Backup වී Main Sheet එක Clear කරනු ලැබේ.")
        
        # වැරදීමකින් button එක එබීම වැළැක්වීමට check box එකක්
        confirm_check = st.checkbox("දත්ත Backup කර Clear කිරීමට මම එකඟ වෙමි.")
        
        if st.button("🚀 Run Manual Backup & Clear Now", type="primary"):
            if confirm_check:
                try:
                    with st.spinner('පද්ධතිය Backup කරමින් පවතී...'):
                        # 1. Backup නම සෑදීම
                        now_str = datetime.now().strftime('%Y-%m-%d_%H-%M')
                        backup_name = f"Manual_Backup_{now_str}"
                        
                        # 2. අලුත් worksheet එකක් සාදා දත්ත copy කිරීම
                        new_ws = spreadsheet.add_worksheet(title=backup_name, rows=len(all_vals)+10, cols=len(all_vals[0])+5)
                        new_ws.update(all_vals)
                        
                        # 3. ප්‍රධාන sheet එකේ දත්ත මැකීම (Header එක තබාගෙන)
                        header = all_vals[0]
                        sheet.clear()
                        sheet.append_row(header)
                        
                        st.balloons()
                        st.success(f"සාර්ථකයි! '{backup_name}' නමින් දත්ත සුරැකි අතර පද්ධතිය Reset කරන ලදී.")
                        time.sleep(2)
                        st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.error("කරුණාකර ඉහත Checkbox එක මත ක්ලික් කර තහවුරු කරන්න.")
    else:
        st.info("Backup කිරීමට හෝ Clear කිරීමට දත්ත පද්ධතියේ නැත.")

# --- FOOTER ---
st.markdown(f'<div class="footer">Developed by Ishanka Madusanka | 2026</div>', unsafe_allow_html=True)
