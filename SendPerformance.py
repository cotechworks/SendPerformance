from pystray import Icon, MenuItem, Menu
from PIL import Image
import time
import threading
import schedule
import psutil
import subprocess
import argparse
import logging
import serial
from pathlib import Path
from config_dialog import OUTPUT_CHOICES, run_config_loop

class SendPerformance:
    def __init__(self, image, port='COM15', baudrate=115200):
        self.status = False
        self.serial = serial.Serial(port=None, baudrate=baudrate, write_timeout=1)
        self.serial.port = port
        self.serial_lock = threading.Lock()
        self.outputs = ('CPU', 'メモリ', 'GPU')
        self.config_stop = threading.Event()
        self.config_requested = threading.Event()

        ## アイコンの画像
        image = Image.open(image)
        ## 右クリックで表示されるメニュー
        menu = Menu(
                    MenuItem('Task', self.doTask),
                    MenuItem('Config', self.showConfig),
                    MenuItem('Exit', self.stopProgram),
                )

        self.icon = Icon(name='nameTray', title='titleTray', icon=image, menu=menu)

    def doTask(self):
        with self.serial_lock:
            outputs = self.outputs
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        gpu = self.getGpuUsage()
        values = {'CPU': cpu, 'メモリ': mem.percent, 'GPU': gpu}
        if 'ディスクのアクティブ時間' in outputs:
            values['ディスクのアクティブ時間'] = self.getDiskUsage()
        payload = (','.join(str(values[name]) for name in outputs) + '\r\n').encode('ascii')
        with self.serial_lock:
            self.serial.write(payload)
        logging.debug('outputs=%s TX=%r', outputs, payload)

    def setOutputs(self, outputs):
        """3出力を一括更新する。不正な設定は送信へ反映しない。"""
        outputs = tuple(outputs)
        if len(outputs) != 3 or any(name not in OUTPUT_CHOICES for name in outputs):
            raise ValueError('出力候補から3つ選択してください')
        with self.serial_lock:
            self.outputs = outputs

    def getOutputs(self):
        with self.serial_lock:
            return self.outputs

    def showConfig(self):
        """トレイスレッドからメインスレッドへ表示を要求する。"""
        if not self.config_stop.is_set():
            self.config_requested.set()

    @staticmethod
    def getDiskUsage():
        """物理ディスクごとの100-アイドル時間の最大値。取得不能なら0。"""
        command = (
            "$ErrorActionPreference = 'Stop'; "
            "$disks = @(Get-CimInstance "
            "Win32_PerfFormattedData_PerfDisk_PhysicalDisk | "
            "Where-Object { $_.Name -ne '_Total' -and $null -ne $_.PercentIdleTime }); "
            "if ($disks.Count -eq 0) { exit 1 }; "
            "$usage = $disks | ForEach-Object { "
            "100.0 - [double]$_.PercentIdleTime "
            "} | Measure-Object -Maximum; "
            "[Console]::Write($usage.Maximum.ToString("
            "[System.Globalization.CultureInfo]::InvariantCulture))"
        )
        try:
            result = subprocess.run(
                ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command],
                capture_output=True, text=True, check=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            value = max(0.0, min(100.0, float(result.stdout.strip())))
            logging.debug('disk raw=%r active=%s', result.stdout, value)
            return value
        except (OSError, subprocess.SubprocessError, ValueError) as error:
            logging.debug('disk acquisition failed: %r stderr=%r', error, getattr(error, 'stderr', None))
            return 0

    @staticmethod
    def getGpuUsage():
        # Sum processes sharing an engine, then report the busiest GPU engine.
        command = (
            "$ErrorActionPreference = 'Stop'; "
            "$engines = @(Get-CimInstance "
            "Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine); "
            "if ($engines.Count -eq 0) { exit 1 }; "
            "$usage = $engines | "
            "Group-Object { $_.Name -replace '^pid_\\d+_', '' } | "
            "ForEach-Object { "
            "($_.Group | Measure-Object UtilizationPercentage -Sum).Sum "
            "} | Measure-Object -Maximum; "
            "[Console]::Write($usage.Maximum)"
        )
        try:
            result = subprocess.run(
                ['powershell.exe', '-NoProfile', '-NonInteractive',
                 '-Command', command],
                capture_output=True, text=True, check=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return max(0.0, min(100.0, float(result.stdout.strip())))
        except (OSError, subprocess.SubprocessError, ValueError):
            return 0
    
    def runSchedule(self):
        ## 5秒毎にタスクを実行する。
        schedule.every(0.1).seconds.do(self.doTask)
        ## status が True である間実行する。
        while self.status:
            schedule.run_pending()
            time.sleep(0.1)
    
    def stopProgram(self, icon):
        self.status = False
        self.config_stop.set()

        ## 停止
        self.icon.stop()

    def runProgram(self):
        self.serial.open()
        self.status = True

        ## スケジュールの実行
        task_thread = threading.Thread(target=self.runSchedule)
        task_thread.start()

        ## 実行
        try:
            self.icon.run_detached()
            run_config_loop(
                self.config_stop, self.config_requested, self.getOutputs, self.setOutputs,
            )
        finally:
            self.status = False
            self.config_stop.set()
            task_thread.join()
            self.icon.stop()
            self.serial.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', default='COM15', help='送信先COMポート（既定: COM15）')
    parser.add_argument('--baudrate', type=int, default=115200)
    parser.add_argument('--debug-log', type=Path, help='取得値と送信データを記録するログファイル')
    parser.add_argument('--diagnose-disk', action='store_true', help='COM接続せずCPU,メモリ,ディスクを5回取得して表示')
    args = parser.parse_args()
    if args.debug_log:
        logging.basicConfig(filename=args.debug_log, level=logging.DEBUG,
                            format='%(asctime)s %(levelname)s %(message)s', encoding='utf-8')
    if args.diagnose_disk:
        from disk_diagnostics import diagnose_disk
        raise SystemExit(diagnose_disk())
    system_tray = SendPerformance(image=Path(__file__).resolve().with_name('icon.png'), port=args.port, baudrate=args.baudrate)
    system_tray.runProgram()
