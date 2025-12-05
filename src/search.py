"""Interactive search and small CLI for editing `commands.json`."""

import json
import os
import shutil
from datetime import datetime

# --- CONFIGURATION ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(PROJECT_ROOT, "data", "commands.json")
BACKUP_DIR = os.path.join(PROJECT_ROOT, "data", "backups")


class Style:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def load_data():
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def create_backup():
    if not os.path.exists(DB_FILE):
        return
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(BACKUP_DIR, f"commands_backup_{timestamp}.json")
    try:
        shutil.copy(DB_FILE, dest)
        print(f"{Style.YELLOW}>> Backup created: {os.path.basename(dest)}{Style.RESET}")
    except Exception as e:
        print(f"{Style.RED}Backup failed: {e}{Style.RESET}")


def save_data(data):
    create_backup()
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print(f"\n{Style.GREEN}Database updated successfully.{Style.RESET}")
    except Exception as e:
        print(f"{Style.RED}Error saving file: {e}{Style.RESET}")


def get_input(prompt_text):
    try:
        user_input = input(prompt_text).strip()
    except (EOFError, KeyboardInterrupt):
        return None
    if user_input.lower() in ("$c", "$cancel", "$back", "$exit"):
        print(f"{Style.RED}>> Operation cancelled.{Style.RESET}")
        return None
    return user_input


def print_help():
    print(f"\n{Style.HEADER}{Style.BOLD}--- AVAILABLE COMMANDS ---{Style.RESET}")
    print(f"{Style.BOLD}{'Action':<15} {'Command':<15} {'Aliases'}{Style.RESET}")
    print(f"{'-'*50}")
    print(f"{'Add Entry':<15} {Style.GREEN}$add{Style.RESET}{'':<10} $new, $create, $a")
    print(f"{'Delete Entry':<15} {Style.RED}$del{Style.RESET}{'':<11} $delete, $rm, $kill")
    print(f"{'Clear Screen':<15} {Style.CYAN}$clear{Style.RESET}{'':<9} $cls, $clean")
    print(f"{'Show Help':<15} {Style.YELLOW}$help{Style.RESET}{'':<10} $h, $?, $info")
    print(f"{'Quit Tool':<15} {Style.BLUE}$quit{Style.RESET}{'':<10} $exit, $q, $bye")
    print(f"\n{Style.BOLD}Search:{Style.RESET} Type any text to search (e.g., 'git')")


def add_command():
    print(f"\n{Style.HEADER}--- ADD NEW COMMAND (Type '$c' to cancel) ---{Style.RESET}")
    cmd = get_input(f"{Style.BOLD}Command: {Style.RESET}")
    if cmd is None:
        return
    desc = get_input(f"{Style.BOLD}Description: {Style.RESET}")
    if desc is None:
        return
    soft = get_input(f"{Style.BOLD}Software/OS: {Style.RESET}")
    if soft is None:
        return
    cat = get_input(f"{Style.BOLD}Category (Hotkey, Run, CMD): {Style.RESET}")
    if cat is None:
        return
    tags_input = get_input(f"{Style.BOLD}Tags (comma separated): {Style.RESET}")
    if tags_input is None:
        return
    tags_list = [t.strip() for t in tags_input.split(",") if t.strip()]
    new_entry = {
        "command": cmd,
        "description": desc,
        "software": soft,
        "category": cat,
        "tags": tags_list,
    }
    data = load_data()
    data.append(new_entry)
    save_data(data)


def delete_command():
    print(f"\n{Style.RED}--- DELETE MODE (Type '$c' to cancel) ---{Style.RESET}")
    search_query = get_input("Search for command to delete: ")
    if search_query is None:
        return
    data = load_data()
    candidates = []
    for index, item in enumerate(data):
        software_field = item.get("software", "")
        tags = item.get("tags", [])
        searchable = (
            f"{item.get('command','')} {item.get('description','')} "
            f"{software_field} {' '.join(tags)}"
        ).lower()
        if search_query.lower() in searchable:
            candidates.append((index, item))
    if not candidates:
        print(f"{Style.YELLOW}No matches found.{Style.RESET}")
        return
    print(f"\n{Style.BOLD}Found these matches:{Style.RESET}")
    for i, (orig_idx, item) in enumerate(candidates):
        print(
            f"{Style.CYAN}[{i+1}]{Style.RESET} {item.get('command','')} -- "
            f"{item.get('description','')}"
        )
    choice = get_input(f"\n{Style.RED}Enter number to DELETE: {Style.RESET}")
    if choice is None:
        return
    try:
        choice_idx = int(choice) - 1
        if 0 <= choice_idx < len(candidates):
            real_index = candidates[choice_idx][0]
            item_to_kill = data[real_index]
            print(f"Deleting: {item_to_kill.get('command','')}...")
            del data[real_index]
            save_data(data)
        else:
            print("Invalid selection.")
    except ValueError:
        print("Invalid input.")


def search():
    clear_screen()
    print(f"{Style.HEADER}{Style.BOLD}=== COMMAND CENTER ==={Style.RESET}")
    print(f"{Style.CYAN}Type '$help' for commands, or just type to search.{Style.RESET}\n")
    while True:
        try:
            query = input(f"{Style.YELLOW}>> {Style.RESET}").lower().strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if not query:
            continue
        if query.startswith("$"):
            cmd = query[1:]
            if cmd in ["q", "quit", "exit", "bye"]:
                print("Goodbye!")
                break
            elif cmd in ["add", "new", "create", "a"]:
                add_command()
                continue
            elif cmd in ["del", "delete", "remove", "rm", "kill"]:
                delete_command()
                continue
            elif cmd in ["clear", "cls", "clean", "refresh"]:
                clear_screen()
                print_help()
                continue
            elif cmd in ["help", "h", "?", "info", "man"]:
                print_help()
                continue
            else:
                print(f"{Style.RED}Unknown command: {query}. Try $help{Style.RESET}")
                continue
        data = load_data()
        found = False
        print("")
        for item in data:
            software_field = item.get("software", "N/A")
            tags = item.get("tags", [])
            searchable = (
                f"{item.get('command','')} {item.get('description','')} "
                f"{software_field} {' '.join(tags)}"
            ).lower()
            if query in searchable:
                found = True
                print(f"{Style.BOLD}CMD:  {Style.GREEN}{item.get('command','')}{Style.RESET}")
                print(f"DESC: {item.get('description','')}")
                print(f"SOFT: {Style.YELLOW}{software_field}{Style.RESET}")
                print(f"TYPE: {Style.CYAN}[{item.get('category','')}] {Style.RESET}")
                print(f"TAGS: {', '.join(tags)}")
                print(f"{Style.BLUE}{'-'*40}{Style.RESET}")
        if not found:
            print(f"{Style.RED}No results found.{Style.RESET}")


if __name__ == "__main__":
    search()
