"""setting.jsonの保存、復元、保存先、失敗時の整合性を確認する。"""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import SendPerformance as app
from src import settings


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / 'setting.json'

    def test_python_path_is_beside_main_not_cwd(self):
        main = Path(self.folder.name) / 'app' / 'SendPerformance.py'
        with patch.object(settings.sys, 'frozen', False, create=True):
            self.assertEqual(settings.get_setting_path(main), main.with_name('setting.json'))

    def test_nuitka_path_is_beside_exe(self):
        build_dir = Path(self.folder.name) / 'dist'
        exe = build_dir / 'SendPerformance.dist' / 'SendPerformance.exe'
        with patch.object(settings.sys, 'argv', [str(exe)]):
            self.assertEqual(
                settings.get_setting_path('unused.py', SimpleNamespace(containing_dir=str(build_dir))),
                exe.with_name('setting.json'),
            )

    def test_compiled_fallback_uses_argv(self):
        exe = Path(self.folder.name) / 'SendPerformance.exe'
        with patch.object(settings.sys, 'argv', [str(exe)]):
            self.assertEqual(settings.get_setting_path('unused.py', True), exe.with_name('setting.json'))

    def test_frozen_path_uses_executable(self):
        exe = Path(self.folder.name) / 'SendPerformance.exe'
        with patch.object(settings.sys, 'frozen', True, create=True), \
             patch.object(settings.sys, 'executable', str(exe)):
            self.assertEqual(settings.get_setting_path('unused.py'), exe.with_name('setting.json'))

    def test_missing_file_uses_defaults_without_creating_file(self):
        self.assertEqual(settings.load_outputs(self.path), settings.DEFAULT_OUTPUTS)
        self.assertFalse(self.path.exists())

    def test_roundtrip_preserves_order_duplicates_and_japanese(self):
        outputs = ('ディスクのアクティブ時間', 'CPU', 'CPU')
        settings.save_outputs(self.path, outputs)
        self.assertEqual(settings.load_outputs(self.path), outputs)
        self.assertEqual(json.loads(self.path.read_text(encoding='utf-8')), {'outputs': list(outputs)})
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_invalid_json_and_schema_preserve_original_file(self):
        for content in ['{broken', '[]', '{}', '{"outputs":["CPU"]}',
                        '{"outputs":["CPU","GPU",{}]}', '{"outputs":["CPU","GPU","unknown"]}']:
            with self.subTest(content=content):
                self.path.write_text(content, encoding='utf-8')
                with self.assertLogs(level='WARNING'):
                    self.assertEqual(settings.load_outputs(self.path), settings.DEFAULT_OUTPUTS)
                self.assertEqual(self.path.read_text(encoding='utf-8'), content)

    def test_replace_error_preserves_file_and_cleans_temp(self):
        settings.save_outputs(self.path, settings.DEFAULT_OUTPUTS)
        original = self.path.read_bytes()
        with patch.object(settings.os, 'replace', side_effect=PermissionError('denied')):
            with self.assertRaises(PermissionError):
                settings.save_outputs(self.path, ('GPU', 'CPU', 'CPU'))
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def make_instance(self):
        with patch.object(app, 'Icon') as icon:
            obj = app.SendPerformance(Path(app.__file__).with_name('icon.png'), settings_path=self.path)
        self.addCleanup(obj.serial.close)
        self.addCleanup(icon.call_args.kwargs['icon'].close)
        return obj

    def test_application_restores_saved_config(self):
        original = self.make_instance()
        outputs = ('GPU', 'ディスクのアクティブ時間', 'メモリ')
        original.setOutputs(outputs)
        restarted = self.make_instance()
        self.assertEqual(restarted.getOutputs(), outputs)

    def test_application_keeps_old_outputs_if_save_fails(self):
        obj = self.make_instance()
        with patch.object(app, 'save_outputs', side_effect=PermissionError('denied')):
            with self.assertRaises(PermissionError):
                obj.setOutputs(('GPU', 'CPU', 'CPU'))
        self.assertEqual(obj.getOutputs(), settings.DEFAULT_OUTPUTS)