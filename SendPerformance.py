from pystray import Icon, MenuItem, Menu
from PIL import Image
import time
import threading
import schedule
import psutil
import subprocess
import argparse
import serial

class SendPerformance:
    def __init__(self, image, port='COM15', baudrate=115200):
        self.status = False
        self.serial = serial.Serial(port=None, baudrate=baudrate, write_timeout=1)
        self.serial.port = port
        self.serial_lock = threading.Lock()

        ## アイコンの画像
        image = Image.open(image)
        ## 右クリックで表示されるメニュー
        menu = Menu(
                    MenuItem('Task', self.doTask),
                    MenuItem('Exit', self.stopProgram),
                )

        self.icon = Icon(name='nameTray', title='titleTray', icon=image, menu=menu)

    def doTask(self):
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        gpu = self.getGpuUsage()
        with self.serial_lock:
            self.serial.write(f'{cpu},{mem.percent},{gpu}\r\n'.encode('ascii'))

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
            self.icon.run()
        finally:
            self.status = False
            task_thread.join()
            self.serial.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', default='COM15', help='送信先COMポート（既定: COM15）')
    parser.add_argument('--baudrate', type=int, default=115200)
    args = parser.parse_args()
    system_tray = SendPerformance(image="icon.jpg", port=args.port, baudrate=args.baudrate)
    system_tray.runProgram()
