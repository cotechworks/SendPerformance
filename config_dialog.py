"""Tk操作をメインスレッドに集約する出力設定画面。"""
import tkinter as tk
from tkinter import ttk

OUTPUT_CHOICES = ('CPU', 'メモリ', 'GPU')


def show_output_config(outputs, on_apply, stop_event, focus_event, master=None):
    root = tk.Toplevel(master) if master is not None else tk.Tk()
    root.title('Config')
    root.resizable(False, False)
    closed = False
    timer = None
    try:
        frame = ttk.Frame(root, padding=16)
        frame.grid()
        ttk.Label(frame, text='各出力に送信する使用率を選択してください。').grid(
            row=0, column=0, columnspan=2, pady=(0, 12))
        variables = []
        for index, output in enumerate(outputs):
            ttk.Label(frame, text=f'出力 {index + 1}').grid(
                row=index + 1, column=0, padx=(0, 12), pady=4)
            variable = tk.StringVar(master=root, value=output)
            variables.append(variable)
            ttk.Combobox(
                frame, textvariable=variable, values=OUTPUT_CHOICES,
                state='readonly', width=16,
            ).grid(row=index + 1, column=1, pady=4)

        def close():
            nonlocal closed
            closed = True
            if timer is not None:
                root.after_cancel(timer)
            root.destroy()

        def apply():
            on_apply(tuple(variable.get() for variable in variables))
            close()

        ttk.Label(frame, text='設定はアプリ終了まで有効です。').grid(
            row=4, column=0, columnspan=2, pady=(12, 4))
        ttk.Button(frame, text='適用', command=apply).grid(row=5, column=0, pady=(8, 0))
        ttk.Button(frame, text='キャンセル', command=close).grid(row=5, column=1, pady=(8, 0))
        root.protocol('WM_DELETE_WINDOW', close)

        def poll():
            nonlocal timer
            if stop_event.is_set():
                close()
                return
            if focus_event.is_set():
                focus_event.clear()
                root.lift()
                root.focus_force()
            timer = root.after(100, poll)

        timer = root.after(100, poll)
        if master is None:
            root.mainloop()
        else:
            root.wait_window()
    finally:
        if not closed:
            if timer is not None:
                root.after_cancel(timer)
            root.destroy()


def run_config_loop(stop_event, request_event, get_outputs, on_apply):
    """非表示のTkルートを維持し、トレイからの表示要求を処理する。"""
    root = tk.Tk()
    root.withdraw()
    try:
        def poll():
            if stop_event.is_set():
                root.quit()
                return
            if request_event.is_set():
                request_event.clear()
                show_output_config(
                    get_outputs(), on_apply, stop_event, request_event, master=root,
                )
            root.after(100, poll)
        root.after(100, poll)
        root.mainloop()
    finally:
        root.destroy()