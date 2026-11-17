"""ビルドで生成したICOと、exeへのアイコン埋め込みを確認する。"""
import ctypes
import sys
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


class ExecutableIconTests(unittest.TestCase):
    def test_generated_ico_has_multiple_sizes(self):
        icon = ROOT / 'dist' / 'SendPerformance.ico'
        if not icon.exists() or icon.stat().st_mtime < (ROOT / 'icon.png').stat().st_mtime:
            self.skipTest('ICO未生成または画像より古い。Build.batを実行する')
        with Image.open(icon) as image:
            self.assertEqual(image.format, 'ICO')
            self.assertTrue({(16, 16), (32, 32), (48, 48)} <= image.ico.sizes())

    @unittest.skipUnless(sys.platform == 'win32', 'Windowsのexeリソース検証')
    def test_executable_has_icon_resource(self):
        exe = ROOT / 'dist' / 'SendPerformance.dist' / 'SendPerformance.exe'
        if not exe.exists() or exe.stat().st_mtime < max(
            (ROOT / 'Build.bat').stat().st_mtime, (ROOT / 'icon.png').stat().st_mtime,
        ):
            self.skipTest('exe未生成またはビルド定義より古い')
        extract = ctypes.WinDLL('shell32').ExtractIconExW
        extract.argtypes = [ctypes.c_wchar_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]
        extract.restype = ctypes.c_uint
        count = extract(str(exe), -1, None, None, 0)
        self.assertNotEqual(count, 0xFFFFFFFF, 'exeのアイコンを読み取れない')
        self.assertGreater(count, 0, 'アイコンリソースがない')