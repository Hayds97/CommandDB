import io
import json
import os
import shutil
import webbrowser
from datetime import datetime

import pandas as pd
import requests
import streamlit as st

# --- CONFIG ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(PROJECT_ROOT, "data", "commands.json")
BACKUP_DIR = os.path.join(PROJECT_ROOT, "data", "backups")

st.set_page_config(page_title="Web Harvester", page_icon="🕷️", layout="wide")


# --- FUNCTIONS ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_db_smart(new_data):
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    shutil.copy(
        DB_FILE,
        os.path.join(BACKUP_DIR, f"backup_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"),
    )

    current_db = load_db()
    existing_signatures = {
        f"{item.get('software','').lower()}|{item['command'].lower().strip()}"
        for item in current_db
    }

    added, skipped = 0, 0
    for entry in new_data:
        sig = f"{entry['software'].lower()}|{entry['command'].lower().strip()}"
        if sig in existing_signatures:
            skipped += 1
            continue
        current_db.append(entry)
        existing_signatures.add(sig)
        added += 1

    with open(DB_FILE, "w") as f:
        json.dump(current_db, f, indent=4)
    return added, skipped


st.title("🕷️ Web Command Harvester")

# --- STEP 1: FIND ---
st.header("1. Find")
col1, col2 = st.columns([3, 1])
search_query = col1.text_input("Software Name", placeholder="e.g. Blender")
if col1.button("🔍 Search Google"):
    webbrowser.open(
        f"https://www.google.com/search?q={search_query}+keyboard+shortcuts+cheat+sheet+filetype:html"
    )

# --- STEP 2: SCRAPE ---
st.header("2. Paste URL")
url_input = st.text_input(
    "URL:", placeholder="https://en.wikipedia.org/wiki/Table_of_keyboard_shortcuts"
)

if url_input:
    try:
        # FAKE BROWSER HEADER TO FIX 403 ERROR
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            )
        }
        response = requests.get(url_input, headers=headers)
        response.raise_for_status()

        tables = pd.read_html(io.StringIO(response.text))

        if tables:
            st.success(f"Found {len(tables)} tables!")

            # --- SELECTION LOGIC ---
            use_all = st.checkbox("Select All Tables", value=False)

            if use_all:
                selected_indices = list(range(len(tables)))
                st.info(f"Selected all {len(tables)} tables.")
            else:
                selected_indices = st.multiselect(
                    "Select Tables:",
                    range(len(tables)),
                    format_func=lambda x: f"Table {x+1} ({len(tables[x])} rows)",
                )

            if selected_indices:
                # Preview based on first selection
                first_idx = selected_indices[0]
                first_df = tables[first_idx]

                st.subheader("Schema Configuration")
                st.caption(f"Configuring based on Table {first_idx+1}")
                st.dataframe(first_df.head(3))

                # Column Mapping Strategy
                col_mode = st.radio(
                    "Match Columns By:", ["Header Name", "Column Index"], horizontal=True
                )

                cols = first_df.columns.tolist()
                c1, c2, c3 = st.columns(3)

                sel_cmd, sel_desc = None, None
                sel_cmd_idx, sel_desc_idx = 0, 0

                if col_mode == "Header Name":
                    col_options = [str(c) for c in cols]
                    sel_cmd = c1.selectbox("Command Column", options=col_options, index=0)
                    sel_desc = c2.selectbox(
                        "Description Column", options=col_options, index=1 if len(cols) > 1 else 0
                    )
                else:
                    col_options = range(len(cols))

                    # Helper to show a sample value in the dropdown
                    def fmt_col(i):
                        val = str(first_df.iloc[0, i]) if not first_df.empty else ""
                        return f"Column {i+1} (Ex: {val[:15]}...)"

                    sel_cmd_idx = c1.selectbox(
                        "Command Column", col_options, index=0, format_func=fmt_col
                    )
                    sel_desc_idx = c2.selectbox(
                        "Description Column",
                        col_options,
                        index=1 if len(cols) > 1 else 0,
                        format_func=fmt_col,
                    )

                soft_tag = c3.text_input(
                    "Software Tag", value=search_query if search_query else "General"
                )

                if st.button("🚀 IMPORT SELECTED", type="primary"):
                    preview = []
                    progress = st.progress(0)

                    for i, idx in enumerate(selected_indices):
                        df = tables[idx]
                        try:
                            if col_mode == "Header Name":
                                df.columns = [str(c) for c in df.columns]
                                if sel_cmd in df.columns and sel_desc in df.columns:
                                    for _, row in df.iterrows():
                                        c, d = str(row[sel_cmd]).strip(), str(row[sel_desc]).strip()
                                        if c and c.lower() != "nan":
                                            preview.append(
                                                {
                                                    "command": c,
                                                    "software": soft_tag,
                                                    "description": d,
                                                    "category": "Hotkey",
                                                    "tags": ["import"],
                                                }
                                            )
                            else:
                                # Index Mode
                                if len(df.columns) > max(sel_cmd_idx, sel_desc_idx):
                                    for _, row in df.iterrows():
                                        c = str(row.iloc[sel_cmd_idx]).strip()
                                        d = str(row.iloc[sel_desc_idx]).strip()
                                        if c and c.lower() != "nan":
                                            preview.append(
                                                {
                                                    "command": c,
                                                    "software": soft_tag,
                                                    "description": d,
                                                    "category": "Hotkey",
                                                    "tags": ["import"],
                                                }
                                            )
                        except Exception as e:
                            print(f"Skipping table {idx}: {e}")

                        progress.progress((i + 1) / len(selected_indices))

                    if preview:
                        added, skipped = save_db_smart(preview)
                        st.success(
                            f"Imported {added} commands from {len(selected_indices)} tables! "
                            f"({skipped} duplicates skipped)"
                        )
                        st.balloons()
                    else:
                        st.warning("No valid data found. Check your column mapping.")
        else:
            st.warning("No tables found.")

    except Exception as e:
        st.error(f"Error: {e}")
