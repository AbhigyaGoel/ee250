"""Tests for dashboard/app.py — DB functions and Flask routes."""

import sys
import os
import sqlite3
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dashboard"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pi"))

import pytest


class TestDatabase:
    """Test SQLite DB functions with a temp database."""

    def setup_method(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.db_path = self.tmp.name

        # Patch DB_PATH before importing
        import app as dashboard_app
        self._orig_db_path = dashboard_app.DB_PATH
        dashboard_app.DB_PATH = self.db_path
        self.app_module = dashboard_app

        self.app_module.init_db()

    def teardown_method(self):
        self.app_module.DB_PATH = self._orig_db_path
        os.unlink(self.db_path)

    def test_init_db_creates_table(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='messages'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_save_and_get_message(self):
        self.app_module.save_message("A", "S", 0.95, "S")
        messages = self.app_module.get_recent_messages(10)
        assert len(messages) == 1
        assert messages[0]["node"] == "A"
        assert messages[0]["character"] == "S"
        assert messages[0]["confidence"] == 0.95
        assert messages[0]["message_so_far"] == "S"

    def test_get_recent_respects_limit(self):
        for i in range(20):
            self.app_module.save_message("A", chr(65 + i % 26), 0.9, "msg")
        messages = self.app_module.get_recent_messages(5)
        assert len(messages) == 5

    def test_get_recent_returns_chronological_order(self):
        self.app_module.save_message("A", "X", 0.9, "X")
        self.app_module.save_message("A", "Y", 0.8, "XY")
        self.app_module.save_message("A", "Z", 0.7, "XYZ")
        messages = self.app_module.get_recent_messages(10)
        chars = [m["character"] for m in messages]
        assert chars == ["X", "Y", "Z"]

    def test_save_message_with_special_chars(self):
        self.app_module.save_message("B", " ", 0.85, "HI ")
        messages = self.app_module.get_recent_messages(10)
        assert messages[0]["character"] == " "

    def test_init_db_idempotent(self):
        """Calling init_db twice shouldn't error."""
        self.app_module.init_db()
        self.app_module.init_db()
        messages = self.app_module.get_recent_messages(10)
        assert isinstance(messages, list)

    def test_empty_db_returns_empty_list(self):
        messages = self.app_module.get_recent_messages(10)
        assert messages == []


class TestFlaskRoutes:
    """Test Flask route responses."""

    def setup_method(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()

        import app as dashboard_app
        self._orig_db_path = dashboard_app.DB_PATH
        dashboard_app.DB_PATH = self.tmp.name
        dashboard_app.init_db()
        self.app_module = dashboard_app
        self.client = dashboard_app.app.test_client()

    def teardown_method(self):
        self.app_module.DB_PATH = self._orig_db_path
        os.unlink(self.tmp.name)

    def test_index_returns_200(self):
        response = self.client.get("/")
        assert response.status_code == 200

    def test_index_contains_title(self):
        response = self.client.get("/")
        assert b"Morse" in response.data and b"Pager" in response.data

    def test_api_messages_returns_json(self):
        response = self.client.get("/api/messages")
        assert response.status_code == 200
        import json
        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_api_messages_with_data(self):
        self.app_module.save_message("A", "H", 0.99, "H")
        response = self.client.get("/api/messages")
        import json
        data = json.loads(response.data)
        assert len(data) == 1
        assert data[0]["character"] == "H"
