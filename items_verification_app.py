# -*- coding: utf-8 -*-
"""
Items Verification Web App
Mobile-friendly Streamlit app for verifying equipment items
Supports Google Sheets for cloud deployment
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# Page configuration - must be first Streamlit command
st.set_page_config(
    page_title="אימות ציוד",
    page_icon="✅",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for compact mobile-friendly Hebrew RTL interface
st.markdown("""
<style>
    /* RTL support for Hebrew */
    .stApp {
        direction: rtl;
    }
    
    /* Compact radio buttons */
    .stRadio > div {
        flex-direction: row !important;
        gap: 5px !important;
    }
    
    .stRadio label {
        padding: 2px 8px !important;
        font-size: 12px !important;
    }
    
    /* Reduce spacing between elements */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
    
    div[data-testid="stVerticalBlock"] > div {
        gap: 0.2rem !important;
    }
    
    /* Success/Error messages styling */
    .success-box {
        background-color: #d4edda;
        border: 2px solid #28a745;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        margin: 10px 0;
    }
    
    .error-box {
        background-color: #f8d7da;
        border: 2px solid #dc3545;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        margin: 10px 0;
    }
    
    /* Header styling */
    h1 {
        text-align: center;
        font-size: 1.5rem !important;
        margin-bottom: 0.5rem !important;
    }
    
    h3 {
        font-size: 1rem !important;
        margin: 0.5rem 0 !important;
    }
    
    /* Compact buttons */
    .stButton > button {
        height: 45px;
        font-size: 16px !important;
        padding: 5px 10px !important;
    }

    hr {
        margin: 0.5rem 0 !important;
    }

    /* Table-like alternating rows */
    .row-gray {
        background-color: #e9e9e9;
        padding: 6px 10px;
        border-bottom: 1px solid #ccc;
    }
    
    .row-white {
        background-color: #ffffff;
        padding: 6px 10px;
        border-bottom: 1px solid #ccc;
    }
    
    /* Table header */
    .table-header {
        background-color: #4a6fa5;
        color: white;
        padding: 8px 10px;
        font-weight: bold;
        font-size: 14px;
        border-radius: 6px 6px 0 0;
    }
    
    /* Table wrapper */
    .table-wrapper {
        border: 1px solid #ccc;
        border-radius: 6px;
        overflow: hidden;
        margin: 8px 0;
    }
</style>
""", unsafe_allow_html=True)

# Google Sheets configuration
# Use the native Google Sheets URL format (create a new Google Sheet, don't upload Excel)
SPREADSHEET_ID = "1XRIXqax3atq5_ZrgoHZ0ZHkyZVp7VfPHOP9P9at7XMc"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Fallback local file path
DATA_FILE = Path(__file__).parent / "RSP6551.xlsx"

# Item columns to track (excluding metadata columns)
METADATA_COLS = ['תא אחסון', 'צוות', 'שם', 'Unnamed: 26', 'זיכוי']

# Status options
STATUS_OPTIONS = ["אין", "יש", "תרומה"]
STATUS_MAP = {"אין": None, "יש": 1, "תרומה": "ת"}
REVERSE_STATUS_MAP = {None: "אין", 1: "יש", 1.0: "יש", "1": "יש", "ת": "תרומה"}


def get_google_sheets_client():
    """Get authenticated Google Sheets client"""
    try:
        # Try to get credentials from Streamlit secrets (for cloud deployment)
        if hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
            creds = Credentials.from_service_account_info(
                st.secrets["gcp_service_account"],
                scopes=SCOPES
            )
            return gspread.authorize(creds)
        
        # Try local service account file
        service_account_file = Path(__file__).parent / "service_account.json"
        if service_account_file.exists():
            creds = Credentials.from_service_account_file(
                str(service_account_file),
                scopes=SCOPES
            )
            return gspread.authorize(creds)
        
        return None
    except Exception as e:
        st.warning(f"Google Sheets לא זמין: {e}")
        return None


def load_data():
    """Load data from Google Sheets or local Excel file"""
    # Try Google Sheets first
    client = get_google_sheets_client()
    if client:
        try:
            spreadsheet = client.open_by_key(SPREADSHEET_ID)
            worksheet = spreadsheet.sheet1
            data = worksheet.get_all_records()
            df = pd.DataFrame(data)
            st.session_state.use_google_sheets = True
            st.session_state.gs_client = client
            return df
        except Exception as e:
            st.warning(f"שגיאה בטעינה מ-Google Sheets: {e}")
    
    # Fallback to local Excel
    try:
        df = pd.read_excel(DATA_FILE)
        st.session_state.use_google_sheets = False
        return df
    except Exception as e:
        st.error(f"שגיאה בטעינת הקובץ: {e}")
        return None


def get_all_items(df):
    """Get all item columns"""
    return [col for col in df.columns if col not in METADATA_COLS]


def get_person_item_status(df, name, item):
    """Get item status for a person: None, 1, or 'ת'"""
    person_row = df[df['שם'] == name]
    if person_row.empty:
        return None
    
    val = person_row.iloc[0][item]
    
    if pd.isna(val) or val == '' or val == 0:
        return None
    if val == 1 or val == 1.0 or str(val) == '1':
        return 1
    if str(val) == 'ת':
        return "ת"
    return None


def get_person_info(df, name):
    """Get person metadata"""
    person_row = df[df['שם'] == name]
    if person_row.empty:
        return {}
    
    row = person_row.iloc[0]
    return {
        'תא אחסון': row.get('תא אחסון', ''),
        'צוות': row.get('צוות', '')
    }


def ensure_backup_exists(client, spreadsheet):
    """Create a backup sheet if it doesn't exist (one-time only)"""
    try:
        sheet_names = [ws.title for ws in spreadsheet.worksheets()]
        if "גיבוי_מקורי" not in sheet_names:
            original_sheet = spreadsheet.sheet1
            backup_sheet = spreadsheet.add_worksheet(
                title="גיבוי_מקורי",
                rows=original_sheet.row_count,
                cols=original_sheet.col_count
            )
            all_data = original_sheet.get_all_values()
            if all_data:
                backup_sheet.update('A1', all_data)
    except Exception as e:
        st.warning(f"לא ניתן ליצור גיבוי: {e}")


def save_verification(df, name, item_statuses, notes=""):
    """Save verification - update main sheet directly, backup created once"""
    # Find person's row index
    person_idx = df[df['שם'] == name].index
    if len(person_idx) == 0:
        return None
    
    idx = person_idx[0]
    
    # Update the dataframe with new values
    for item, status in item_statuses.items():
        df.at[idx, item] = status if status is not None else ""
    
    # Add notes if provided
    if notes:
        if 'הערות' not in df.columns:
            df['הערות'] = ""
        df.at[idx, 'הערות'] = notes
    
    # Try to save to Google Sheets
    if st.session_state.get('use_google_sheets') and st.session_state.get('gs_client'):
        try:
            client = st.session_state.gs_client
            spreadsheet = client.open_by_key(SPREADSHEET_ID)
            
            # Create backup of original data (only first time)
            ensure_backup_exists(client, spreadsheet)
            
            # Update the main sheet directly
            main_sheet = spreadsheet.sheet1
            header = df.columns.tolist()
            values = [header] + df.fillna("").values.tolist()
            main_sheet.clear()
            main_sheet.update('A1', values)
            
            return "הגיליון הראשי"
        except Exception as e:
            st.warning(f"שגיאה בשמירה ל-Google Sheets: {e}")
    
    # Fallback to local Excel - update in place with one-time backup
    backup_file = DATA_FILE.parent / f"גיבוי_מקורי_{DATA_FILE.name}"
    if not backup_file.exists():
        import shutil
        shutil.copy(DATA_FILE, backup_file)
    
    df.to_excel(DATA_FILE, index=False)
    return DATA_FILE.name


def main():
    st.title("אימות ציוד")
    
    # Load data
    df = load_data()
    if df is None:
        st.error("לא ניתן לטעון את קובץ הנתונים")
        return
    
    # Show data source indicator
    if st.session_state.get('use_google_sheets'):
        st.caption("📊 מחובר ל-Google Sheets")
    
    # Get list of names and all items
    names = df['שם'].dropna().unique().tolist()
    names.sort()
    all_items = get_all_items(df)
    
    # Initialize session state
    if 'selected_name' not in st.session_state:
        st.session_state.selected_name = None
    if 'initialized' not in st.session_state:
        st.session_state.initialized = False
    
    # Name selection
    selected_name = st.selectbox("בחר את שמך:", options=[""] + names, index=0)
    
    if selected_name:
        # Reset and initialize if name changed
        if st.session_state.selected_name != selected_name:
            st.session_state.selected_name = selected_name
            st.session_state.initialized = False
            # Clear all item states
            for item in all_items:
                if f"item_{item}" in st.session_state:
                    del st.session_state[f"item_{item}"]
        
        # Show person info
        person_info = get_person_info(df, selected_name)
        st.caption(f"👤 {selected_name} | צוות: {person_info.get('צוות', '-')} | תא: {person_info.get('תא אחסון', '-')}")
        
        st.markdown("---")
        
        # Count items with status
        items_with_status = sum(1 for item in all_items if get_person_item_status(df, selected_name, item) is not None)
        st.markdown(f"**רשימת ציוד** ({items_with_status} פריטים רשומים)")
        
        # Display items
        item_statuses = {}
        has_count = 0
        donation_count = 0
        missing_required = []
        
        # Table header
        st.markdown('<div class="table-wrapper">', unsafe_allow_html=True)
        st.markdown('<div class="table-header">פריט &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; סטטוס</div>', unsafe_allow_html=True)
        
        for i, item in enumerate(all_items):
            original_status = get_person_item_status(df, selected_name, item)
            original_display = REVERSE_STATUS_MAP.get(original_status, "אין")
            
            # Set default value on first load
            key = f"item_{item}"
            if not st.session_state.initialized:
                default_idx = STATUS_OPTIONS.index(original_display)
            else:
                default_idx = STATUS_OPTIONS.index(st.session_state.get(key, original_display))
            
            # Alternating row color
            row_class = "row-gray" if i % 2 == 0 else "row-white"
            st.markdown(f'<div class="{row_class}">', unsafe_allow_html=True)
            
            col1, col2 = st.columns([2, 3])
            with col1:
                st.markdown(f"**{item}**")
            
            with col2:
                selected = st.radio(
                    f"status_{item}",
                    options=STATUS_OPTIONS,
                    index=default_idx,
                    key=key,
                    horizontal=True,
                    label_visibility="collapsed"
                )
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Track status
            item_statuses[item] = STATUS_MAP[selected]
            
            if selected == "יש":
                has_count += 1
            elif selected == "תרומה":
                donation_count += 1
            
            # Check if originally had item but now missing
            if original_status is not None and selected == "אין":
                missing_required.append(item)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.session_state.initialized = True
        
        st.markdown("---")
        
        # Summary
        total_have = has_count + donation_count
        st.caption(f"סה\"כ: {total_have} פריטים ({has_count} רגיל + {donation_count} תרומה)")
        
        # Notes field
        notes = st.text_area("הערות (אופציונלי):", height=80, placeholder="הוסף הערות כאן...")
        
        # Buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("אפס", use_container_width=True):
                st.session_state.initialized = False
                st.session_state.selected_name = None
                st.rerun()
        
        with col2:
            verify_clicked = st.button("אמת ושמור", use_container_width=True, type="primary")
        
        # Verification result
        if verify_clicked:
            if not missing_required:
                st.markdown("""
                <div class="success-box">
                    <h3>אימות הושלם!</h3>
                    <p>כל הפריטים הרשומים קיימים</p>
                </div>
                """, unsafe_allow_html=True)
                st.balloons()
            else:
                st.markdown(f"""
                <div class="error-box">
                    <h3>שים לב!</h3>
                    <p>{len(missing_required)} פריטים שהיו רשומים סומנו כחסרים</p>
                </div>
                """, unsafe_allow_html=True)
                st.warning(f"**פריטים חסרים:** {', '.join(missing_required)}")
            
            # Save verification
            result = save_verification(df.copy(), selected_name, item_statuses, notes)
            if result:
                st.success(f"נשמר: {result}")
                st.info(f"אומת: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            else:
                st.error("שגיאה בשמירת הקובץ")
    else:
        st.info("בחר את שמך מהרשימה")


if __name__ == "__main__":
    main()
