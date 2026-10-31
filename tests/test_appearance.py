"""Appearance persistence must remain independent of radio settings."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from dxtalker.appearance import load_appearance, save_appearance
from dxtalker.models import Settings, save_settings


class AppearanceTests(unittest.TestCase):
    def test_theme_roundtrip_preserves_radio_profile(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, LOCALAPPDATA=folder):
            radio = Path(folder) / 'DXTalker/settings.json'
            save_settings(Settings(cw_text='KF4DBX'))
            original = radio.read_bytes()
            for theme in ('Light', 'Dark'):
                save_appearance(theme)
                self.assertEqual(load_appearance(), theme)
                self.assertEqual(radio.read_bytes(), original)

    def test_missing_or_damaged_appearance_uses_dark_without_overwriting(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, LOCALAPPDATA=folder):
            self.assertEqual(load_appearance(), 'Dark')
            path = Path(folder) / 'DXTalker/appearance.json'
            path.parent.mkdir()
            for text in ('broken', 'null', '[]', '{}', '{"theme": []}', '{"theme": "unknown"}'):
                path.write_text(text)
                self.assertEqual(load_appearance(), 'Dark')
                self.assertEqual(path.read_text(), text)
