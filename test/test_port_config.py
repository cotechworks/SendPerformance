"""COM設定の保存・移行、接続切替、失敗時保護を確認する。"""
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import SendPerformance as app
from src import settings


class PortConfigTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / 'setting.json'

    def make_instance(self, port=None):
        with patch.object(app, 'Icon') as icon:
            obj = app.SendPerformance(Path(app.__file__).with_name('icon.png'),
                                      settings_path=self.path, port=port)
        self.addCleanup(obj.serial.close)
        self.addCleanup(icon.call_args.kwargs['icon'].close)
        return obj

    def connected(self, obj):
        old = Mock(is_open=True, baudrate=115200)
        obj.serial = old
        return old

    def test_old_outputs_only_file_uses_default_port(self):
        settings.save_outputs(self.path, ('GPU', 'CPU', 'CPU'))
        obj = self.make_instance()
        self.assertEqual(obj.getPort(), 'COM15')
        self.assertEqual(obj.getOutputs(), ('GPU', 'CPU', 'CPU'))

    def test_saved_port_and_command_line_precedence(self):
        settings.save_outputs(self.path, settings.DEFAULT_OUTPUTS, port='COM9')
        self.assertEqual(self.make_instance().getPort(), 'COM9')
        self.assertEqual(self.make_instance(port='COM7').getPort(), 'COM7')

    def test_switch_opens_new_before_closing_old_and_persists(self):
        obj = self.make_instance()
        old = self.connected(obj)
        new = Mock(is_open=True)
        def connect(**kwargs):
            old.close.assert_not_called()
            return new
        with patch.object(app.serial, 'Serial', side_effect=connect):
            obj.applyConfig(('GPU', 'CPU', 'CPU'), ' com9 ')
        self.assertIs(obj.serial, new)
        old.close.assert_called_once()
        self.assertEqual(obj.getPort(), 'COM9')
        self.assertEqual(settings.load_config(self.path), {
            'port': 'COM9', 'outputs': ('GPU', 'CPU', 'CPU')})
        self.assertEqual(self.make_instance().getPort(), 'COM9')

    def test_busy_port_preserves_connection_file_and_outputs(self):
        obj = self.make_instance()
        old = self.connected(obj)
        obj.setOutputs(settings.DEFAULT_OUTPUTS)
        original = self.path.read_bytes()
        with patch.object(app.serial, 'Serial', side_effect=app.serial.SerialException('busy')):
            with self.assertRaises(app.serial.SerialException):
                obj.applyConfig(('GPU', 'CPU', 'CPU'), 'COM9')
        old.close.assert_not_called()
        self.assertIs(obj.serial, old)
        self.assertEqual(obj.getPort(), 'COM15')
        self.assertEqual(obj.getOutputs(), settings.DEFAULT_OUTPUTS)
        self.assertEqual(self.path.read_bytes(), original)

    def test_save_failure_closes_new_and_keeps_old(self):
        obj = self.make_instance()
        old = self.connected(obj)
        new = Mock()
        with patch.object(app.serial, 'Serial', return_value=new), \
             patch.object(app, 'save_outputs', side_effect=PermissionError('denied')):
            with self.assertRaises(PermissionError):
                obj.applyConfig(('GPU', 'CPU', 'CPU'), 'COM9')
        new.close.assert_called_once()
        old.close.assert_not_called()
        self.assertIs(obj.serial, old)
        self.assertEqual(obj.getOutputs(), settings.DEFAULT_OUTPUTS)

    def test_same_open_port_does_not_reopen(self):
        obj = self.make_instance()
        old = self.connected(obj)
        with patch.object(app.serial, 'Serial') as factory:
            obj.applyConfig(('CPU', 'CPU', 'CPU'), 'COM15')
        factory.assert_not_called()
        old.close.assert_not_called()
        self.assertEqual(json.loads(self.path.read_text(encoding='utf-8'))['port'], 'COM15')

    def test_closed_port_can_be_connected_from_config(self):
        obj = self.make_instance()
        obj.serial.is_open = False
        new = Mock(is_open=True)
        with patch.object(app.serial, 'Serial', return_value=new) as factory:
            obj.applyConfig(settings.DEFAULT_OUTPUTS, 'COM15')
        factory.assert_called_once()
        self.assertIs(obj.serial, new)

    def test_invalid_port_is_rejected_before_connecting(self):
        obj = self.make_instance()
        for port in ['', 'COM0', 'COM-1', 'loop://', '../file']:
            with self.subTest(port=port), patch.object(app.serial, 'Serial') as factory:
                with self.assertRaises(ValueError):
                    obj.applyConfig(settings.DEFAULT_OUTPUTS, port)
                factory.assert_not_called()
        self.assertFalse(self.path.exists())

    def test_startup_failure_still_runs_config_and_shuts_down(self):
        obj = self.make_instance()
        obj.serial = Mock()
        obj.serial.open.side_effect = app.serial.SerialException('unavailable')
        obj.runSchedule = Mock()
        def gui(*args):
            self.assertTrue(obj.config_requested.is_set())
            self.assertTrue(obj.status)
        with patch.object(app, 'run_config_loop', side_effect=gui), self.assertLogs(level='WARNING'):
            obj.runProgram()
        obj.runSchedule.assert_called_once()
        obj.serial.close.assert_called_once()
        self.assertFalse(obj.status)

    def test_disconnected_task_does_not_measure_or_send(self):
        obj = self.make_instance()
        with patch.object(app.psutil, 'cpu_percent') as cpu:
            obj.doTask()
        cpu.assert_not_called()
    def test_real_tk_port_field_is_applied(self):
        from src import config_dialog as dialog
        original_top = dialog.tk.Toplevel
        stop = threading.Event()
        request = threading.Event()
        request.set()
        selected = []
        def create_top(master):
            root = original_top(master)
            root.withdraw()
            def apply():
                frame = root.winfo_children()[0]
                combos = [w for w in frame.winfo_children() if w.winfo_class() == 'TCombobox']
                self.assertEqual(len(combos), 4)
                combos[-1].set('COM9')
                next(w for w in frame.winfo_children()
                     if w.winfo_class() == 'TButton' and w.cget('text') == '適用').invoke()
            root.after(50, apply)
            return root
        def on_apply(outputs, port):
            selected.append((outputs, port))
            stop.set()
        watchdog = threading.Timer(4, stop.set)
        watchdog.start()
        try:
            with patch.object(dialog.tk, 'Toplevel', side_effect=create_top), \
                 patch.object(dialog.list_ports, 'comports', return_value=[]):
                dialog.run_config_loop(
                    stop, request, lambda: settings.DEFAULT_OUTPUTS, Mock(),
                    lambda: 'COM15', on_apply,
                )
        finally:
            watchdog.cancel()
            watchdog.join()
        self.assertEqual(selected, [(settings.DEFAULT_OUTPUTS, 'COM9')])
    def test_write_failure_keeps_scheduler_callable_and_requests_config(self):
        obj = self.make_instance()
        old = self.connected(obj)
        old.write.side_effect = app.serial.SerialException('disconnected')
        with patch.object(app.psutil, 'cpu_percent', return_value=10), \
             patch.object(app.psutil, 'virtual_memory', return_value=type('Memory', (), {'percent': 20})()), \
             patch.object(obj, 'getGpuUsage', return_value=30), self.assertLogs(level='WARNING'):
            obj.doTask()
        old.close.assert_called_once()
        self.assertTrue(obj.config_requested.is_set())