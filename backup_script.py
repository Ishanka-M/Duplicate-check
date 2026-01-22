import gspread
import os
import json
from google.oauth2.service_account import Credentials
from datetime import datetime

def run_backup():
    try:
        # Secrets වලින් දත්ත ගැනීම
        if 'GCP_JSON' not in os.environ:
            print("❌ Error: GCP_JSON environment variable not found.")
            exit(1)

        info = json.loads(os.environ['GCP_JSON'])
        
        # --- වැදගත්ම කොටස: Scopes නිවැරදිව ලබා දීම ---
        # 403 Error එක විසඳෙන්නේ මෙතැනිනි
        SCOPES = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        client = gspread.authorize(creds)
        
        # Sheet එක සම්බන්ධ කරගැනීම
        print("Connecting to Google Sheets...")
        spreadsheet = client.open('streamlit_DB')
        source_sheet = spreadsheet.worksheet('Sheet1')
        
        data = source_sheet.get_all_values()
        
        if len(data) > 1:
            # අද දිනයට නමක්
            today_str = datetime.now().strftime('%Y-%m-%d_%H-%M')
            backup_sheet_name = f'Backup_{today_str}'
            
            print(f'Creating backup sheet: {backup_sheet_name}...')
            
            # Backup එක සෑදීම
            backup_sheet = spreadsheet.add_worksheet(title=backup_sheet_name, rows=len(data)+10, cols=len(data[0])+5)
            backup_sheet.update(data)
            
            # Clear කිරීම
            header = data[0]
            source_sheet.clear()
            source_sheet.append_row(header)
            
            print('✅ SUCCESS: Backup created and Sheet1 cleared.')
        else:
            print('ℹ️ INFO: No data found to backup.')

    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        exit(1)

if __name__ == "__main__":
    run_backup()
