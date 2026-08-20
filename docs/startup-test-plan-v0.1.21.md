# GBModer v0.1.21 起動試験表

| ID | 試験 | 合格条件 |
|---|---|---|
| START-001 | Activity基底クラス | 生成後MainActivityがComponentActivityを継承 |
| START-002 | View tree owner | android.app.Activity継承が生成後ソースに残らない |
| START-003 | Compose UI回帰 | v0.1.20 UI automated gate PASS |
| START-004 | FontMin回帰 | foreground=671かつ基準SHA一致 |
| START-005 | 日本語フォント回帰 | 7,170字形生成確認 |
| START-006 | JVM/Android compile | testDebugUnitTest / assembleDebug PASS |
| START-007 | 配布物 | signed debug APK生成 |

START-001/002を静的起動前提試験としてCIゲートへ追加する。実機起動確認が可能な場合は、ランチャーからMainActivityを開き初期画面が描画されることを最終確認する。
