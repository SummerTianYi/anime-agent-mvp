"""Codex: adversarial checks of audit tooling only; no live DB/service."""
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from probe import copy_stable_sqlite


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='audit-probe-selftest-')
        root = Path(self.temp.name)
        self.source, self.dest = root/'source.db', root/'copy.db'
        self.source.write_bytes(b'A')
        self.addCleanup(self.temp.cleanup)

    def test_unchanged_files_with_wal_are_verified(self):
        Path(str(self.source)+'-wal').write_bytes(b'WAL')
        result = copy_stable_sqlite(self.source,self.dest)
        self.assertEqual(result['source_before'],result['copy'])
        self.assertEqual(result['source_after'],result['copy'])

    def test_late_wal_is_rejected(self):
        original = shutil.copyfile
        def copy(src,dst):
            original(src,dst)
            Path(str(self.source)+'-wal').write_bytes(b'LATE')
        with patch('probe.shutil.copyfile',side_effect=copy):
            with self.assertRaises(RuntimeError):
                copy_stable_sqlite(self.source,self.dest)

    def test_different_copy_despite_matching_source_scans_is_rejected(self):
        def copy(src,dst):
            self.source.write_bytes(b'B')
            Path(dst).write_bytes(self.source.read_bytes())
            self.source.write_bytes(b'A')
        with patch('probe.shutil.copyfile',side_effect=copy):
            with self.assertRaises(RuntimeError):
                copy_stable_sqlite(self.source,self.dest)

    def test_deleted_wal_is_rejected(self):
        wal=Path(str(self.source)+'-wal');wal.write_bytes(b'WAL')
        original=shutil.copyfile
        def copy(src,dst):
            original(src,dst)
            if str(src).endswith('-wal'): wal.unlink()
        with patch('probe.shutil.copyfile',side_effect=copy):
            with self.assertRaises(RuntimeError):
                copy_stable_sqlite(self.source,self.dest)

    def test_malformed_timestamp_does_not_pass_date_filter(self):
        with sqlite3.connect(':memory:') as db:
            actual=db.execute("SELECT julianday(?)>=julianday(?)",('avatar-chat-1735379','2026-10-07 11:01:00')).fetchone()[0]
            self.assertIsNone(actual)


if __name__=='__main__':
    unittest.main(verbosity=2)
