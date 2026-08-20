# GBModer v0.1.21 起動修正仕様

## 1. 事象
v0.1.20 は ComposeView を Activity の content view として使用するが、生成後 MainActivity が android.app.Activity を継承している。

## 2. 原因
ComposeView / AbstractComposeView は ViewTreeLifecycleOwner と ViewTreeSavedStateRegistryOwner が伝播する View hierarchy を要求する。androidx.activity.ComponentActivity はこれらの owner を初期化する。

## 3. 修正範囲
- 生成後 MainActivity を androidx.activity.ComponentActivity 継承へ変更する。
- Compose UI、MediaProjection、Accessibility、ログ、フィルター、文字レンダラーの挙動は変更しない。
- 既存の v0.1.20 UI仕様を維持する。

## 4. 受入条件
- 生成後 MainActivity に `import androidx.activity.ComponentActivity;` が存在する。
- 生成後 MainActivity が `extends ComponentActivity` である。
- 旧 `extends Activity` が残っていない。
- UI仕様自動ゲートがPASSする。
- FontMinRenderer基準SHAと日本語8x8フォント検証がPASSする。
- signed debug APKが生成される。
