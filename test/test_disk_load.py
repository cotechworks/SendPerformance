"""負荷スクリプトの上限と後片付けを小容量で検証する。"""
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import disk_load


class DiskLoadTests(unittest.TestCase):
    def test_small_load_preserves_existing_files_and_removes_scratch(self):
        with tempfile.TemporaryDirectory() as directory:
            existing = Path(directory) / 'existing.txt'
            existing.write_bytes(b'keep')
            with contextlib.redirect_stdout(io.StringIO()):
                result = disk_load.run_load(directory, seconds=0.2, size_mib=1, max_write_mib=1)
            self.assertGreater(result['written_bytes'], 0)
            self.assertLessEqual(result['written_bytes'], disk_load.MIB)
            self.assertEqual(existing.read_bytes(), b'keep')
            self.assertEqual(list(Path(directory).iterdir()), [existing])

    def test_invalid_limits_do_not_create_files(self):
        with tempfile.TemporaryDirectory() as directory:
            for params in [
                dict(seconds=0), dict(seconds=float('nan')), dict(size_mib=0),
                dict(seconds=3601), dict(size_mib=4097), dict(size_mib=2, max_write_mib=1),
            ]:
                with self.subTest(params=params), self.assertRaises(ValueError):
                    disk_load.run_load(directory, **params)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_insufficient_space_does_not_create_files(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
            disk_load.shutil, 'disk_usage', return_value=type('Space', (), {'free': 0})(),
        ):
            with self.assertRaises(ValueError):
                disk_load.run_load(directory)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_io_error_cleans_up(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()), \
             patch.object(disk_load.os, 'fsync', side_effect=OSError('test error')):
            with self.assertRaises(OSError):
                disk_load.run_load(directory, seconds=1, size_mib=1, max_write_mib=1)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_ctrl_c_cleans_up(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()), \
             patch.object(disk_load.os, 'fsync', side_effect=KeyboardInterrupt):
            result = disk_load.run_load(directory, seconds=1, size_mib=1, max_write_mib=1)
            self.assertTrue(result['interrupted'])
            self.assertEqual(list(Path(directory).iterdir()), [])