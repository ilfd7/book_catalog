"""Тесты резервного копирования."""

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backup import create_backup, list_backups, restore_backup, _sha256


class TestBackup(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.db_path = self.test_dir / 'test.db'
        self.db_path.write_text('fake database content', encoding='utf-8')
        self.backup_dir = self.test_dir / 'backups'
        self.backup_dir.mkdir()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_sha256(self):
        h = _sha256(self.db_path)
        self.assertEqual(len(h), 64)

    def test_create_backup(self):
        backup_path = create_backup(self.db_path, self.backup_dir)
        self.assertTrue(backup_path.exists())
        self.assertTrue(backup_path.name.startswith('backup_'))

    def test_list_backups_empty(self):
        backups = list_backups(self.backup_dir)
        self.assertEqual(backups, [])

    def test_list_backups(self):
        create_backup(self.db_path, self.backup_dir)
        backups = list_backups(self.backup_dir)
        self.assertEqual(len(backups), 1)

    def test_restore_backup(self):
        backup_path = create_backup(self.db_path, self.backup_dir)
        original_content = self.db_path.read_text()
        self.db_path.write_text('corrupted', encoding='utf-8')
        restore_backup(backup_path, self.db_path)
        self.assertEqual(self.db_path.read_text(), original_content)

    def test_restore_nonexistent(self):
        with self.assertRaises(FileNotFoundError):
            restore_backup(Path('/nonexistent/backup.zip'), self.db_path)


if __name__ == '__main__':
    unittest.main()