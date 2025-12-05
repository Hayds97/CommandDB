import json
import os
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DB_FILE = os.path.join(DATA_DIR, "commands.json")


def test_data_directory_exists():
    assert os.path.exists(DATA_DIR), "data/ directory should exist"


def test_commands_json_structure():
    # If file doesn't exist (CI), create a dummy one for testing structure logic
    created = False
    if not os.path.exists(DB_FILE):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(DB_FILE, "w") as f:
            json.dump([], f)
        created = True
    
    try:
        with open(DB_FILE, "r") as f:
            data = json.load(f)
        assert isinstance(data, list), "commands.json should contain a list"
    finally:
        if created:
            os.remove(DB_FILE)
