"""実行中のPython/exeの取得・CSV生成経路をCOM接続なしで検証する。"""
import logging
import threading
import time
from serial.urlhandler import protocol_loop


def diagnose_disk(samples=5, output=print):
    # __main__として動作中なら同じクラスを使う。
    import sys
    main = sys.modules.get('__main__')
    if hasattr(main, 'SendPerformance'):
        cls = main.SendPerformance
    else:
        from SendPerformance import SendPerformance as cls
    app = cls.__new__(cls)
    app.serial_lock = threading.Lock()
    app.outputs = ('CPU', 'メモリ', 'ディスクのアクティブ時間')
    with protocol_loop.Serial('loop://', timeout=1) as app.serial:
        output('COM接続なし / 出力順: CPU,メモリ,ディスクのアクティブ時間')
        for index in range(samples):
            start = time.monotonic()
            app.doTask()
            payload = app.serial.readline()
            output(f'{index + 1}: {payload.decode("ascii").strip()} ({time.monotonic() - start:.2f}s)')
            logging.debug('diagnostic loopback received=%r', payload)
    return 0