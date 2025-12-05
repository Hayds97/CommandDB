import ctypes
import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk

# --- THEME ---
BG = "#0E1117"
FG = "#FAFAFA"
ACCENT = "#00FF41"
HEADER_BG = "#262730"


class Installer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.minimize_console()
        self.title("CommandDB Installer")

        # Icon
        try:
            icon_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "assets",
                "app_icon.ico",
            )
            self.iconbitmap(icon_path)
        except Exception:
            pass

        self.geometry("600x450")
        self.configure(bg=BG)

        # Center window
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - 600) // 2
        y = (screen_height - 450) // 2
        self.geometry(f"600x450+{x}+{y}")

        # Variables
        self.project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.venv_dir = os.path.join(self.project_dir, ".venv")
        self.startup_var = tk.BooleanVar(value=True)

        self.setup_ui()

    def minimize_console(self):
        try:
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE = 6
        except Exception:
            pass

    def setup_ui(self):
        # Header
        header_frame = tk.Frame(self, bg=HEADER_BG, pady=20)
        header_frame.pack(fill="x")

        tk.Label(
            header_frame, text="CommandDB Setup", font=("Segoe UI", 20, "bold"), bg=HEADER_BG, fg=FG
        ).pack()

        tk.Label(
            header_frame,
            text="Personal Automation Suite",
            font=("Segoe UI", 10),
            bg=HEADER_BG,
            fg="#ccc",
        ).pack()

        # Content
        content_frame = tk.Frame(self, bg=BG, padx=40, pady=20)
        content_frame.pack(fill="both", expand=True)

        # Options
        c = tk.Checkbutton(
            content_frame,
            text="Start CommandDB automatically with Windows",
            variable=self.startup_var,
            bg=BG,
            fg=FG,
            selectcolor=BG,
            activebackground=BG,
            activeforeground=FG,
            font=("Segoe UI", 10),
        )
        c.pack(anchor="w", pady=10)

        # Progress
        self.progress_label = tk.Label(
            content_frame, text="Ready to install...", bg=BG, font=("Segoe UI", 9), fg="#ccc"
        )
        self.progress_label.pack(anchor="w", pady=(20, 5))

        self.progress = ttk.Progressbar(content_frame, mode="determinate", length=400)
        self.progress.pack(fill="x")

        # Log
        self.log_text = tk.Text(
            content_frame,
            height=8,
            font=("Consolas", 8),
            state="disabled",
            bg="#1E1E1E",
            fg="#D4D4D4",
            relief="flat",
        )
        self.log_text.pack(fill="x", pady=10)

        # Buttons
        btn_frame = tk.Frame(self, bg=BG, pady=20)
        btn_frame.pack(fill="x", side="bottom")

        self.install_btn = tk.Button(
            btn_frame,
            text="INSTALL",
            command=self.start_install,
            bg=ACCENT,
            fg="black",
            font=("Segoe UI", 10, "bold"),
            padx=30,
            pady=8,
            relief="flat",
            cursor="hand2",
        )
        self.install_btn.pack()

    def log(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")
        self.update_idletasks()

    def start_install(self):
        self.install_btn.config(state="disabled", text="Installing...")
        threading.Thread(target=self.run_installation, daemon=True).start()

    def run_installation(self):
        try:
            # 1. Create venv
            self.progress_label.config(text="Creating virtual environment...")
            self.progress["value"] = 10
            self.log(f"Creating .venv in {self.venv_dir}...")

            subprocess.check_call([sys.executable, "-m", "venv", self.venv_dir])

            # 2. Install dependencies
            self.progress_label.config(text="Installing dependencies (this may take a while)...")
            self.progress["value"] = 30
            self.log("Installing requirements.txt...")

            pip_exe = os.path.join(self.venv_dir, "Scripts", "pip.exe")
            req_file = os.path.join(self.project_dir, "requirements.txt")

            # Run pip and capture output
            process = subprocess.Popen(
                [pip_exe, "install", "-r", req_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

            while True:
                output = process.stdout.readline()
                if output == "" and process.poll() is not None:
                    break
                if output:
                    self.log(output.strip())

            if process.returncode != 0:
                raise Exception("Pip install failed")

            # 3. Startup Shortcut
            self.progress["value"] = 80
            if self.startup_var.get():
                self.progress_label.config(text="Configuring startup...")
                self.log("Creating startup shortcut...")
                self.create_shortcut()
            else:
                self.log("Skipping startup shortcut.")

            # 4. Launch
            self.progress["value"] = 100
            self.progress_label.config(text="Installation Complete!")
            self.log("Done!")

            self.launch_app()
            self.show_instructions()

        except Exception as e:
            self.log(f"Error: {str(e)}")
            messagebox.showerror("Error", f"Installation failed:\n{str(e)}")
            self.install_btn.config(state="normal", text="Retry Install")

    def center_window(self, width, height):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def show_instructions(self):
        # Clear existing widgets
        for widget in self.winfo_children():
            widget.destroy()

        self.center_window(800, 600)

        # Header
        header = tk.Frame(self, bg=HEADER_BG, pady=15)
        header.pack(fill="x")
        tk.Label(
            header,
            text="🎉 Installation Complete!",
            font=("Segoe UI", 18, "bold"),
            bg=HEADER_BG,
            fg=ACCENT,
        ).pack()

        # Content Scrollable
        canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=BG, padx=20, pady=20)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        # Center the frame inside the canvas
        window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        def on_canvas_configure(event):
            canvas.itemconfig(window_id, width=event.width)

        canvas.bind("<Configure>", on_canvas_configure)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Helper for sections
        def add_section(title, content):
            tk.Label(
                scrollable_frame,
                text=title,
                font=("Segoe UI", 14, "bold"),
                bg=BG,
                fg=ACCENT,
                anchor="center",
            ).pack(fill="x", pady=(15, 5))

            tk.Label(
                scrollable_frame,
                text=content,
                font=("Segoe UI", 10),
                bg=BG,
                fg=FG,
                justify="center",
                anchor="center",
            ).pack(fill="x")

        # 1. Desktop App
        add_section(
            "🖥️ Desktop Application (Quick Add)",
            "• Use Ctrl+Alt+A to open the Quick Add widget anywhere.\n"
            "• Add Tab: Quickly save new commands without breaking flow.\n"
            "• Search Tab: Type to find commands, Enter to run, or Double-click to copy.\n"
            "• Cards Tab: Visual grid view of your commands.",
        )

        # 2. Visual Dashboard
        add_section(
            "📊 Visual Dashboard (Ctrl+Alt+V)",
            "• Edit Database: Spreadsheet view to manage all commands. Edits auto-save.\n"
            "• Card View: Visual grid of your commands grouped by software.\n"
            "• Auto-Tagger: Bulk organize imported commands using smart rules.",
        )

        # 3. Command Harvester
        add_section(
            "🕷️ Command Harvester (Ctrl+Alt+H)",
            "• Paste a URL containing tables of shortcuts (e.g., documentation).\n"
            "• Select tables to import.\n"
            "• Map columns (Command & Description) to scrape data instantly.\n"
            "• Note: Works best on standard HTML tables.",
        )

        # 4. Developers
        add_section(
            "👨‍💻 For Developers",
            "• See README.md for details on the Virtual Environment (.venv).\n"
            "• Check 'requirements-dev.txt' for linting and testing tools.\n"
            "• Use 'cmdsearch.bat' for a lightweight CLI database manager.",
        )

        # Close Button
        tk.Button(
            scrollable_frame,
            text="Close & Start Using",
            command=self.quit,
            bg=ACCENT,
            fg="black",
            font=("Segoe UI", 11, "bold"),
            padx=20,
            pady=10,
            relief="flat",
            cursor="hand2",
        ).pack(pady=30)

    def create_shortcut(self):
        startup_folder = os.path.join(
            os.getenv("APPDATA"), "Microsoft", "Windows", "Start Menu", "Programs", "Startup"
        )
        shortcut_path = os.path.join(startup_folder, "CommandDBQuickAdd.lnk")
        target_script = os.path.join(self.project_dir, "scripts", "quickadd_startup.bat")

        # PowerShell command to create shortcut
        ps_cmd = (
            f"$ws = New-Object -ComObject WScript.Shell; "
            f"$s = $ws.CreateShortcut('{shortcut_path}'); "
            f"$s.TargetPath = '{target_script}'; "
            f"$s.WorkingDirectory = '{self.project_dir}'; "
            f"$s.Save()"
        )

        subprocess.check_call(
            ["powershell", "-Command", ps_cmd], creationflags=subprocess.CREATE_NO_WINDOW
        )

    def launch_app(self):
        pythonw = os.path.join(self.venv_dir, "Scripts", "pythonw.exe")
        app_script = os.path.join(self.project_dir, "src", "quick_add.py")
        subprocess.Popen([pythonw, app_script], cwd=self.project_dir)


if __name__ == "__main__":
    app = Installer()
    app.mainloop()
