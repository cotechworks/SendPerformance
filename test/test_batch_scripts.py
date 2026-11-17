"""起動・配布バッチを一時プロジェクトと別作業フォルダから検証する。"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(sys.platform == 'win32', 'Windows batch tests')
class BatchTests(unittest.TestCase):
    def run_batch(self, batch, arguments=''):
        env = os.environ.copy()
        env['TASK_BATCH_PATH'] = str(batch)
        env['PATH'] = str(Path(getattr(sys, '_base_executable', sys.executable)).parent) + os.pathsep + env['PATH']
        with tempfile.TemporaryDirectory() as directory:
            return subprocess.run(
                'cmd.exe /d /c call "%TASK_BATCH_PATH%" ' + arguments,
                cwd=directory, env=env, input='\n', capture_output=True,
                text=True, errors='replace', timeout=30,
            )

    def fixture(self):
        directory = tempfile.TemporaryDirectory(prefix='batch-test-')
        self.addCleanup(directory.cleanup)
        root = Path(directory.name) / '日本語 project'
        root.mkdir()
        return root

    def test_real_start_help(self):
        result = self.run_batch(ROOT / 'Start.bat', '--help')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('--port', result.stdout)
        self.assertIn('--diagnose-disk', result.stdout)

    def test_start_forwards_arguments_and_uses_project_directory(self):
        root = self.fixture()
        shutil.copyfile(ROOT / 'Start.bat', root / 'Start.bat')
        (root / 'SendPerformance.py').write_text(
            "import json, pathlib, sys\n"
            "pathlib.Path('result.json').write_text(json.dumps({'args':sys.argv[1:], 'cwd':str(pathlib.Path.cwd())}))\n",
            encoding='utf-8',
        )
        result = self.run_batch(root / 'Start.bat', '--port COM15 --debug-log "log file.log"')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        actual = json.loads((root / 'result.json').read_text())
        self.assertEqual(actual['args'], ['--port', 'COM15', '--debug-log', 'log file.log'])
        self.assertEqual(Path(actual['cwd']), root)

    def test_start_preserves_failure_exit_code(self):
        root = self.fixture()
        shutil.copyfile(ROOT / 'Start.bat', root / 'Start.bat')
        (root / 'SendPerformance.py').write_text('raise SystemExit(7)\n', encoding='utf-8')
        result = self.run_batch(root / 'Start.bat')
        self.assertEqual(result.returncode, 7, result.stdout + result.stderr)

    def package_fixture(self):
        root = self.fixture()
        shutil.copyfile(ROOT / 'Package.bat', root / 'Package.bat')
        dist = root / 'dist' / 'SendPerformance.dist'
        dist.mkdir(parents=True)
        (dist / 'SendPerformance.exe').write_bytes(b'fake-exe')
        (dist / 'runtime.dll').write_bytes(b'runtime')
        (dist / 'icon.png').write_bytes(b'icon')
        nested = dist / 'tk'
        nested.mkdir()
        (nested / 'data.txt').write_bytes(b'tcl-data')
        return root, dist

    def test_package_contains_entire_distribution_and_replaces_old_zip(self):
        root, dist = self.package_fixture()
        archive = root / 'dist' / 'SendPerformance.zip'
        for value in [b'first', b'updated']:
            (dist / 'runtime.dll').write_bytes(value)
            result = self.run_batch(root / 'Package.bat')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            with zipfile.ZipFile(archive) as package:
                self.assertEqual(set(package.namelist()), {
                    'SendPerformance.exe', 'runtime.dll', 'icon.png', 'tk/data.txt',
                })
                self.assertEqual(package.read('runtime.dll'), value)
            self.assertEqual(list(archive.parent.glob('*.tmp')), [])

    def test_missing_exe_preserves_previous_package(self):
        root = self.fixture()
        shutil.copyfile(ROOT / 'Package.bat', root / 'Package.bat')
        (root / 'dist').mkdir()
        archive = root / 'dist' / 'SendPerformance.zip'
        archive.write_bytes(b'previous')
        result = self.run_batch(root / 'Package.bat')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Run Build.bat first', result.stdout)
        self.assertEqual(archive.read_bytes(), b'previous')

    def test_zip_creation_failure_cleans_temp(self):
        root, dist = self.package_fixture()
        archive = root / 'dist' / 'SendPerformance.zip'
        archive.mkdir()  # 出力先との衝突で置き換え失敗を起こす。
        result = self.run_batch(root / 'Package.bat')
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(archive.is_dir())
        self.assertEqual(list(archive.parent.glob('*.tmp')), [])