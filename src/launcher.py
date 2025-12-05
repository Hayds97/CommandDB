import importlib.util
import os
import subprocess
import sys
import time

# --- CONFIGURATION ---
# We now check for EVERY library the suite needs
REQUIRED_LIBS = [
    "keyboard",
    "pyperclip",
    "pyautogui",
    "pygetwindow",  # Quick Add
    "streamlit",
    "pandas",
    "requests",
    "lxml",
    "html5lib",
    "beautifulsoup4",  # Dashboard & Harvester
]
SERVICE_FILENAME = "quick_add.py"


def is_installed(package_name):
    return importlib.util.find_spec(package_name) is not None


def ensure_python_compatibility():
    """
    Ensures we are running on a compatible Python version (3.12).
    If 3.13+ is detected (which lacks some wheels), we try to restart with 'py -3.12'.
    """
    if sys.version_info >= (3, 13):
        print("⚠️  Python 3.13+ detected. Some libraries (Streamlit/Pandas) may not work yet.")
        print("🔄  Checking for Python 3.12...")

        try:
            # Check if py -3.12 exists
            subprocess.check_call(
                ["py", "-3.12", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

            print("✅  Python 3.12 found. Restarting launcher...")
            # Relaunch with 3.12
            subprocess.call(["py", "-3.12", __file__] + sys.argv[1:])
            sys.exit()
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(
                "❌  Python 3.12 not found. Continuing with current version "
                "(installation may fail)."
            )


def install_libs():
    print("--------------------------------------------------")
    print("⚙️  UPDATING COMMANDDB SUITE DEPENDENCIES")
    print("--------------------------------------------------")
    print("We detected missing libraries for the Dashboard/Harvester.")
    print("Installing now...\n")

    try:
        # Install all missing requirements
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", *REQUIRED_LIBS])
        print("\n✅ All libraries installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error installing libraries: {e}")
        input("Press Enter to exit...")
        return False


def check_startup_prompt():
    """
    Checks if the startup shortcut exists. If not, asks the user if they want to create it.
    """
    try:
        startup_folder = os.path.join(
            os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs", "Startup"
        )
        shortcut_path = os.path.join(startup_folder, "CommandDBQuickAdd.lnk")

        if not os.path.exists(shortcut_path):
            print("\n--------------------------------------------------")
            print("🚀 STARTUP CONFIGURATION")
            print("--------------------------------------------------")
            print("Would you like Command Manager to start automatically with Windows?")
            choice = (
                input("Type 'y' to install startup service, or Enter to skip: ").strip().lower()
            )

            if choice == "y":
                installer_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "INSTALL.bat"
                )
                if os.path.exists(installer_path):
                    # Run the batch file in a new window so its 'pause' doesn't block us
                    # too awkwardly, or just run it here. Since it has a UI, let's run it.
                    subprocess.call([installer_path], shell=True)
                else:
                    print("⚠️ Could not find install_service.bat")
    except Exception as e:
        print(f"Error checking startup config: {e}")


def main():
    # 0. Ensure Compatibility
    ensure_python_compatibility()

    # 1. Check/Install Dependencies (Visibly)
    missing = [lib for lib in REQUIRED_LIBS if not is_installed(lib)]
    if missing:
        success = install_libs()
        if not success:
            sys.exit()

    # 2. Check Startup Config
    check_startup_prompt()

    # 3. Launch the Service (Invisibly)
    # First, kill any old instances to be safe
    os.system("taskkill /F /IM pythonw.exe /T 2>nul")

    print(f"🚀 Starting {SERVICE_FILENAME} in the background...")
    pythonw_exe = sys.executable.replace("python.exe", "pythonw.exe")

    # Determine path to quick_add.py (it is in the same folder as this script)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    service_path = os.path.join(script_dir, SERVICE_FILENAME)

    try:
        subprocess.Popen([pythonw_exe, service_path], cwd=script_dir)
        print("✅ Service Started. You can close this window.")
        time.sleep(2)
    except Exception as e:
        print(f"❌ Failed to start service: {e}")
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()
