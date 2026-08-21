package com.sktpj.gbmoder

import android.content.Context
import androidx.compose.material3.LocalTextStyle
import androidx.compose.material3.Text as MaterialText
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.TextLayoutResult
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.TextUnit

/**
 * Transitional localization bridge for the existing Compose UI.
 *
 * The app historically stored Japanese copy directly in UI/state code. This bridge keeps those
 * stable internal status tokens while rendering them through Android resources, so system and
 * per-app locale changes take effect without changing filter/conversion behavior.
 */
object GbModerLocalization {
    private val exact = mapOf(
        "停止中" to R.string.stopped_idle,
        "共通" to R.string.common_section,
        "フィルター" to R.string.filter_section,
        "変換" to R.string.conversion_section,
        "対象ファイルを選択" to R.string.conversion_source_select,
        "出力先を選択" to R.string.conversion_output_select,
        "対応していないファイル形式です" to R.string.unsupported_file_type,
        "変換しました" to R.string.conversion_completed,
        "表示モード" to R.string.display_mode,
        "解像度" to R.string.resolution,
        "スマホの元解像度 / 100%" to R.string.native_resolution,
        "端末比は5%刻みで選択できます。表示モードの色・階調処理と解像度の出力サイズを組み合わせて適用します。" to R.string.resolution_help,
        "明るさ" to R.string.brightness,
        "コントラスト" to R.string.contrast,
        "ディザ" to R.string.dither,
        "階調境界をパターン化して見かけの階調を補います。" to R.string.dither_description,
        "文字を読みやすくする" to R.string.readable_text,
        "画面内の文字を認識し、低解像度向け8×8フォントで再描画します。GB / 160×144で有効です。" to R.string.readable_text_description,
        "フィルターを停止" to R.string.filter_stop,
        "フィルターを開始" to R.string.filter_start_accessibility,
        "停止" to R.string.stop,
        "フィルター開始" to R.string.filter_start,
        "初回設定" to R.string.first_setup,
        "ユーザー補助を有効にして、画面のテキストを取得します。" to R.string.enable_accessibility_description,
        "ユーザー補助を有効化" to R.string.enable_accessibility,
        "ファイル変換" to R.string.file_conversion,
        "現在の表示モード・解像度・明るさ・コントラスト・ディザで変換して保存します。" to R.string.file_conversion_description,
        "写真をPNGに変換" to R.string.convert_photo_png,
        "動画をMP4に変換" to R.string.convert_video_mp4,
        "3Dモデルを変換" to R.string.convert_model,
        "3Dモデル対応: PLY / OBJ / glTF / GLB" to R.string.model_supported,
        "標準（推奨）" to R.string.standard_recommended,
        "互換モード" to R.string.compatibility_mode,
        "詳細設定・診断" to R.string.advanced_diagnostics,
        "画面取得方式・ログ・ADB" to R.string.capture_log_adb,
        "画面取得方式" to R.string.capture_method,
        "互換モード（Android 14+）" to R.string.compatibility_mode_android14,
        "MediaProjectionを使用します。通常はこちらを使用してください。" to R.string.media_projection_description,
        "Accessibility Windowを使用します。Android 14以降向けの互換モードです。" to R.string.accessibility_window_description,
        "ログ同期" to R.string.video_diagnostics_action,
        "ADB手順" to R.string.adb_steps,
        "画面共有では『1つのアプリ』を選択してください。画面全体を選ぶと自己キャプチャ検出で停止します。DRM / FLAG_SECUREで保護された画面は取得できません。" to R.string.capture_note,
        "プレビュー" to R.string.preview,
        "GB (DMG) パレット" to R.string.gb_palette,
        "変換元ファイルを選択してください" to R.string.choose_source_initial,
        "保存先は未選択です" to R.string.output_not_selected,
        "変換元ファイルは未選択です" to R.string.source_not_selected,
        "3Dモデルは .ply / .obj / .gltf / .glb に対応しています" to R.string.unsupported_model_extension,
        "変換元" to R.string.source,
        "未選択" to R.string.not_selected,
        "ファイルを選択" to R.string.select_file,
        "ファイルを選び直す" to R.string.reselect_file,
        "保存先を選択してください" to R.string.choose_output,
        "保存先を選んで変換" to R.string.choose_output_and_convert,
        "閉じる" to R.string.close,
        "写真を変換" to R.string.convert_photo_title,
        "動画を変換" to R.string.convert_video_title,
        "現在の表示設定を適用し、PNGとして保存します。" to R.string.photo_conversion_description,
        "現在の表示設定を適用し、MP4として保存します。" to R.string.video_conversion_description,
        "現在の表示設定を色へ適用します。対応形式: PLY / OBJ / glTF / GLB。" to R.string.model_conversion_description,
        "通知欄に解除を表示するため通知を許可してください" to R.string.notification_permission_request,
        "ユーザー補助で「GBModer screen filter」を有効にしてください" to R.string.accessibility_enable_instruction,
        "ユーザー補助サービスの接続を待っています" to R.string.accessibility_waiting,
        "ユーザー補助サービスに接続できません" to R.string.accessibility_connection_failed,
        "表示モード × 解像度の組み合わせで開始しました" to R.string.filter_started,
        "MediaProjection高速キャプチャで開始しました" to R.string.filter_started,
        "停止しました" to R.string.stopped,
        "同期する性能ログがありません" to R.string.no_performance_log,
        "ログの同期先を選択してください" to R.string.choose_log_destination,
        "ログ同期をキャンセルしました" to R.string.log_sync_cancelled,
        "ログを同期中です" to R.string.log_syncing,
        "ログを同期しました" to R.string.log_synced,
        "画面共有がキャンセルされました" to R.string.capture_cancelled,
        "通知欄の解除を使うため通知権限が必要です" to R.string.notification_permission_required,
        "共有する他アプリを選択してください" to R.string.choose_app_to_share,
    )

    @JvmStatic
    fun localize(context: Context, raw: String): String {
        if (raw.isBlank()) return raw
        exact[raw]?.let { return context.getString(it) }

        if (raw.startsWith("端末比 / ") && raw.endsWith("%")) {
            raw.removePrefix("端末比 / ").removeSuffix("%").toIntOrNull()?.let { percent ->
                return context.getString(R.string.phone_ratio_format, percent)
            }
        }
        prefix(context, raw, "変換中: ", R.string.converting_format)?.let { return it }
        prefix(context, raw, "保存しました: ", R.string.saved_format)?.let { return it }
        prefix(context, raw, "変換できませんでした: ", R.string.conversion_failed_format)?.let { return it }
        prefix(context, raw, "選択済み: ", R.string.selected_format)?.let { return it }
        prefix(context, raw, "ログ同期に失敗しました: ", R.string.log_sync_failed_format)?.let { return it }

        val language = context.resources.configuration.locales[0]?.language.orEmpty()
        if (language == "ja") return raw

        // Converter internals still emit stable Japanese diagnostic tokens. Keep common progress useful
        // in non-Japanese locales and never leak untranslated UI copy for uncommon error paths.
        if (containsJapaneseKana(raw)) {
            return when {
                raw.contains("写真") -> context.getString(R.string.convert_photo_title)
                raw.contains("動画") || raw.contains("音声") -> context.getString(R.string.convert_video_title)
                raw.contains("3D") || raw.contains("PLY") || raw.contains("OBJ") || raw.contains("glTF") || raw.contains("GLB") -> context.getString(R.string.convert_model)
                else -> context.getString(R.string.status_localized_fallback)
            }
        }
        return raw
    }

    private fun prefix(context: Context, raw: String, prefix: String, resource: Int): String? {
        if (!raw.startsWith(prefix)) return null
        return context.getString(resource, raw.removePrefix(prefix))
    }

    private fun containsJapaneseKana(value: String): Boolean =
        value.any { it in '\u3040'..'\u30ff' }
}

@Composable
internal fun Text(
    text: String,
    modifier: Modifier = Modifier,
    color: Color = Color.Unspecified,
    fontSize: TextUnit = TextUnit.Unspecified,
    fontStyle: FontStyle? = null,
    fontWeight: FontWeight? = null,
    fontFamily: FontFamily? = null,
    letterSpacing: TextUnit = TextUnit.Unspecified,
    textDecoration: TextDecoration? = null,
    textAlign: TextAlign? = null,
    lineHeight: TextUnit = TextUnit.Unspecified,
    overflow: TextOverflow = TextOverflow.Clip,
    softWrap: Boolean = true,
    maxLines: Int = Int.MAX_VALUE,
    minLines: Int = 1,
    onTextLayout: ((TextLayoutResult) -> Unit)? = null,
    style: TextStyle = LocalTextStyle.current,
) {
    MaterialText(
        text = GbModerLocalization.localize(LocalContext.current, text),
        modifier = modifier,
        color = color,
        fontSize = fontSize,
        fontStyle = fontStyle,
        fontWeight = fontWeight,
        fontFamily = fontFamily,
        letterSpacing = letterSpacing,
        textDecoration = textDecoration,
        textAlign = textAlign,
        lineHeight = lineHeight,
        overflow = overflow,
        softWrap = softWrap,
        maxLines = maxLines,
        minLines = minLines,
        onTextLayout = onTextLayout,
        style = style,
    )
}
