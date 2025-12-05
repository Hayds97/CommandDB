import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import Listbox, messagebox, simpledialog, ttk


# --- 1. SELF-HEALING CHECK ---
def check_deps():
    required = [
        "keyboard",
        "pyperclip",
        "pyautogui",
        "pygetwindow",
        "streamlit",
        "pandas",
        "requests",
        "lxml",
        "html5lib",
        "beautifulsoup4",
    ]
    missing = [lib for lib in required if importlib.util.find_spec(lib) is None]
    if missing:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        if messagebox.askyesno(
            "Setup Required", f"Install missing libraries?\n{', '.join(missing)}"
        ):
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
            except Exception:
                sys.exit()
        else:
            sys.exit()
        root.destroy()


check_deps()

# --- 2. IMPORTS ---
import keyboard  # noqa: E402
import pyperclip  # noqa: E402

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(PROJECT_ROOT, "data", "commands.json")
BACKUP_DIR = os.path.join(PROJECT_ROOT, "data", "backups")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
import utils  # noqa: E402

# --- 3. SINGLE INSTANCE ---
try:
    _lock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    _lock.bind(("127.0.0.1", 49202))
except Exception:
    sys.exit()

# --- CONFIG ---
HOTKEY_ADD = "ctrl+alt+a"
HOTKEY_VISUAL = "ctrl+alt+v"
HOTKEY_HARVEST = "ctrl+alt+h"
# DB_FILE and BACKUP_DIR are defined above

# --- THEME ---
BG = "#0E1117"
FG = "#FAFAFA"
ACCENT = "#00FF41"
IN_BG = "white"
IN_FG = "black"


class QuickAddWidget:
    def __init__(self):
        self.root = None
        self.db_data = []
        self.last_mtime = 0

    def initialize_root(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("✅ Command Center")
        
        # Icon
        try:
            from ctypes import windll
            windll.shell32.SetCurrentProcessExplicitAppUserModelID("commanddb.cc.v1")
            self.root.iconbitmap(os.path.join(ASSETS_DIR, "app_icon.ico"))
        except Exception:
            pass

        self.root.configure(bg=BG)
        self.root.attributes("-topmost", True)

        # Center
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"550x450+{int((sw/2)-275)}+{int((sh/2)-225)}")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background="#262730", foreground=FG, padding=[15, 5])
        style.map(
            "TNotebook.Tab", background=[("selected", ACCENT)], foreground=[("selected", "black")]
        )

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_add = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(self.tab_add, text="  + Add New  ")
        self.setup_add()

        self.tab_search = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(self.tab_search, text="  🔍 Search & Run  ")
        self.setup_search()

        self.tab_cards = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(self.tab_cards, text="  🃏 Cards  ")
        self.setup_cards()

        self.notebook.select(self.tab_search)
        self.root.bind("<Escape>", lambda e: self.close())
        
        # Handle window close button (X)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def load_db(self):
        if os.path.exists(DB_FILE):
            mtime = os.path.getmtime(DB_FILE)
            if mtime == self.last_mtime and self.db_data:
                return

            try:
                with open(DB_FILE, "r") as f:
                    self.db_data = json.load(f)
                # Pre-compute search strings for performance
                for item in self.db_data:
                    item["_search_str"] = (
                        f"{item['command']} {item['description']} {item.get('software','')} "
                        f"{' '.join(item.get('tags',[]))}"
                    ).lower()
                self.last_mtime = mtime
            except Exception:
                self.db_data = []
        else:
            self.db_data = []

    def show(self):
        # Workaround: 'suppress=True' is unreliable for Ctrl+Alt+A on some systems.
        # We manually clean up the typed character.
        
        # 1. Release modifiers to avoid Ctrl+Backspace / Alt+Backspace
        for k in ["ctrl", "alt", "shift", "right ctrl", "right alt", "right shift"]:
            try:
                keyboard.release(k)
            except Exception:
                pass
        
        # 2. Brief delay and backspace
        time.sleep(0.05)
        keyboard.send("backspace")

        self.load_db()
        
        # Refresh lists
        self.update_list()
        self.update_software_list()
        self.refresh_cards()
        
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.entry_search.focus_set()
        self.entry_search.selection_range(0, tk.END)

    def setup_cards(self):
        # Filter Frame
        f_top = tk.Frame(self.tab_cards, bg=BG, padx=10, pady=10)
        f_top.pack(fill="x")

        # Software Dropdown
        self.card_soft_var = tk.StringVar(value="All Software")
        self.c_card_soft = ttk.Combobox(f_top, textvariable=self.card_soft_var, state="readonly")
        self.c_card_soft.pack(side="left", fill="x", expand=False, padx=(0, 10))
        self.c_card_soft.bind("<<ComboboxSelected>>", self.refresh_cards)

        # Search Bar
        self.card_search_var = tk.StringVar()
        self.card_search_var.trace("w", self.refresh_cards)
        tk.Entry(
            f_top, textvariable=self.card_search_var, bg=IN_BG, fg=IN_FG, relief="solid", bd=1
        ).pack(side="left", fill="x", expand=True, ipady=3)

        # Scrollable Canvas
        self.canvas = tk.Canvas(self.tab_cards, bg=BG, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.tab_cards, orient="vertical", command=self.canvas.yview)
        self.card_frame = tk.Frame(self.canvas, bg=BG)

        self.card_frame.bind(
            "<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        # Window inside canvas
        self.canvas_window = self.canvas.create_window((0, 0), window=self.card_frame, anchor="nw")

        # Resize frame to match canvas width
        def on_canvas_configure(event):
            self.canvas.itemconfig(self.canvas_window, width=event.width)

        self.canvas.bind("<Configure>", on_canvas_configure)

        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Mousewheel
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Initial Population
        self.update_software_list()
        self.refresh_cards()

    def update_software_list(self):
        softwares = sorted(list({i.get("software", "General") for i in self.db_data}))
        self.c_card_soft["values"] = ["All Software"] + softwares
        self.c_card_soft.current(0)

    def _on_mousewheel(self, event):
        if self.notebook.select() == str(self.tab_cards):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def refresh_cards(self, *args):
        for w in self.card_frame.winfo_children():
            w.destroy()

        query = self.card_search_var.get().lower()
        selected_soft = self.card_soft_var.get()

        # Filter
        filtered = []
        for i in self.db_data:
            # Software Filter
            item_soft = i.get("software", "General")
            if selected_soft != "All Software" and item_soft != selected_soft:
                continue

            # Text Filter
            if query in (f"{i['command']} {i['description']} {item_soft}").lower():
                filtered.append(i)

        # Limit results for performance if showing "All"
        if selected_soft == "All Software" and len(filtered) > 50 and not query:
            tk.Label(
                self.card_frame,
                text=(
                    f"Showing first 50 of {len(filtered)} items. "
                    "Select a software or search to see more."
                ),
                bg=BG,
                fg="#888",
            ).pack(pady=10)
            filtered = filtered[:50]

        # Group
        grouped = {}
        for item in filtered:
            soft = item.get("software", "General")
            if soft not in grouped:
                grouped[soft] = []
            grouped[soft].append(item)

        for soft in sorted(grouped.keys()):
            tk.Label(
                self.card_frame, text=soft, bg=BG, fg=ACCENT, font=("Segoe UI", 10, "bold")
            ).pack(fill="x", padx=10, pady=(10, 5), anchor="w")

            grid = tk.Frame(self.card_frame, bg=BG)
            grid.pack(fill="x", padx=5)
            grid.grid_columnconfigure(0, weight=1)
            grid.grid_columnconfigure(1, weight=1)

            for idx, item in enumerate(grouped[soft]):
                self.create_card(grid, item, idx // 2, idx % 2)

    def create_card(self, parent, item, row, col):
        card = tk.Frame(
            parent, bg="#1E1E1E", padx=8, pady=8, highlightbackground="#333", highlightthickness=1
        )
        card.grid(row=row, column=col, sticky="ew", padx=5, pady=5)

        # Header
        icon = utils.get_icon(item.get("software", ""))
        tk.Label(
            card,
            text=f"{icon} {item['description']}",
            bg="#1E1E1E",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x")

        # Category
        tk.Label(
            card,
            text=f"Type: {item['category']}",
            bg="#1E1E1E",
            fg="#666",
            font=("Segoe UI", 7),
            anchor="w",
        ).pack(fill="x")

        # Command
        cmd = item["command"]
        if len(cmd) > 25:
            cmd = cmd[:22] + "..."
        tk.Label(card, text=cmd, bg="#1E1E1E", fg="#888", font=("Consolas", 8), anchor="w").pack(
            fill="x", pady=5
        )

        # Buttons
        btns = tk.Frame(card, bg="#1E1E1E")
        btns.pack(fill="x")

        cat = item["category"]
        if cat == "Hotkey":
            tk.Button(
                btns,
                text="⌨️ Keys",
                bg="#00d2ff",
                fg="black",
                font=("Segoe UI", 8),
                relief="flat",
                command=lambda i=item: self.execute_item(i),
            ).pack(side="left", fill="x", expand=True, padx=(0, 2))
        elif cat in ["CMD", "Run Panel", "PowerShell", "Workflow"]:
            tk.Button(
                btns,
                text="🚀 Run",
                bg=ACCENT,
                fg="black",
                font=("Segoe UI", 8),
                relief="flat",
                command=lambda i=item: self.execute_item(i),
            ).pack(side="left", fill="x", expand=True, padx=(0, 2))

        tk.Button(
            btns,
            text="📋",
            bg="#333",
            fg="white",
            font=("Segoe UI", 8),
            relief="flat",
            width=3,
            command=lambda i=item: pyperclip.copy(i["command"]),
        ).pack(side="right")

    def setup_add(self):
        f = tk.Frame(self.tab_add, bg=BG, padx=15, pady=15)
        f.pack(fill="both", expand=True)

        self.lbl(f, "Command:", ACCENT)
        self.e_cmd = self.entry(f)
        self.e_cmd.pack(fill="x", pady=(0, 10), ipady=4)

        self.lbl(f, "Description:", FG)
        self.e_desc = self.entry(f)
        self.e_desc.pack(fill="x", pady=(0, 10), ipady=4)

        row = tk.Frame(f, bg=BG)
        row.pack(fill="x", pady=5)
        self.lbl(row, "Software:", FG, "left")
        self.c_soft = ttk.Combobox(
            row, values=["General", "Windows", "VS Code", "Terminal", "Git", "Obsidian", "Chrome"]
        )
        self.c_soft.current(0)
        self.c_soft.pack(side="left", fill="x", expand=True, padx=(5, 10))

        self.lbl(row, "Type:", FG, "left")
        self.c_cat = ttk.Combobox(row, values=["Hotkey", "CMD", "Run Panel", "Snippet", "Workflow"])
        self.c_cat.current(0)
        self.c_cat.pack(side="left", fill="x", expand=True)

        self.lbl(f, "Tags:", FG)
        self.e_tags = self.entry(f)
        self.e_tags.pack(fill="x", pady=(0, 15), ipady=4)

        tk.Button(
            f,
            text="SAVE",
            bg=ACCENT,
            fg="black",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            command=self.save,
        ).pack(side="bottom", fill="x", ipady=5)

    def setup_search(self):
        f = tk.Frame(self.tab_search, bg=BG, padx=15, pady=15)
        f.pack(fill="both", expand=True)
        self.lbl(f, "Search:", "#888")

        self.s_var = tk.StringVar()
        self.s_var.trace("w", self.update_list)
        self.entry_search = self.entry(f, self.s_var)
        self.entry_search.pack(fill="x", pady=(0, 10), ipady=4)

        self.list = Listbox(
            f,
            bg="white",
            fg="black",
            font=("Consolas", 10),
            relief="flat",
            height=10,
            selectbackground=ACCENT,
            selectforeground="black",
        )
        self.list.pack(fill="both", expand=True)
        self.list.bind("<<ListboxSelect>>", self.show_details)
        self.list.bind("<Return>", lambda e: self.run_action())
        self.list.bind("<Double-Button-1>", lambda e: self.run_action())

        det = tk.Frame(f, bg=BG)
        det.pack(fill="x", pady=(10, 0))
        self.lbl_det = tk.Label(
            det, text="Select an item...", bg=BG, fg="#888", justify="left", anchor="w"
        )
        self.lbl_det.pack(side="left", fill="x", expand=True)
        self.btn_run = tk.Button(
            det,
            text="RUN",
            bg=ACCENT,
            fg="black",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            command=self.run_action,
        )

    def update_list(self, *a):
        q = self.s_var.get().lower()
        self.list.delete(0, tk.END)
        self.filtered = []

        count = 0
        MAX_RESULTS = 50

        for i in self.db_data:
            # Use pre-computed search string
            if q in i.get("_search_str", ""):
                self.filtered.append(i)
                self.list.insert(tk.END, f"[{i.get('software','Gen')}] {i['description']}")
                count += 1
                if count >= MAX_RESULTS:
                    break

        if count >= MAX_RESULTS:
            self.list.insert(tk.END, "... (Keep typing to refine search)")

    def show_details(self, e):
        sel = self.list.curselection()
        if not sel:
            self.btn_run.pack_forget()
            return
        item = self.filtered[sel[0]]
        self.lbl_det.config(text=f"CMD: {item['command']}", fg=FG)
        self.btn_run.pack(side="right", padx=5)

        cat = item["category"]
        if cat == "Hotkey":
            self.btn_run.config(text="⌨️ KEYS", bg="#00d2ff")
        elif cat in ["CMD", "Run Panel", "PowerShell", "Workflow"]:
            self.btn_run.config(text="🚀 RUN", bg=ACCENT)
        else:
            self.btn_run.config(text="📋 COPY", bg="#333", fg="white")

    def run_action(self):
        sel = self.list.curselection()
        if not sel:
            return
        item = self.filtered[sel[0]]
        self.execute_item(item)

    def execute_item(self, item):
        self.root.withdraw()

        if item["category"] == "Hotkey":
            threading.Thread(
                target=utils.run_hotkey, args=(item["command"], item.get("software", "General"))
            ).start()
        elif item["category"] in ["CMD", "Run Panel", "PowerShell", "Workflow"]:
            cmd = item["command"]
            if any(p in cmd for p in utils.PLACEHOLDERS):
                r = tk.Tk()
                r.withdraw()
                r.attributes("-topmost", True)
                arg = simpledialog.askstring("Input", f"Command: {cmd}\nEnter argument:")
                r.destroy()
                if arg is None:
                    return
                cmd = utils.resolve_command(cmd, arg)
            
            # Handle Run Panel workflows (e.g. win + r > cmd)
            if item["category"] == "Run Panel" and ">" in cmd:
                parts = cmd.split(">")
                # Construct workflow: hotkey ;; WAIT 0.5 ;; TYPE text ;; enter
                cmd = f"{parts[0].strip()} ;; WAIT 0.5 ;; TYPE {parts[1].strip()} ;; enter"

            # Handle CLI tools visibility
            elif item["category"] == "CMD":
                if ";;" not in cmd:
                    cmd = f'start cmd /k "{cmd}"'
            elif item["category"] == "PowerShell":
                if ";;" not in cmd:
                    cmd = f'start powershell -NoExit -Command "{cmd}"'
                
            threading.Thread(target=utils.run_command_locally, args=(cmd,)).start()
        else:
            pyperclip.copy(item["command"])

    def lbl(self, p, t, c, s="top"):
        tk.Label(p, text=t, bg=BG, fg=c, font=("Segoe UI", 9)).pack(side=s, anchor="w", pady=(0, 2))

    def entry(self, p, v=None):
        return tk.Entry(
            p, textvariable=v, bg=IN_BG, fg=IN_FG, relief="solid", bd=1, font=("Segoe UI", 10)
        )

    def save(self):
        cmd = self.e_cmd.get().strip()
        if not cmd:
            return
        new = {
            "command": cmd,
            "software": self.c_soft.get(),
            "description": self.e_desc.get().strip(),
            "category": self.c_cat.get(),
            "tags": [t.strip() for t in self.e_tags.get().split(",") if t.strip()],
        }
        self.append_db(new)
        self.root.withdraw()

    def append_db(self, entry):
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        shutil.copy(
            DB_FILE,
            os.path.join(
                BACKUP_DIR, f"backup_quick_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            ),
        )
        try:
            with open(DB_FILE, "r") as f:
                d = json.load(f)
            d.append(entry)
            with open(DB_FILE, "w") as f:
                json.dump(d, f, indent=4)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def close(self):
        if self.root:
            self.root.withdraw()


def listen():
    print(f"✅ CommandDB Services Running (Python {sys.version.split()[0]})...")
    print(f"  [1] Quick Add: {HOTKEY_ADD}")
    print(f"  [2] Visual DB: {HOTKEY_VISUAL}")
    print(f"  [3] Harvester: {HOTKEY_HARVEST}")

    # Helper to launch scripts using the current python executable
    def launch(script):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), script)
        if os.path.exists(path):
            subprocess.Popen([sys.executable, "-m", "streamlit", "run", path])

    widget = QuickAddWidget()
    widget.initialize_root()
    
    # Use suppress=False and manual cleanup since suppress=True is flaky
    keyboard.add_hotkey(HOTKEY_ADD, lambda: widget.root.after(0, widget.show), suppress=False)
    keyboard.add_hotkey(HOTKEY_VISUAL, lambda: launch("visual_db.py"))
    keyboard.add_hotkey(HOTKEY_HARVEST, lambda: launch("importer.py"))
    
    # Run Tkinter mainloop instead of keyboard.wait()
    widget.root.mainloop()


if __name__ == "__main__":
    listen()
