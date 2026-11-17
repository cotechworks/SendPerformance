# 構成・設計
更新日: 2026-11-17

## 目次
- [全体構成](#全体構成)
- [モジュールの役割](#モジュールの役割)
- [データ・保存形式](#データ保存形式)
- [主要な処理](#主要な処理)
- [外部依存](#外部依存)
- [制約](#制約)

## 全体構成
単一のSendPerformanceクラスがトレイと指標送信を管理する。メインスレッドがトレイ、別スレッドがscheduleを実行する。継承はない。構成図は[README](../README.md#構成)を参照する。

## モジュールの役割
| 要素 | 役割 |
| --- | --- |
| SendPerformance.py | エントリーポイントとSendPerformanceクラス |
| status | 定期実行継続フラグ |
| serial | 未接続状態で生成し、runProgramで開くSerialオブジェクト |
| serial_lock | Taskと定期処理のシリアル書き込みを直列化 |
| icon | pystrayのトレイオブジェクト |
| Build.bat | .venvのPythonからNuitkaを実行 |
| requirements-build.txt | Nuitka==4.3.5 |
| icon.png | PILで開くトレイ用画像 |

## データ・保存形式
送信はASCIIの3数値、カンマ区切り、行末CRLF。順序はCPU・メモリ・GPU。永続データ、DB、設定ファイルは存在しない。起動引数はプロセス内だけで使用する。

## 主要な処理
| メソッド | 引数・戻り値 | 処理・副作用・主な例外 |
| --- | --- | --- |
| __init__ | image, port=COM15, baudrate=115200 / None | Serial・ロック・画像・メニューを準備。画像読み込み等の例外は伝播 |
| doTask | なし / None | CPU・メモリ・GPU取得、ロック内でwrite。SerialException等は伝播 |
| getGpuUsage | なし / 数値 | PowerShellを最大5秒待機。合計したエンジン使用率の最大を0～100に制限。OSError、SubprocessError、ValueErrorを0へ変換 |
| runSchedule | なし / None | 0.1秒間隔のジョブをグローバルscheduleへ登録しrun_pendingを実行。doTask例外は捕捉しない |
| stopProgram | icon / None | status=False、トレイ停止 |
| runProgram | なし / None | COM接続、ワーカー開始、トレイ実行。トレイ実行終了時はfinallyでワーカーjoinとポートclose |

起動引数を解析し、スクリプトと同じ場所のicon.pngを渡してrunProgramを呼ぶ。

```mermaid
flowchart TD
  Main["エントリーポイント"] --> Init["__init__"]
  Main --> Run["runProgram"]
  Run --> Schedule["runSchedule"]
  Schedule --> Task["doTask"]
  TrayTask["トレイ Task"] --> Task
  Task --> GPU["getGpuUsage"]
  TrayExit["トレイ Exit"] --> Stop["stopProgram"]
```

状態一覧は「準備済み」「稼働中」「終了処理中」「終了」「起動失敗」とする。送信スレッド単体の異常停止はstatusで表現されない。
```mermaid
stateDiagram-v2
  state "準備済み" as Ready
  state "稼働中" as Running
  state "終了処理中" as Closing
  state "終了" as Closed
  state "起動失敗" as Failed
  Ready --> Running: COM接続成功・ワーカー開始
  Ready --> Failed: COM接続例外
  Running --> Closing: Exitまたはトレイ実行終了
  Closing --> Closed: ワーカー終了待ち・COM切断
```

関数の引数・戻り値・例外を説明するdocstringは全6メソッドで未整備。コメントの一部は実装のスケジュール間隔と不一致。

## 外部依存
| 依存 | 用途 |
| --- | --- |
| pystray | Windowsトレイ |
| Pillow | PNG読み込み |
| schedule | 定期実行 |
| psutil | CPU・メモリ |
| pyserial | シリアル送信 |
| Windows PowerShell / GPU CIMカウンター | GPUエンジン情報 |
| Nuitka・Cコンパイラ | exe生成時のみ |

## 制約
- Windows固有のPowerShellとCREATE_NO_WINDOWを使用する。
- 計測・PowerShell起動は同期処理で、固定周期や即時終了を保証しない。
- ロック対象はwriteだけであり、指標取得は同時実行され得る。
- 起動時のCOM接続とワーカー開始はトレイのtry/finallyより前にある。
- シリアル切断の自動再接続やジョブ解除はなく、1プロセスでの再実行・複数インスタンス管理は未整備。
- 設計変更案の採否は[決定記録](decisions.md)で扱い、現行実装と区別する。