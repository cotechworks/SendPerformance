"""診断経路と取得失敗ログを検証する。"""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import SendPerformance as app
import disk_diagnostics


class DiagnosticTests(unittest.TestCase):
    def test_diagnostic_uses_disk_in_third_column_without_real_port(self):
        lines = []
        with patch.object(app.psutil, 'cpu_percent', return_value=10), \
             patch.object(app.psutil, 'virtual_memory', return_value=SimpleNamespace(percent=20)), \
             patch.object(app.SendPerformance, 'getGpuUsage', return_value=30), \
             patch.object(app.SendPerformance, 'getDiskUsage', return_value=80):
            result = disk_diagnostics.diagnose_disk(samples=2, output=lines.append)
        self.assertEqual(result, 0)
        self.assertEqual(len(lines), 3)
        self.assertTrue(all('10,20,80' in line for line in lines[1:]))

    def test_disk_failure_is_recorded_when_debug_logging_enabled(self):
        with patch.object(app.subprocess, 'run', side_effect=OSError('denied')), \
             self.assertLogs(level='DEBUG') as logs:
            self.assertEqual(app.SendPerformance.getDiskUsage(), 0)
        self.assertIn('disk acquisition failed', '\n'.join(logs.output))