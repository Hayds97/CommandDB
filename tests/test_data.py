import json
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(PROJECT_ROOT, "data", "commands.json")


def test_commands_json_exists():
    assert os.path.exists(DB_FILE), "commands.json should exist in data/"


def test_commands_json_is_valid():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            data = json.load(f)
        assert isinstance(data, list), "commands.json should contain a list"
