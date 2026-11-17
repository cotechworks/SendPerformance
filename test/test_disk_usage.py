"""ディスクアクティブ時間の取得・範囲・3列送信を検証する。"""
import subprocess
import tempfile
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import SendPerformance as app
import serial


class DiskTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.settings_path = Path(folder.name) / 'setting.json'

    def test_values_are_clamped(self):
        for value, expected in [('0', 0), ('42.5', 42.5), ('100', 100), ('-8', 0), ('120', 100)]:
            with self.subTest(value=value), patch.object(
                app.subprocess, 'run',
                return_value=subprocess.CompletedProcess([], 0, value),
            ):
                self.assertEqual(app.SendPerformance.getDiskUsage(), expected)

    def test_errors_return_zero(self):
        for error in [OSError('missing'), subprocess.CalledProcessError(1, 'powershell'),
                      subprocess.TimeoutExpired('powershell', 5)]:
            with self.subTest(error=type(error).__name__), patch.object(
                app.subprocess, 'run', side_effect=error,
            ):
                self.assertEqual(app.SendPerformance.getDiskUsage(), 0)

    def test_invalid_output_returns_zero(self):
        for value in ['', 'invalid']:
            with self.subTest(value=value), patch.object(
                app.subprocess, 'run',
                return_value=subprocess.CompletedProcess([], 0, value),
            ):
                self.assertEqual(app.SendPerformance.getDiskUsage(), 0)

    def test_real_powershell_uses_busiest_disk_and_excludes_total(self):
        original = subprocess.run
        fixture = """
function Get-CimInstance {
    [pscustomobject]@{Name='_Total'; PercentIdleTime=0}
    [pscustomobject]@{Name='0 C:'; PercentIdleTime=80}
    [pscustomobject]@{Name='1 D:'; PercentIdleTime=25}
    [pscustomobject]@{Name='2 E:'; PercentIdleTime=$null}
}
"""
        def run(args, **kwargs):
            args = list(args)
            args[-1] = fixture + args[-1]
            kwargs['timeout'] = 15
            return original(args, **kwargs)
        with patch.object(app.subprocess, 'run', side_effect=run):
            self.assertEqual(app.SendPerformance.getDiskUsage(), 75)

    def test_real_powershell_no_disk_returns_zero(self):
        original = subprocess.run
        def run(args, **kwargs):
            args = list(args)
            args[-1] = 'function Get-CimInstance {}\n' + args[-1]
            kwargs['timeout'] = 15
            return original(args, **kwargs)
        with patch.object(app.subprocess, 'run', side_effect=run):
            self.assertEqual(app.SendPerformance.getDiskUsage(), 0)

    def make_instance(self):
        with patch.object(app, 'Icon') as icon:
            obj = app.SendPerformance(Path(__file__).resolve().parents[1] / 'icon.png', settings_path=self.settings_path)
        self.addCleanup(icon.call_args.kwargs['icon'].close)
        self.addCleanup(obj.serial.close)
        return obj

    def test_selection_and_duplicates_send_three_columns(self):
        obj = self.make_instance()
        obj.serial = serial.serial_for_url('loop://', timeout=1)
        self.addCleanup(obj.serial.close)
        obj.setOutputs(('ディスクのアクティブ時間', 'CPU', 'ディスクのアクティブ時間'))
        with patch.object(app.psutil, 'cpu_percent', return_value=10), \
             patch.object(app.psutil, 'virtual_memory', return_value=SimpleNamespace(percent=20)), \
             patch.object(obj, 'getGpuUsage', return_value=30), \
             patch.object(obj, 'getDiskUsage', return_value=75) as disk:
            obj.doTask()
        self.assertEqual(obj.serial.readline(), b'75,10,75\r\n')
        disk.assert_called_once()

    def test_unselected_disk_is_not_queried(self):
        obj = self.make_instance()
        obj.serial = serial.serial_for_url('loop://', timeout=1)
        self.addCleanup(obj.serial.close)
        with patch.object(app.psutil, 'cpu_percent', return_value=10), \
             patch.object(app.psutil, 'virtual_memory', return_value=SimpleNamespace(percent=20)), \
             patch.object(obj, 'getGpuUsage', return_value=30), \
             patch.object(obj, 'getDiskUsage') as disk:
            obj.doTask()
        self.assertEqual(obj.serial.readline(), b'10,20,30\r\n')
        disk.assert_not_called()