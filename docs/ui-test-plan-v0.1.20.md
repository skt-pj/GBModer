# GBModer UI受入試験表 v0.1.20

作成役割: 仕様作成担当とは別の評価担当

対象仕様: `docs/ui-spec-v0.1.20.md`

判定原則:
- PASSは観測可能な結果が期待値と一致した場合のみ。
- ビルド成功だけではUI要件PASSとしない。
- 実機/エミュレータでしか確認できない項目は、CIでは「未実施」と明示する。
- 既存ロジックの退行試験を必須とする。

| ID | 区分 | 試験内容 | 操作/条件 | 期待結果 | 自動化 |
|---|---|---|---|---|---|
| UI-001 | 構造 | Compose UIが起動する | MainActivity起動 | 旧LinearLayout画面ではなくCompose画面が表示される | build/static |
| UI-002 | 構造 | Scaffold採用 | ソース確認 | 最上位がMaterial3 Scaffoldで構成される | static |
| UI-003 | スクロール | Compact縦スクロール | 画面高が小さい端末 | 最下部の主操作まで到達できる | UI test/manual |
| UI-004 | Insets | status bar回避 | API35+, edge-to-edge | TopAppBar/本文がsystem barに隠れない | UI test/manual |
| UI-005 | Insets | navigation bar回避 | 3ボタンナビ | 主操作がnav barに隠れない | manual |
| UI-006 | TopAppBar | タイトル | 起動 | `GBModer`表示 | UI test |
| UI-007 | 状態 | 停止中表示 | 初期状態 | `停止中`が文字で分かる | UI test |
| UI-008 | 初回設定 | 未設定カード | Accessibility OFF | 初回設定カードと有効化CTA表示 | integration/manual |
| UI-009 | 初回設定 | 設定済み縮退 | Accessibility ON | 初回設定カードが主役にならない | integration/manual |
| UI-010 | モード | 4択表示 | 起動 | GB/GBC/GBA/DSの4択 | UI test |
| UI-011 | モード | 単一選択 | GBCを選択 | GBCだけ選択状態 | UI test |
| UI-012 | 解像度 | 全10択 | 解像度メニュー展開 | 既存10項目が全て存在 | UI test |
| UI-013 | 組合せ | モードと解像度独立 | GB + DS/256x192 | 選択を保持し開始処理へ渡せる | unit/integration |
| UI-014 | 明るさ | 初期値 | 起動 | 数値6 | UI test |
| UI-015 | 明るさ | 値変更 | Slider操作 | 表示値と既存内部値が一致 | unit/UI |
| UI-016 | コントラスト | 初期値 | 起動 | 数値122 | UI test |
| UI-017 | コントラスト | 値変更 | Slider操作 | 表示値と既存内部値が一致 | unit/UI |
| UI-018 | ディザ | 初期値 | 起動 | ON | UI test |
| UI-019 | ディザ | 切替 | Switch操作 | OFF/ONを開始処理へ渡す | unit/UI |
| UI-020 | 詳細 | 初期折りたたみ | 起動 | ログ/ADBの詳細が前面に出ない | UI test |
| UI-021 | 詳細 | 展開 | 詳細設定・診断をタップ | ログ同期/ADB手順が操作可能 | UI test |
| UI-022 | 主操作 | 停止中 | 初期状態 | 主ボタンは`フィルター開始`1つ | UI test |
| UI-023 | 主操作 | 実行中 | 実行状態へ遷移 | 同位置が`停止`へ切替 | integration/manual |
| UI-024 | 主操作 | 二重主要操作禁止 | 全状態 | 開始と停止を同時に主要ボタン表示しない | UI test |
| UI-025 | Bridge | 開始値受け渡し | 任意設定後開始 | mode/resolution/brightness/contrast/ditherがJava側へ渡る | unit |
| UI-026 | Bridge | status受信 | Java側からstatus更新 | Composeへ即時反映 | unit/UI |
| UI-027 | ログ | ログ同期導線 | 詳細→ログ同期 | 既存ログ同期処理を呼ぶ | integration |
| UI-028 | ADB | ADB導線 | 詳細→ADB手順 | 既存ADB手順を表示 | integration |
| UI-029 | Adaptive | Compact | 幅<840dp | 1ペイン | UI test/manual |
| UI-030 | Adaptive | Expanded | 幅>=840dp | 左プレビュー+右設定の2ペイン | UI test/manual |
| UI-031 | Preview | 文字見本 | Expanded | GAME BOY/数字/英字が表示 | UI test |
| UI-032 | Preview | DMGパレット | Expanded | 0,1,2,3の4階調サンプル | UI test |
| UI-033 | Theme | Light | Light theme | 読めるコントラスト | screenshot/manual |
| UI-034 | Theme | Dark | Dark theme | 読めるコントラスト | screenshot/manual |
| UI-035 | Theme | Dynamic Color | 対応端末 | UIへ適用、DMG previewは固定 | manual |
| UI-036 | A11y | 200%文字 | fontScale 2.0 | 重要項目が切れずスクロール到達可能 | manual |
| UI-037 | A11y | TalkBack | TalkBack ON | ボタン/Slider/Switchの意味と状態を取得可能 | manual |
| UI-038 | A11y | 色非依存 | 実行/停止状態 | 状態が文字でも判別可能 | static/manual |
| BUILD-001 | Toolchain | compileSdk | Gradle設定/CI | 37。CI packageはandroid-37.0 | static/CI |
| BUILD-002 | Toolchain | AGP | Gradle設定 | 9.3.0 stable | static |
| BUILD-003 | Toolchain | Gradle | CI | 9.5.0 | static/CI |
| BUILD-004 | Library | Compose BOM | dependency | 2026.08.00 | static |
| BUILD-005 | Library | Material3 | resolved dependency | 1.4.0系 | dependency/CI |
| BUILD-006 | Library | Activity Compose | dependency | 1.13.0 | static |
| BUILD-007 | Library | Adaptive | dependency | 1.3.0 | static |
| BUILD-008 | Kotlin | Compose compiler | plugin | 2.3.21 | static/CI |
| REG-001 | Regression | font_min | unit test | fg=671, SHA=38bb88...06c5維持 | automated |
| REG-002 | Regression | 日本語8x8 | unit test | 既存日本語テストPASS | automated |
| REG-003 | Regression | APK build | CI | signed debug APK生成 | automated |
| REG-004 | Regression | Java capture/filter | compile | 既存Java処理がコンパイルされる | automated |

## 必須PASSゲート

CIで自動判定できる項目:
- BUILD-001〜008
- REG-001〜004
- UI-001, UI-002, UI-025, UI-026（実装テストを追加できた範囲）

実機確認が必要な項目:
- UI-003〜005
- UI-008〜009
- UI-023
- UI-029〜037の一部

CIで実機項目をPASS扱いしない。APK提出時に未実施項目を明記する。
