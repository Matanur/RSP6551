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
    /* RTL support */
    .stApp {
        direction: rtl;
    }
    
    /* Light modern theme */
    .stApp {
        background-color: #f5f7fa;
        color: #2d3436;
    }
    
    /* Radio buttons - pill style */
    .stRadio > div {
        flex-direction: row !important;
        gap: 6px !important;
    }
    
    .stRadio > div > label {
        padding: 2px 10px !important;
        font-size: 13px !important;
        min-height: 0 !important;
        border-radius: 12px !important;
        border: 1px solid #ccc !important;
        background: #ffffff !important;
        color: #333 !important;
        transition: all 0.2s !important;
    }
    
    .stRadio > div > label[data-checked="true"],
    .stRadio > div > label:has(input:checked) {
        background: #ffffff !important;
        border-color: #2563eb !important;
        color: #2563eb !important;
        font-weight: 700 !important;
    }
    
    .stRadio {
        margin: 0 !important;
        padding: 0 !important;
    }
    
    .stRadio > label {
        font-size: 14px !important;
        font-weight: 600 !important;
        color: #2d3436 !important;
        margin-bottom: 0 !important;
        padding-bottom: 0 !important;
    }
    
    /* Kill ALL vertical gaps */
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
    }
    
    div[data-testid="stVerticalBlock"] > div {
        gap: 0px !important;
        padding-top: 0px !important;
        padding-bottom: 0px !important;
    }
    
    div[data-testid="stVerticalBlockBorderWrapper"] {
        padding: 0 !important;
        gap: 0 !important;
    }
    
    div[data-testid="column"] > div {
        padding: 0 !important;
    }
    
    /* Radio group wrapper - kill spacing */
    div[data-testid="stRadio"] {
        margin-top: -4px !important;
        margin-bottom: -4px !important;
    }
    
    /* Tight text */
    .stMarkdown p {
        margin: 0 !important;
        padding: 0 !important;
    }
    
    .stMarkdown {
        margin: 0 !important;
        padding: 0 !important;
    }
    
    /* Item row stripes */
    .item-row-even {
        background: #ffffff;
        padding: 6px 10px;
        border-bottom: 1px solid #e0e0e0;
        margin: 0;
    }
    
    .item-row-odd {
        background: #f0f2f5;
        padding: 6px 10px;
        border-bottom: 1px solid #e0e0e0;
        margin: 0;
    }

    /* Selectbox */
    div[data-testid="stSelectbox"] {
        margin-bottom: 8px;
    }
    
    /* Success/Error boxes */
    .success-box {
        background: linear-gradient(135deg, #d8f3dc, #b7e4c7);
        border: 2px solid #40916c;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        margin: 10px 0;
        color: #1b4332;
    }
    
    .error-box {
        background: linear-gradient(135deg, #ffd6d6, #ffb3b3);
        border: 2px solid #e5383b;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        margin: 10px 0;
        color: #641220;
    }
    
    /* Header */
    h1 {
        text-align: center;
        font-size: 1.5rem !important;
        margin-bottom: 0.3rem !important;
        color: #2563eb !important;
    }
    
    h3 {
        font-size: 1rem !important;
        margin: 0.3rem 0 !important;
    }
    
    /* Buttons */
    .stButton > button {
        height: 45px;
        font-size: 16px !important;
        padding: 5px 10px !important;
        border-radius: 10px !important;
    }
    
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
        border: none !important;
        color: white !important;
    }

    hr {
        margin: 0.4rem 0 !important;
        border-color: #ddd !important;
    }
    
    /* Caption styling */
    .stCaption, small {
        color: #666 !important;
    }
    
    /* Text area */
    textarea {
        background: #ffffff !important;
        border: 1px solid #ccc !important;
        color: #333 !important;
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
        
        # Tracking variables
        item_statuses = {}
        has_count = 0
        donation_count = 0
        missing_required = []
        
        for i, item in enumerate(all_items):
            original_status = get_person_item_status(df, selected_name, item)
            original_display = REVERSE_STATUS_MAP.get(original_status, "אין")
            
            # Set default value on first load
            key = f"item_{item}"
            if not st.session_state.initialized:
                default_idx = STATUS_OPTIONS.index(original_display)
            else:
                default_idx = STATUS_OPTIONS.index(st.session_state.get(key, original_display))
            
            # Alternating background
            row_class = "item-row-even" if i % 2 == 0 else "item-row-odd"
            st.markdown(f'<div class="{row_class}">', unsafe_allow_html=True)
            
            selected = st.radio(
                f"{i+1}. {item}",
                options=STATUS_OPTIONS,
                index=default_idx,
                key=key,
                horizontal=True,
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
