# タスク管理
更新日: 2026-11-18

## 目次
- [運用ルール](#運用ルール)
- [未完了タスク](#未完了タスク)
- [次に着手するタスク](#次に着手するタスク)
- [保留事項](#保留事項)
- [完了済みタスク](#完了済みタスク)

## 運用ルール
- IDはT-001から採番し、完了後も維持する。
- 未着手・進行中・未確認・保留を未完了に置く。
- 開発側検証と利用者確認を分け、全確認項目を満たした行だけ完了へ移動する。
- 既存実装を調査しただけでは実装タスクを完了と扱わない。下記の開発検証タスクは既存実装に対する検証の管理である。
- コマンド、結果、未実施理由、利用者確認日と結果を備考に記録する。

## 未完了タスク
| ID | タスク | 状態 | 関連決定 | 備考 |
| --- | --- | --- | --- | --- |
なし。

## 次に着手するタスク
未完了タスクはなし。以降の実装時もtest/の自動テストを実行する。

## 保留事項
- 対応環境・許容送信周期・切断時対応の要件整理は未決定。
- 自動テストをtest/test_send_performance.pyに配置した。実機・実GUIの検証と区別する。
- 過去のJPG同梱ビルドや過去の検証結果は、現在のPNG版の完了根拠として流用しない。

## 完了済みタスク
| ID | タスク | 状態 | 関連決定 | 備考 |
| --- | --- | --- | --- | --- |
| T-001 | READMEと管理資料の初期作成・ソース照合 | 完了 | D-005 | 2026-11-17。AGENTS.md、ソース、ビルド定義、設定を読んで作成。python SendPerformance.py --helpは終了コード0、python -m pip checkはNo broken requirements found、ast.parseで構文確認成功。Pythonはいずれも.venv/Scripts/python.exe。実機・GPU実測・PNG版exeは未検証 |
| T-002 | 3指標・GPU取得失敗・COM送信の開発検証 | 完了 | D-001, D-002 | 2026-11-17、T-006でループバック送信・GPU集計・失敗時0・Task/Exit・終了処理の自動テスト成功。同日、利用者から「T-002完了」の報告を受領し、残項目を含む完了として記録。実機送信・GPU実測の個別手順・結果ログは未受領。利用者確認T-004は別途完了済み |
| T-003 | PNG同梱exeの開発検証 | 完了 | D-003, D-004 | 2026-11-17、T-006で既存exeのPNG一致、別フォルダからの--help、画像読込後の接続処理到達を確認。同日、利用者から「T-003完了」の報告を受領し、再ビルド・実GUI・送信・Exit・配布先確認を含む完了として記録。個別の結果ログは未受領。利用者確認T-004は別途完了済み |
| T-004 | 実機での利用者確認 | 完了 | D-001, D-002, D-003, D-004 | 対象はT-002・T-003の既存実装検証。COM15受信、値の妥当性、GPU未取得時0、PNGトレイ表示、TaskとExit、配布先起動を確認。2026-11-17、利用者から「T-004完了」の報告を受領し、確認完了として記録 |
| T-005 | ドキュメントの利用者確認 | 完了 | D-005 | 対象はT-001。READMEとdoc/4資料の要件区分、準備・ビルド・配布手順、未決定事項を確認。2026-11-17、利用者から「T-005完了」の報告を受領し、確認完了として記録 |
| T-006 | test/への自動テスト作成・実行 | 完了 | D-001, D-002, D-003, D-004, D-006 | 2026-11-17。test/test_send_performance.pyを追加。.venv/Scripts/python.exe -W error::ResourceWarning -m unittest discover -s test -vで14件成功、スキップなし。pip check成功。実機ポート未使用、再ビルド未実施。アプリ本体・依存の変更なし |
| T-007 | Configメニュー・3出力設定・自動テスト | 完了 | D-007 | 2026-11-17。Config画面、3枠プルダウン、起動中の一括設定、終了要求を実装。test/にテスト追加。.venv/Scripts/python.exe -B -W error::ResourceWarning -m unittest discover -s test -vで23件成功、旧exeのテスト群1グループをスキップ。実Tkを非表示で適用・再表示・終了確認。--help成功。実トレイ・実機・再ビルドはT-008・T-009 |
| T-008 | Config機能の利用者確認 | 完了 | D-007 | 対象T-007。右クリックConfig、各プルダウン、順序変更・重複・3列CRLF、適用・キャンセル・×、再表示、定期送信継続、画面表示中のExitを実機で確認。再起動時は初期値へ戻る。2026-11-17、利用者から「T-008完了」の報告を受領し、確認完了として記録 |
| T-009 | Config・ディスク対応exeの再ビルド・確認 | 完了 | D-003, D-004, D-007, D-008 | Build.batのtk-inter設定、再ビルド、自動テスト（exe群含む）、別フォルダからのConfig表示・適用・終了、Tcl/Tk同梱が確認対象。2026-11-17、利用者から「T-009完了」の報告を受領し、確認完了として記録 |
| T-010 | ディスクのアクティブ時間取得・選択・送信・自動テスト | 完了 | D-008 | 2026-11-17。getDiskUsageとConfig候補を追加。同日の利用者指示で表示名を「ディスクのアクティブ時間」に変更し、プルダウン幅を調整。変更後も30件成功、旧exe群1グループスキップ。test/test_disk_usage.pyを追加、実Tkテストを更新。.venv/Scripts/python.exe -B -W error::ResourceWarning -m unittest discover -s test -vで30件成功、旧exe群1グループスキップ。実CIMで3物理ディスクのカウンター読み取りを確認。実機送信・負荷追従・exeはT-011・T-009 |
| T-012 | T-011用ディスク負荷スクリプト作成・検証 | 完了 | D-008 | 2026-11-17の利用者指示。test/disk_load.pyとtest/test_disk_load.pyを追加。時間・ファイルサイズ・累積書込上限、空き容量検査、専用一時ファイルと終了時削除を実装。.venv/Scripts/python.exe -B -m unittest discover -s test -p test_disk_load.py -vで5件成功。--seconds 0.5 --size-mib 1 --max-write-mib 2でCLI成功、一時ファイル削除確認。実機追従確認はT-011のまま |
| T-014 | exe内ディスク診断・送信ログ・再ビルド | 完了 | D-008 | 2026-11-17。--diagnose-disk、--debug-logを追加。disk_diagnostics.pyで実COM未接続のloopback検証。Nuitkaでprotocol_loopを明示importし同梱。Build.bat成功、最大64MiB・8秒の限定一時負荷でexeの3列目が82・81・81%、停止後1%となることを確認（実書込約43.6MiB）。自動テスト40件成功、スキップなし。実デバイスの不一致は当時T-013で継続し、後に最新ビルドの正常動作報告で完了 |
| T-011 | ディスクのアクティブ時間の利用者確認 | 完了 | D-008 | 対象T-010、負荷ツールT-012。2026-11-17、利用者より最新ビルドでは正常動作との報告を受領。負荷中の取得・出力3の追従を確認完了。ログでも22:20:45以降に82～88%の取得・送信を確認。以前はビルド前のexeで検証していた可能性があるが、原因としては未確定 |
| T-013 | ディスク値とデバイス表示の不一致の切り分け | 完了 | D-008 | 対象T-014。ソース・診断exeの負荷追従、通常ログの設定とTXを照合。2026-11-17、利用者より最新ビルドの正常動作を確認。旧exeを検証していた可能性を原因候補として記録し、再現症状は解消として終了。旧exe使用の事実・根本原因は未確定 |
| T-015 | 補助Pythonモジュールのsrc移動 | 完了 | D-009 | 2026-11-17。src/config_dialog.py・src/disk_diagnostics.pyへ移動し、src/__init__.py追加。importとテスト参照・exe鮮度判定を更新。.venv/Scripts/python.exe -B -W error::ResourceWarning -m unittest discover -s test -vで37件成功、旧exe群1グループスキップ。SendPerformance.py --help成功。exe再ビルドはT-016 |
| T-016 | src移動後のexe再ビルド・利用者確認 | 完了 | D-009 | 対象T-015。Build.batでの再ビルド、exeの--help・--diagnose-disk、Config表示・適用・Exit、COM実機送信が確認対象。2026-11-17、利用者から「T-016完了」の報告を受領し、確認完了として記録。setting.json保存・復元はT-019で別途確認 |
| T-017 | 実行時requirements.txtの作成 | 完了 | なし | 2026-11-17の利用者指示。現在のimportと仮想環境に基づきpystray・Pillow・schedule・psutil・pyserialの直接依存5件を固定。requirements-build.txtはビルド専用のまま維持。固定版と導入版の一致・アプリimport・pip check成功。依存の追加・更新は未実施。新規環境での再構築は未確認 |
| T-018 | Configのsetting.json保存・復元 | 完了 | D-010 | 2026-11-17。src/settings.pyを追加し、起動時読込、適用時の置換保存、保存失敗通知を実装。test/test_settings.py追加、既存テストを一時ファイルで分離。.venv/Scripts/python.exe -B -W error::ResourceWarning -m unittest discover -s test -vで48件成功、旧exe群1グループスキップ。exe実保存はT-019 |
| T-020 | Nuitka版setting.json保存先の修正 | 完了 | D-010 | 2026-11-17。containing_dirではなくsys.argv[0]の親を保存先に変更。distとSendPerformance.distが異なる回帰ケースをtest/test_settings.pyに追加。exeは未再ビルド、利用者確認はT-019 |
| T-019 | setting.json保存・復元の利用者確認 | 完了 | D-010 | 対象T-018・T-020。Python保存先の確認後、exeのdist/直下への保存を修正。2026-11-17、利用者から「T-019完了」の報告を受領。exe横への保存、別作業フォルダからの起動、再起動復元、キャンセル、書込失敗時の確認を完了として記録 |
| T-021 | icon.pngからexeアイコンを生成・埋め込み | 完了 | D-011 | 2026-11-17。Build.batでPillowから7サイズのICOを生成し、Nuitkaで埋め込み。ビルド成功、Adding 7 iconsを確認。test/test_executable_icon.py追加。ICOの複数サイズ・exeのアイコンリソースを検証し、全53件成功、スキップなし。実画面はT-022 |
| T-022 | exeアイコンの利用者確認 | 完了 | D-011 | 対象T-021。dist/SendPerformance.dist/SendPerformance.exeをエクスプローラーで表示し、icon.png由来のアイコンになっていることを確認する。2026-11-17、利用者から「T-022完了」の報告を受領し、表示確認完了として記録 |
| T-023 | Start.bat・Package.batの対象修正・検証 | 完了 | D-012 | 2026-11-17。別プロジェクト名を本プロジェクトに置換、Startの引数伝播を追加。test/test_batch_scripts.py追加。.venv/Scripts/python.exe -B -m unittest discover -s test -p test_batch_scripts.py -vで6件成功。実Package.batでdist/SendPerformance.zip作成、948ファイルの一致とCRC検証成功（14,487,497bytes）。通常起動のCOM操作・展開先実行はT-024 |
| T-025 | ConfigのCOM選択・保存・接続切替 | 完了 | D-013 | 2026-11-17。COM欄追加、一覧更新・手入力、outputsとport保存、起動時復元、引数優先、旧JSON互換、失敗時保護、接続待ちからの回復を実装。test/test_port_config.py追加と既存テスト更新。.venv/Scripts/python.exe -B -W error::ResourceWarning -m unittest discover -s testで70件成功、旧exe群1グループスキップ。実Tk COM適用・--help確認。実機・再ビルドはT-026 |
| T-024 | 起動・配布バッチの利用者確認 | 完了 | D-012 | 対象T-023。Start.batの通常起動・Config・COM送信・Exit、ZIP展開先でexeが起動することを確認。--helpとZIP内容は開発側検証済み。2026-11-18、利用者から「T-024完了」の報告を受領し、確認完了として記録 |
| T-026 | ConfigのCOM設定・再接続の利用者確認 | 完了 | D-013 | 対象T-025。2026-11-18、利用者よりビルド済みexeで全確認項目完了の報告を受領。COM一覧・手入力、実機切替、使用中ポート時の旧接続維持、再起動復元、起動失敗・切断後の再接続を確認済み。exeアイコン表示は別件T-027で管理 |
| T-027 | エクスプローラーのexeアイコン非表示の確認 | 完了 | D-011 | 2026-11-18、利用者報告。dist/SendPerformance.dist/SendPerformance.exeはWindows APIでアイコン1グループを検出、ICO・exeアイコンのテスト2件成功。対象exeへのShell更新通知を実行。同日、利用者がZIP圧縮後にデスクトップへ展開したexeで正常なアイコン表示を確認。元の場所での非表示原因は未確定 |
