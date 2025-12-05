import subprocess
import time

import keyboard

try:
    import pygetwindow as gw
except ImportError:
    gw = None

PLACEHOLDERS = ["{1}", "{arg}", "%1%", "%arg%"]


def get_icon(software):
    software = software.lower()
    if "windows" in software:
        return "🪟"
    if "code" in software or "vs" in software:
        return "👨‍💻"
    if "chrome" in software or "browser" in software:
        return "🌐"
    if "git" in software:
        return "🐙"
    if "terminal" in software or "cmd" in software:
        return "💻"
    if "obsidian" in software:
        return "📓"
    return "⚡"


def resolve_command(cmd, arg=None):
    if not arg:
        return cmd
    for p in PLACEHOLDERS:
        cmd = cmd.replace(p, arg)
    return cmd


def run_command_locally(cmd):
    # Check for workflow
    if ";;" in cmd:
        return run_workflow(cmd)

    try:
        subprocess.Popen(cmd, shell=True)
        return True
    except Exception as e:
        print(f"Error running command: {e}")
        return False


def run_workflow(workflow_str):
    steps = workflow_str.split(";;")

    for step in steps:
        step = step.strip()
        if not step:
            continue

        try:
            # 1. WAIT
            if step.upper().startswith("WAIT "):
                try:
                    sec = float(step[5:].strip())
                    time.sleep(sec)
                except ValueError:
                    pass

            # 2. CMD (Explicit Command)
            elif step.upper().startswith("CMD "):
                run_command_locally(step[4:].strip())

            # 3. TYPE (Explicit Text)
            elif step.upper().startswith("TYPE "):
                keyboard.write(step[5:].strip())

            # 4. Default (Try Hotkey, then Text)
            else:
                # Heuristic: If it contains spaces and isn't a known hotkey combo, type it?
                # Actually, "ctrl+alt+del" has no spaces. "win+r" has no spaces.
                # "Hello World" has spaces.
                if " " in step and not any(
                    k in step.lower() for k in ["ctrl", "alt", "shift", "win"]
                ):
                    keyboard.write(step)
                else:
                    try:
                        keyboard.send(step)
                    except ValueError:
                        # If hotkey fails, fallback to write
                        keyboard.write(step)

        except Exception:
            pass

    return True


def run_hotkey(keys, software="General"):
    # Give time for the QuickAdd window to close and focus to return
    time.sleep(0.3)

    # Try to focus the window if software is specified (skip Windows OS)
    if software and software not in ["General", "Windows"] and gw:
        try:
            windows = gw.getWindowsWithTitle(software)
            if windows:
                win = windows[0]
                if not win.isActive:
                    win.activate()
                    time.sleep(0.2)
        except Exception:
            pass

    # Check for workflow or sequence
    if ";;" in keys:
        return run_workflow(keys)

    # Handle sequence notation (e.g. "win + x > A")
    if ">" in keys:
        parts = keys.split(">")
        # Convert to workflow: part1 ;; WAIT 0.5 ;; part2 ...
        workflow = " ;; WAIT 0.5 ;; ".join([p.strip() for p in parts])
        return run_workflow(workflow)

    try:
        # Parse keys like "ctrl+c"
        keyboard.send(keys)
        return True
    except Exception as e:
        print(f"Error sending keys: {e}")
        return False
