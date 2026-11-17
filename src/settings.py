"""Configの保存・復元と、実行ファイル横の保存先解決。"""
import json
import logging
import os
from pathlib import Path
import sys
import tempfile

from .config_dialog import OUTPUT_CHOICES

DEFAULT_OUTPUTS = ('CPU', 'メモリ', 'GPU')


def get_setting_path(main_file, compiled=None):
    if compiled is not None:
        # Nuitkaのcontaining_dirはstandalone配布フォルダの親を返す場合がある。
        return Path(sys.argv[0]).resolve().with_name('setting.json')
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().with_name('setting.json')
    return Path(main_file).resolve().with_name('setting.json')


def validate_outputs(outputs):
    if not isinstance(outputs, (list, tuple)) or len(outputs) != 3 or any(
        not isinstance(name, str) or name not in OUTPUT_CHOICES for name in outputs
    ):
        raise ValueError('出力候補から3つ選択してください')
    return tuple(outputs)


def load_outputs(path):
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            raise ValueError('設定はJSONオブジェクトで指定してください')
        return validate_outputs(data.get('outputs'))
    except FileNotFoundError:
        return DEFAULT_OUTPUTS
    except (OSError, ValueError, UnicodeError) as error:
        logging.warning('設定を読み込めないため初期値を使用します: %s (%s)', path, error)
        return DEFAULT_OUTPUTS


def save_outputs(path, outputs):
    outputs = validate_outputs(outputs)
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='w', encoding='utf-8', dir=path.parent,
            prefix='.setting-', suffix='.tmp', delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump({'outputs': list(outputs)}, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)