try:
    import streamlit as st
except Exception:
    st = None

import json

try:
    import pandas as pd
except Exception:
    pd = None
import os
import shutil
import time
from datetime import datetime

# --- IMPORT SHARED BRAIN ---
import utils

# --- CONFIGURATION ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(PROJECT_ROOT, "data", "commands.json")
BACKUP_DIR = os.path.join(PROJECT_ROOT, "data", "backups")

# --- PAGE CONFIG ---
st.set_page_config(page_title="CommandDB", layout="wide", page_icon="💻")


# --- HELPERS ---
def execute_hotkey_wrapper(cmd, soft):
    with st.spinner(f"Sending keys to {soft}..."):
        success = utils.run_hotkey(cmd, soft)
    if success:
        st.toast(f"⌨️ Sent: {cmd}")
    else:
        st.error(f"Could not focus '{soft}' or send keys.")


def execute_command_wrapper(cmd):
    with st.spinner("Executing command..."):
        success = utils.run_command_locally(cmd)
    if success:
        st.toast(f"🚀 Executed: {cmd}")
    else:
        st.error(f"Failed to run: {cmd}")


def create_backup():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    try:
        shutil.copy(DB_FILE, os.path.join(BACKUP_DIR, f"commands_backup_{timestamp}.json"))
        return True
    except Exception:
        return False


@st.cache_data(ttl=60)
def load_data():
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, "r") as f:
        data = json.load(f)
    for item in data:
        if "software" not in item:
            item["software"] = "General"
    return data


def save_data(df_to_save):
    create_backup()
    try:
        json_str = df_to_save.to_json(orient="records", indent=4)
        parsed = json.loads(json_str)
        with open(DB_FILE, "w") as f:
            json.dump(parsed, f, indent=4)
        st.cache_data.clear()
        st.success("✅ Saved! (Backup created)")
    except Exception as e:
        st.error(f"Error: {e}")


# --- APP START ---
st.title("💻 Command Manager")
raw_data = load_data()
if not raw_data:
    st.warning("No commands found.")
    st.stop()
df = pd.DataFrame(raw_data)

# --- METRICS ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Commands", len(df))
col2.metric("Categories", len(df["category"].unique()))
col3.metric("Software/OS", len(df["software"].unique()))
all_tags = [tag for tags in df["tags"] for tag in tags]
col4.metric("Top Tag", max(set(all_tags), key=all_tags.count) if all_tags else "None")
st.markdown("---")

# --- SIDEBAR ---
st.sidebar.header("🔍 Filter Options")
available_soft = list(df["software"].unique())
selected_software = st.sidebar.multiselect(
    "Software / OS", options=available_soft, default=available_soft
)
available_cats = list(df["category"].unique())
selected_category = st.sidebar.multiselect(
    "Category", options=available_cats, default=available_cats
)
search_term = st.text_input("Search (Command, Desc, or Tags)...", "")

mask = (df["software"].isin(selected_software)) & (df["category"].isin(selected_category))
filtered_df = df[mask]
if search_term:
    search_mask = (
        filtered_df.astype(str)
        .apply(lambda x: x.str.contains(search_term, case=False, na=False))
        .any(axis=1)
    )
    filtered_df = filtered_df[search_mask]

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["📝 Edit Database", "🃏 Card View", "🏷️ Auto-Tagger"])

# --- TAB 1: EDITOR ---
with tab1:
    st.info("💡 Click any cell to edit. Edits are auto-backed up on Save.")
    preset_options = [
        "Windows",
        "Mac",
        "Linux",
        "VS Code",
        "Chrome",
        "General",
        "Terminal",
        "Git",
        "Docker",
        "Python",
        "Obsidian",
    ]
    combined_options = sorted(list(set(preset_options + df["software"].unique().tolist())))

    edited_df = st.data_editor(
        filtered_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "command": st.column_config.TextColumn("Command", required=True),
            "software": st.column_config.SelectboxColumn(
                "Software", width="medium", options=combined_options, required=True
            ),
            "category": st.column_config.SelectboxColumn(
                "Category",
                width="medium",
                options=["Hotkey", "Run Panel", "CMD", "PowerShell", "Snippet", "Workflow"],
                required=True,
            ),
            "tags": st.column_config.ListColumn("Tags", width="large"),
        },
        key="editor",
    )
    if st.button("💾 Save Changes", type="primary"):
        if len(filtered_df) != len(df):
            st.error("⚠️ Clear filters before saving.")
        else:
            save_data(edited_df)

# --- TAB 2: CARDS ---
with tab2:
    software_groups = sorted(filtered_df["software"].unique())
    st.write(f"### Showing {len(filtered_df)} Commands")
    for software in software_groups:
        icon = utils.get_icon(software)
        subset = filtered_df[filtered_df["software"] == software]
        with st.expander(f"{icon} {software} ({len(subset)})", expanded=False):
            cols = st.columns(3)
            for index, row in subset.reset_index().iterrows():
                with cols[index % 3]:
                    with st.container(border=True):
                        st.markdown(
                            f"### {icon} {row['software']}<br>"
                            f"<span style='font-size: 0.9em; color: #ccc'>"
                            f"{row['description']}</span>",
                            unsafe_allow_html=True,
                        )
                        st.code(row["command"], language="powershell")
                        st.caption(f"**Type:** {row['category']}")

                        if row["category"] in [
                            "Run Panel",
                            "CMD",
                            "PowerShell",
                            "Windows",
                            "Workflow",
                        ]:
                            with st.popover("⚙️ Run...", use_container_width=True):
                                user_arg = st.text_input(
                                    "Replace variable:",
                                    key=f"arg_{software}_{index}_{row['command']}",
                                    placeholder="Leave empty to run as-is",
                                )
                                final_cmd = utils.resolve_command(row["command"], user_arg)
                                st.caption(f"Preview: `{final_cmd}`")
                                if st.button(
                                    "🚀 Execute", key=f"btn_{software}_{index}_{row['command']}"
                                ):
                                    # Handle Run Panel workflows (e.g. win + r > cmd)
                                    if row["category"] == "Run Panel" and ">" in final_cmd:
                                        parts = final_cmd.split(">")
                                        final_cmd = (
                                            f"{parts[0].strip()} ;; WAIT 0.5 ;; "
                                            f"TYPE {parts[1].strip()} ;; enter"
                                        )
                                    
                                    # Handle CLI tools visibility
                                    elif row["category"] == "CMD":
                                        final_cmd = f'start cmd /k "{final_cmd}"'
                                    elif row["category"] == "PowerShell":
                                        final_cmd = (
                                            f'start powershell -NoExit -Command "{final_cmd}"'
                                        )

                                    execute_command_wrapper(final_cmd)
                        elif row["category"] == "Hotkey":
                            if st.button(
                                "⌨️ Send Keys", key=f"key_{software}_{index}_{row['command']}"
                            ):
                                execute_hotkey_wrapper(row["command"], row["software"])

                        with st.expander("Tags"):
                            st.write(f"{', '.join(row['tags'])}")
        st.write("")

# --- TAB 3: AUTO-TAGGER ---
with tab3:
    st.header("🏷️ Bulk Auto-Tagger")
    st.info("Automatically generate tags based on keywords found in the Description or Command.")
    with st.expander("⚙️ Configure Tagging Rules", expanded=False):
        default_rules = {
            # File Management
            "file": ["file", "document", "project", "folder", "directory", "path"],
            "save": ["save", "export", "write", "download", "backup", "archive"],
            "open": ["open", "load", "import", "new", "create", "add"],
            "close": ["close", "exit", "quit", "shutdown", "terminate"],
            "print": ["print", "page setup", "preview"],
            # Editing & Clipboard
            "edit": ["edit", "change", "modify", "update", "rename", "replace"],
            "clipboard": ["copy", "paste", "cut", "clipboard", "duplicate"],
            "undo": ["undo", "redo", "revert", "restore"],
            "select": ["select", "highlight", "mark", "choose"],
            "delete": ["delete", "remove", "erase", "clear", "trash", "discard"],
            # View & Navigation
            "view": ["view", "zoom", "show", "hide", "toggle", "preview", "display", "mode"],
            "nav": [
                "navigate",
                "go to",
                "find",
                "search",
                "next",
                "previous",
                "scroll",
                "move",
                "jump",
                "switch",
            ],
            "window": [
                "window",
                "tab",
                "pane",
                "split",
                "screen",
                "monitor",
                "minimize",
                "maximize",
            ],
            # Development
            "code": [
                "code",
                "debug",
                "terminal",
                "console",
                "function",
                "variable",
                "class",
                "method",
                "syntax",
                "api",
                "sdk",
            ],
            "git": [
                "git",
                "commit",
                "push",
                "pull",
                "branch",
                "merge",
                "checkout",
                "repo",
                "clone",
                "diff",
                "stash",
                "rebase",
            ],
            "build": [
                "build",
                "compile",
                "make",
                "deploy",
                "publish",
                "release",
                "package",
                "dist",
            ],
            "test": ["test", "spec", "assert", "verify", "check", "benchmark", "coverage", "lint"],
            "db": [
                "database",
                "sql",
                "query",
                "table",
                "row",
                "column",
                "index",
                "migration",
                "schema",
                "record",
            ],
            "web": [
                "html",
                "css",
                "javascript",
                "js",
                "dom",
                "element",
                "browser",
                "url",
                "link",
                "http",
                "request",
                "response",
            ],
            "cloud": [
                "cloud",
                "aws",
                "azure",
                "gcp",
                "docker",
                "kubernetes",
                "container",
                "pod",
                "service",
                "lambda",
                "serverless",
            ],
            "data": [
                "data",
                "analysis",
                "pandas",
                "numpy",
                "plot",
                "graph",
                "chart",
                "csv",
                "json",
                "xml",
                "yaml",
            ],
            # System & Settings
            "system": [
                "system",
                "os",
                "kernel",
                "process",
                "service",
                "daemon",
                "registry",
                "task",
                "cpu",
                "memory",
                "disk",
            ],
            "settings": [
                "settings",
                "config",
                "preferences",
                "options",
                "properties",
                "setup",
                "install",
                "env",
                "variable",
            ],
            "security": [
                "security",
                "password",
                "login",
                "logout",
                "auth",
                "permission",
                "lock",
                "encrypt",
                "ssh",
                "key",
                "cert",
            ],
            "network": [
                "network",
                "wifi",
                "ip",
                "dns",
                "port",
                "connection",
                "server",
                "client",
                "proxy",
                "vpn",
                "firewall",
            ],
            "shell": [
                "bash",
                "zsh",
                "powershell",
                "cmd",
                "script",
                "pipe",
                "redirect",
                "echo",
                "cat",
                "ls",
                "cd",
                "grep",
                "sed",
                "awk",
            ],
            # Office & Productivity
            "office": [
                "email",
                "mail",
                "outlook",
                "calendar",
                "meeting",
                "schedule",
                "task",
                "todo",
                "spreadsheet",
                "excel",
                "sheet",
                "slide",
                "presentation",
                "powerpoint",
                "doc",
                "word",
                "pdf",
                "report",
                "memo",
                "agenda",
            ],
            "text": [
                "text",
                "string",
                "regex",
                "pattern",
                "match",
                "find",
                "replace",
                "word",
                "line",
                "char",
                "paragraph",
                "sentence",
                "case",
                "upper",
                "lower",
                "trim",
                "split",
                "join",
            ],
            "collab": [
                "share",
                "comment",
                "review",
                "approve",
                "reject",
                "chat",
                "message",
                "team",
                "slack",
                "discord",
                "zoom",
                "teams",
            ],
            "finance": [
                "money",
                "cost",
                "price",
                "budget",
                "invoice",
                "bill",
                "tax",
                "calc",
                "finance",
                "accounting",
            ],
            # Media & Formatting
            "media": [
                "play",
                "pause",
                "stop",
                "record",
                "volume",
                "mute",
                "track",
                "audio",
                "video",
                "image",
                "picture",
                "photo",
                "music",
                "sound",
                "mic",
                "camera",
                "stream",
                "broadcast",
                "capture",
                "screenshot",
                "clip",
                "movie",
                "film",
            ],
            "format": [
                "format",
                "bold",
                "italic",
                "underline",
                "font",
                "align",
                "indent",
                "style",
                "color",
                "size",
                "theme",
                "highlight",
                "strike",
                "subscript",
                "superscript",
                "header",
                "footer",
                "margin",
                "padding",
                "border",
                "background",
            ],
            "graphics": [
                "draw",
                "paint",
                "sketch",
                "design",
                "vector",
                "pixel",
                "canvas",
                "layer",
                "mask",
                "filter",
                "crop",
                "resize",
                "svg",
                "png",
                "jpg",
                "gif",
            ],
            # Execution
            "run": [
                "run",
                "execute",
                "start",
                "launch",
                "play",
                "trigger",
                "invoke",
                "call",
                "spawn",
                "init",
                "boot",
                "activate",
                "enable",
                "resume",
                "restart",
                "reload",
            ],
            "schedule": [
                "schedule",
                "cron",
                "timer",
                "delay",
                "wait",
                "timeout",
                "interval",
                "period",
                "at",
                "batch",
                "job",
            ],
        }
        st.json(default_rules)
        tag_rules = default_rules  # Use defaults for now

    # --- TARGET SELECTION ---
    st.subheader("Target Selection")
    c1, c2 = st.columns(2)

    # Gather all tags
    all_existing_tags = set()
    for tags in df["tags"]:
        if isinstance(tags, list):
            all_existing_tags.update(tags)

    # Filter Inputs
    sel_tags = c1.multiselect(
        "Filter by existing tag:",
        sorted(list(all_existing_tags)),
        default=["import"] if "import" in all_existing_tags else [],
    )
    sel_soft = c2.multiselect("Filter by Software:", sorted(df["software"].unique()))

    # Calculate Target
    def match_filters(row):
        # Tag Filter
        if sel_tags:
            row_tags = row["tags"] if isinstance(row["tags"], list) else []
            if not any(t in row_tags for t in sel_tags):
                return False
        # Software Filter
        if sel_soft:
            if row["software"] not in sel_soft:
                return False
        return True

    target_indices = [i for i, r in df.iterrows() if match_filters(r)]
    st.markdown(f"Found **{len(target_indices)}** commands to process.")

    remove_import = st.checkbox("Remove 'import' tag after processing", value=True)

    # Initialize session state for preview
    if "preview_data" not in st.session_state:
        st.session_state.preview_data = None

    if st.button("🔍 Generate Preview"):
        preview_changes = []

        for idx in target_indices:
            row = df.loc[idx]
            current_list = row["tags"] if isinstance(row["tags"], list) else []
            current_set = {t.lower() for t in current_list}
            new_tags = set()

            # Check Keywords
            text_to_scan = (str(row["description"]) + " " + str(row["command"])).lower()
            for tag, keywords in tag_rules.items():
                for keyword in keywords:
                    if keyword in text_to_scan:
                        new_tags.add(tag)
                        break

            # Add Software Name
            soft = str(row["software"]).lower().strip()
            if soft and soft != "general":
                new_tags.add(soft)

            # Calculate Final
            final_set = current_set | new_tags

            # Determine removed tags (specifically 'import')
            removed_tags = set()
            if remove_import and "import" in final_set:
                final_set.discard("import")
                if "import" in current_set:
                    removed_tags.add("import")

            # Only record if there's a change
            if final_set != current_set:
                added_tags = final_set - current_set
                preview_changes.append(
                    {
                        "Index": idx,
                        "Command": row["command"],
                        "Current Tags": ", ".join(sorted(current_list)),
                        "Added Tags": ", ".join(sorted(added_tags)),
                        "Removed Tags": ", ".join(sorted(removed_tags)),
                        "Final Tags": ", ".join(sorted(final_set)),
                        "New Tag Set": sorted(list(final_set)),  # Store for application
                    }
                )

        st.session_state.preview_data = preview_changes

    # Display Preview and Apply Button
    if st.session_state.preview_data is not None:
        changes = st.session_state.preview_data
        if len(changes) > 0:
            st.write(f"### 📋 Preview: {len(changes)} commands will be updated")

            # Create a display dataframe
            preview_df = pd.DataFrame(changes)
            st.dataframe(
                preview_df[["Command", "Current Tags", "Added Tags", "Removed Tags", "Final Tags"]],
                use_container_width=True,
            )

            if st.button("✅ Confirm & Apply Changes"):
                updates_count = 0
                for change in changes:
                    idx = change["Index"]
                    new_tag_list = change["New Tag Set"]
                    df.at[idx, "tags"] = new_tag_list
                    updates_count += 1

                save_data(df)
                st.success(f"Successfully updated {updates_count} commands!")
                st.session_state.preview_data = None  # Reset
                time.sleep(1.5)
                st.rerun()
        else:
            st.info("No changes detected with current rules.")
            st.session_state.preview_data = None
