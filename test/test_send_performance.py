"""Windows上で実行する開発側テスト。実機COMポートは開かない。"""
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import SendPerformance as app
import serial


class PerformanceTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.settings_path = Path(folder.name) / 'setting.json'

    def make_instance(self):
        with patch.object(app, 'Icon') as icon:
            obj = app.SendPerformance(ROOT / 'icon.png', settings_path=self.settings_path)
        self.addCleanup(icon.call_args.kwargs['icon'].close)
        self.addCleanup(obj.serial.close)
        return obj

    def test_default_port_and_png(self):
        obj = self.make_instance()
        self.assertEqual(obj.serial.port, 'COM15')
        self.assertEqual(obj.serial.baudrate, 115200)
        self.assertFalse(obj.serial.is_open)

    def test_task_loopback_csv_crlf(self):
        obj = self.make_instance()
        obj.serial = serial.serial_for_url('loop://', timeout=1)
        self.addCleanup(obj.serial.close)
        with patch.object(app.psutil, 'cpu_percent', return_value=12.5), \
             patch.object(app.psutil, 'virtual_memory', return_value=SimpleNamespace(percent=34.5)), \
             patch.object(obj, 'getGpuUsage', return_value=56.5):
            obj.doTask()
        self.assertEqual(obj.serial.readline(), b'12.5,34.5,56.5\r\n')
        self.assertEqual(obj.serial.in_waiting, 0)

    def test_gpu_failure_is_transmitted_as_zero(self):
        obj = self.make_instance()
        obj.serial = serial.serial_for_url('loop://', timeout=1)
        self.addCleanup(obj.serial.close)
        with patch.object(app.psutil, 'cpu_percent', return_value=10), \
             patch.object(app.psutil, 'virtual_memory', return_value=SimpleNamespace(percent=20)), \
             patch.object(app.subprocess, 'run', side_effect=OSError('unavailable')):
            obj.doTask()
        self.assertEqual(obj.serial.readline(), b'10,20,0\r\n')

    def test_gpu_values_and_bounds(self):
        for value, expected in [('42.5', 42.5), (' 12\r\n', 12), ('-5', 0), ('120', 100)]:
            with self.subTest(value=value), patch.object(
                app.subprocess, 'run',
                return_value=subprocess.CompletedProcess([], 0, value),
            ):
                self.assertEqual(app.SendPerformance.getGpuUsage(), expected)

    def test_gpu_errors_return_zero(self):
        errors = [
            OSError('missing command'),
            subprocess.CalledProcessError(1, 'powershell.exe'),
            subprocess.TimeoutExpired('powershell.exe', 5),
        ]
        for error in errors:
            with self.subTest(error=type(error).__name__), patch.object(
                app.subprocess, 'run', side_effect=error,
            ):
                self.assertEqual(app.SendPerformance.getGpuUsage(), 0)

    def test_gpu_invalid_output_returns_zero(self):
        for value in ['', 'not a number']:
            with self.subTest(value=value), patch.object(
                app.subprocess, 'run',
                return_value=subprocess.CompletedProcess([], 0, value),
            ):
                self.assertEqual(app.SendPerformance.getGpuUsage(), 0)

    def test_gpu_aggregation_with_powershell_fixture(self):
        # 実際のPowerShellを使い、CIM問い合わせだけを固定データに差し替える。
        original_run = subprocess.run
        fixture = """
function Get-CimInstance {
    [pscustomobject]@{Name='pid_10_luid_A_phys_0_eng_0_engtype_3D'; UtilizationPercentage=30}
    [pscustomobject]@{Name='pid_20_luid_A_phys_0_eng_0_engtype_3D'; UtilizationPercentage=40}
    [pscustomobject]@{Name='pid_30_luid_A_phys_0_eng_1_engtype_Copy'; UtilizationPercentage=60}
}
"""
        def run_fixture(args, **kwargs):
            args = list(args)
            args[-1] = fixture + args[-1]
            kwargs['timeout'] = 15
            return original_run(args, **kwargs)
        with patch.object(app.subprocess, 'run', side_effect=run_fixture):
            self.assertEqual(app.SendPerformance.getGpuUsage(), 70)

    def test_menu_config_and_exit_callbacks(self):
        # Iconの生成引数から、実際のMenuItemに登録されたコールバックを呼ぶ。
        with patch.object(app, 'Icon') as icon:
            obj = app.SendPerformance(ROOT / 'icon.png', settings_path=self.settings_path)
        self.addCleanup(obj.serial.close)
        self.addCleanup(icon.call_args.kwargs['icon'].close)
        items = list(icon.call_args.kwargs['menu'].items)
        self.assertEqual([item.text for item in items], ['Config', 'Exit'])
        obj.status = True
        items[0](obj.icon)
        self.assertTrue(obj.config_requested.is_set())
        items[1](obj.icon)
        self.assertFalse(obj.status)
        obj.icon.stop.assert_called_once()

    def test_program_closes_port_after_normal_exit(self):
        self.check_shutdown(False)

    def test_program_closes_port_after_tray_exception(self):
        self.check_shutdown(True)

    def check_shutdown(self, fail):
        obj = self.make_instance()
        obj.serial = Mock()
        worker_started = threading.Event()
        worker_finished = threading.Event()
        release_worker = threading.Event()
        def worker():
            worker_started.set()
            release_worker.wait(3)
            worker_finished.set()
        obj.runSchedule = worker
        def tray():
            self.assertTrue(worker_started.wait(2))
            release_worker.set()
            if fail:
                raise RuntimeError('tray failed')
        gui = patch.object(app, 'run_config_loop', side_effect=lambda *args: tray())
        gui.start()
        self.addCleanup(gui.stop)
        obj.serial.close.side_effect = lambda: self.assertTrue(worker_finished.is_set())
        if fail:
            with self.assertRaisesRegex(RuntimeError, 'tray failed'):
                obj.runProgram()
        else:
            obj.runProgram()
        self.assertFalse(obj.status)
        obj.serial.open.assert_called_once()
        obj.serial.close.assert_called_once()

    def test_schedule_runs_task(self):
        obj = self.make_instance()
        scheduler = app.schedule.Scheduler()
        obj.status = True
        def task():
            obj.status = False
        obj.doTask = Mock(side_effect=task)
        with patch.object(app, 'schedule', scheduler):
            runner = threading.Thread(target=obj.runSchedule)
            runner.start()
            runner.join(3)
            if runner.is_alive():
                obj.status = False
                runner.join(1)
                self.fail('scheduler did not stop')
        obj.doTask.assert_called_once()


    def test_output_reordering_and_duplicates(self):
        obj = self.make_instance()
        obj.serial = serial.serial_for_url('loop://', timeout=1)
        self.addCleanup(obj.serial.close)
        with patch.object(app.psutil, 'cpu_percent', return_value=10), \
             patch.object(app.psutil, 'virtual_memory', return_value=SimpleNamespace(percent=20)), \
             patch.object(obj, 'getGpuUsage', return_value=30):
            for outputs, expected in [
                (('GPU', 'CPU', 'メモリ'), b'30,10,20\r\n'),
                (('メモリ', 'メモリ', 'CPU'), b'20,20,10\r\n'),
            ]:
                obj.setOutputs(outputs)
                obj.doTask()
                self.assertEqual(obj.serial.readline(), expected)

    def test_invalid_output_preserves_previous_setting(self):
        obj = self.make_instance()
        for outputs in [(), ('CPU',), ('CPU', 'GPU', 'メモリ', 'CPU'), ('CPU', 'unknown', 'GPU')]:
            with self.subTest(outputs=outputs):
                with self.assertRaises(ValueError):
                    obj.setOutputs(outputs)
                self.assertEqual(obj.outputs, ('CPU', 'メモリ', 'GPU'))

    def test_setting_change_during_measurement_is_atomic(self):
        obj = self.make_instance()
        obj.serial = serial.serial_for_url('loop://', timeout=1)
        self.addCleanup(obj.serial.close)
        def cpu(**kwargs):
            obj.setOutputs(('GPU', 'GPU', 'GPU'))
            return 10
        with patch.object(app.psutil, 'cpu_percent', side_effect=cpu), \
             patch.object(app.psutil, 'virtual_memory', return_value=SimpleNamespace(percent=20)), \
             patch.object(obj, 'getGpuUsage', return_value=30):
            obj.doTask()
            self.assertEqual(obj.serial.readline(), b'10,20,30\r\n')
            obj.doTask()
            self.assertEqual(obj.serial.readline(), b'30,30,30\r\n')

    def test_config_requests_are_coalesced(self):
        obj = self.make_instance()
        obj.showConfig()
        obj.showConfig()
        self.assertTrue(obj.config_requested.is_set())
        self.assertEqual(obj.getOutputs(), ('CPU', 'メモリ', 'GPU'))

    def test_config_cannot_open_after_exit(self):
        obj = self.make_instance()
        obj.stopProgram(obj.icon)
        obj.showConfig()
        self.assertFalse(obj.config_requested.is_set())

    def test_exit_signals_config_loop(self):
        obj = self.make_instance()
        obj.stopProgram(obj.icon)
        self.assertTrue(obj.config_stop.is_set())


class ExecutableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.exe = ROOT / 'dist' / 'SendPerformance.dist' / 'SendPerformance.exe'
        if cls.exe.exists() and cls.exe.stat().st_mtime < max(
            (ROOT / 'SendPerformance.py').stat().st_mtime,
            (ROOT / 'src' / 'config_dialog.py').stat().st_mtime,
            (ROOT / 'src' / 'disk_diagnostics.py').stat().st_mtime,
            (ROOT / 'src' / '__init__.py').stat().st_mtime,
            (ROOT / 'src' / 'settings.py').stat().st_mtime,
            (ROOT / 'Build.bat').stat().st_mtime,
        ):
            raise unittest.SkipTest('exeがソースより古い。再ビルド後に確認する')
        if not cls.exe.exists():
            raise unittest.SkipTest('exe未作成。Build.batを実行してから再テストする')

    def test_bundled_png_matches_source(self):
        self.assertEqual(self.exe.with_name('icon.png').read_bytes(), (ROOT / 'icon.png').read_bytes())

    def test_help_from_other_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([str(self.exe), '--help'], cwd=directory, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, repr(result.stderr))
        self.assertIn(b'--port', result.stdout)
        self.assertIn(b'--baudrate', result.stdout)



if __name__ == '__main__':
    unittest.main()