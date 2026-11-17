"""Config画面のプルダウン・適用・キャンセル・終了要求を検証する。"""
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config_dialog as dialog


class DialogTests(unittest.TestCase):
    def run_dialog(self, action):
        root = Mock()
        variables = [Mock(), Mock(), Mock()]
        for variable, value in zip(variables, ('ディスクのアクティブ時間', 'CPU', 'CPU')):
            variable.get.return_value = value
        buttons = {}
        stop, focus = threading.Event(), threading.Event()
        def button(parent, **kwargs):
            buttons[kwargs['text']] = kwargs['command']
            return Mock()
        root.mainloop.side_effect = lambda: action(root, buttons, stop, focus)
        on_apply = Mock()
        with patch.object(dialog.tk, 'Tk', return_value=root), \
             patch.object(dialog.tk, 'StringVar', side_effect=variables), \
             patch.object(dialog.ttk, 'Frame'), patch.object(dialog.ttk, 'Label'), \
             patch.object(dialog.ttk, 'Combobox') as combo, \
             patch.object(dialog.ttk, 'Button', side_effect=button):
            dialog.show_output_config(('CPU', 'メモリ', 'GPU'), on_apply, stop, focus)
        root.destroy.assert_called_once()
        self.assertEqual(combo.call_count, 3)
        for call in combo.call_args_list:
            self.assertEqual(call.kwargs['state'], 'readonly')
            self.assertEqual(call.kwargs['values'], ('CPU', 'メモリ', 'GPU', 'ディスクのアクティブ時間'))
        return root, on_apply

    def test_apply_selected_outputs(self):
        root, apply = self.run_dialog(lambda root, buttons, stop, focus: buttons['適用']())
        apply.assert_called_once_with(('ディスクのアクティブ時間', 'CPU', 'CPU'))
        root.destroy.assert_called_once()

    def test_cancel_does_not_apply(self):
        root, apply = self.run_dialog(lambda root, buttons, stop, focus: buttons['キャンセル']())
        apply.assert_not_called()
        root.destroy.assert_called_once()

    def test_exit_request_quits_dialog(self):
        def action(root, buttons, stop, focus):
            stop.set()
            root.after.call_args.args[1]()
        root, apply = self.run_dialog(action)
        root.destroy.assert_called_once()
        apply.assert_not_called()

    def test_reopen_request_focuses_existing_dialog(self):
        def action(root, buttons, stop, focus):
            focus.set()
            root.after.call_args.args[1]()
            self.assertFalse(focus.is_set())
        root, apply = self.run_dialog(action)
        root.lift.assert_called_once()
        root.focus_force.assert_called_once()
        apply.assert_not_called()
class NativeDialogTests(unittest.TestCase):
    def test_real_tk_apply_and_reopen_on_main_thread(self):
        # 実Tkを使うが画面は非表示。COM接続や実トレイ操作は行わない。
        original_tk = dialog.tk.Tk
        selected = []
        failures = []
        def create_root():
            root = original_tk()
            root.withdraw()
            def apply():
                try:
                    frame = root.winfo_children()[0]
                    combos = [w for w in frame.winfo_children() if w.winfo_class() == 'TCombobox']
                    for combo, value in zip(combos, ('ディスクのアクティブ時間', 'CPU', 'CPU')):
                        combo.set(value)
                    button = next(w for w in frame.winfo_children()
                                  if w.winfo_class() == 'TButton' and w.cget('text') == '適用')
                    button.invoke()
                except Exception as error:
                    failures.append(error)
                    root.destroy()
            root.after(100, apply)
            return root
        with patch.object(dialog.tk, 'Tk', side_effect=create_root):
            for _ in range(2):
                dialog.show_output_config(
                    ('CPU', 'メモリ', 'GPU'), selected.append,
                    threading.Event(), threading.Event(),
                )
        self.assertEqual(failures, [])
        self.assertEqual(selected, [('ディスクのアクティブ時間', 'CPU', 'CPU')] * 2)

    def test_real_config_loop_applies_and_exits(self):
        original_top = dialog.tk.Toplevel
        stop = threading.Event()
        requested = threading.Event()
        requested.set()
        selected = []
        def create_top(master):
            root = original_top(master)
            root.withdraw()
            def apply():
                frame = root.winfo_children()[0]
                combos = [w for w in frame.winfo_children() if w.winfo_class() == 'TCombobox']
                for combo in combos:
                    combo.set('ディスクのアクティブ時間')
                button = next(w for w in frame.winfo_children()
                              if w.winfo_class() == 'TButton' and w.cget('text') == '適用')
                button.invoke()
            root.after(50, apply)
            return root
        def on_apply(outputs):
            selected.append(outputs)
            stop.set()
        # 失敗時もテストプロセスが待ち続けないように停止を要求する。
        watchdog = threading.Timer(4, stop.set)
        watchdog.start()
        try:
            with patch.object(dialog.tk, 'Toplevel', side_effect=create_top):
                dialog.run_config_loop(
                    stop, requested, lambda: ('CPU', 'メモリ', 'GPU'), on_apply,
                )
        finally:
            watchdog.cancel()
            watchdog.join()
        self.assertEqual(selected, [('ディスクのアクティブ時間', 'ディスクのアクティブ時間', 'ディスクのアクティブ時間')])