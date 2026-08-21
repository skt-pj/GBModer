package com.sktpj.gbmoder;

import android.app.Activity;
import android.content.Intent;
import android.database.Cursor;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.provider.OpenableColumns;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;

import java.util.Locale;

public final class MediaConversionActivity extends Activity {
    public static final String EXTRA_KIND = "kind";
    public static final String EXTRA_MODE = "mode";
    public static final String EXTRA_RESOLUTION = "resolution";
    public static final String EXTRA_BRIGHTNESS = "brightness";
    public static final String EXTRA_CONTRAST = "contrast";
    public static final String EXTRA_DITHER = "dither";

    public static final String KIND_PHOTO = "photo";
    public static final String KIND_VIDEO = "video";
    public static final String KIND_MODEL = "model";

    private static final int REQUEST_OPEN_SOURCE = 2101;
    private static final int REQUEST_CREATE_OUTPUT = 2102;

    private String kind;
    private MediaFileConverter.Options options;
    private Uri sourceUri;
    private String sourceName;
    private String modelExtension;
    private TextView statusText;
    private ProgressBar progressBar;
    private Button closeButton;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        Intent intent = getIntent();
        kind = intent.getStringExtra(EXTRA_KIND);
        if (!KIND_PHOTO.equals(kind) && !KIND_VIDEO.equals(kind) && !KIND_MODEL.equals(kind)) {
            finish();
            return;
        }

        options = new MediaFileConverter.Options(
                intent.getStringExtra(EXTRA_MODE),
                intent.getStringExtra(EXTRA_RESOLUTION),
                intent.getIntExtra(EXTRA_BRIGHTNESS, 6),
                intent.getIntExtra(EXTRA_CONTRAST, 122),
                intent.getBooleanExtra(EXTRA_DITHER, true)
        );

        setContentView(buildContentView());
        if (savedInstanceState == null) {
            statusText.post(this::openSourcePicker);
        }
    }

    private View buildContentView() {
        int pad = dp(20);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(pad, pad, pad, pad);
        root.setGravity(Gravity.CENTER_HORIZONTAL);
        root.setBackgroundColor(Color.rgb(245, 245, 245));

        TextView title = new TextView(this);
        title.setText(getKindTitle());
        title.setTextSize(22f);
        title.setTextColor(Color.BLACK);
        title.setGravity(Gravity.CENTER_HORIZONTAL);
        root.addView(title, matchWrap());

        statusText = new TextView(this);
        statusText.setText("変換元を選択します");
        statusText.setTextSize(15f);
        statusText.setTextColor(Color.DKGRAY);
        statusText.setPadding(0, dp(20), 0, dp(16));
        statusText.setGravity(Gravity.CENTER_HORIZONTAL);
        root.addView(statusText, matchWrap());

        progressBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progressBar.setMax(100);
        progressBar.setProgress(0);
        progressBar.setVisibility(View.GONE);
        root.addView(progressBar, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        ));

        closeButton = new Button(this);
        closeButton.setText("キャンセル");
        closeButton.setOnClickListener(v -> finish());
        LinearLayout.LayoutParams closeParams = matchWrap();
        closeParams.topMargin = dp(20);
        root.addView(closeButton, closeParams);

        return root;
    }

    private void openSourcePicker() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        if (KIND_PHOTO.equals(kind)) {
            intent.setType("image/*");
        } else if (KIND_VIDEO.equals(kind)) {
            intent.setType("video/*");
        } else {
            intent.setType("*/*");
            intent.putExtra(Intent.EXTRA_MIME_TYPES, new String[]{
                    "model/gltf+json",
                    "model/gltf-binary",
                    "application/octet-stream",
                    "text/plain"
            });
        }
        startActivityForResult(intent, REQUEST_OPEN_SOURCE);
    }

    @Override
    @SuppressWarnings("deprecation")
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQUEST_OPEN_SOURCE) {
            if (resultCode != RESULT_OK || data == null || data.getData() == null) {
                finish();
                return;
            }
            sourceUri = data.getData();
            sourceName = queryDisplayName(sourceUri);
            if (sourceName == null || sourceName.isEmpty()) {
                sourceName = getDefaultInputName();
            }
            if (KIND_MODEL.equals(kind)) {
                modelExtension = extensionOf(sourceName);
                if (!MediaFileConverter.isSupportedModelExtension(modelExtension)) {
                    showError("3Dモデルは .ply / .obj / .gltf / .glb に対応しています");
                    return;
                }
            }
            openOutputPicker();
            return;
        }

        if (requestCode == REQUEST_CREATE_OUTPUT) {
            if (resultCode != RESULT_OK || data == null || data.getData() == null) {
                showError("保存先の選択をキャンセルしました");
                return;
            }
            startConversion(data.getData());
        }
    }

    private void openOutputPicker() {
        Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType(getOutputMimeType());
        intent.putExtra(Intent.EXTRA_TITLE, buildOutputName());
        startActivityForResult(intent, REQUEST_CREATE_OUTPUT);
        statusText.setText("保存先を選択してください");
    }

    private void startConversion(Uri outputUri) {
        progressBar.setVisibility(View.VISIBLE);
        progressBar.setProgress(0);
        closeButton.setEnabled(false);
        closeButton.setText("変換中");
        statusText.setText("変換中: " + sourceName);

        new Thread(() -> {
            try {
                MediaFileConverter.Progress progress = (percent, message) -> runOnUiThread(() -> {
                    progressBar.setProgress(Math.max(0, Math.min(100, percent)));
                    if (message != null && !message.isEmpty()) {
                        statusText.setText(message);
                    }
                });

                if (KIND_PHOTO.equals(kind)) {
                    MediaFileConverter.convertPhoto(this, sourceUri, outputUri, options, progress);
                } else if (KIND_VIDEO.equals(kind)) {
                    MediaFileConverter.convertVideo(this, sourceUri, outputUri, options, progress);
                } else {
                    MediaFileConverter.convertModel(
                            this,
                            sourceUri,
                            outputUri,
                            modelExtension,
                            options,
                            progress
                    );
                }

                runOnUiThread(() -> {
                    progressBar.setProgress(100);
                    statusText.setText("変換して保存しました: " + buildOutputName());
                    closeButton.setEnabled(true);
                    closeButton.setText("閉じる");
                });
            } catch (Throwable error) {
                runOnUiThread(() -> showError(
                        error.getMessage() == null ? error.getClass().getSimpleName() : error.getMessage()
                ));
            }
        }, "GBModerFileConversion").start();
    }

    private void showError(String message) {
        progressBar.setVisibility(View.GONE);
        statusText.setText("変換できませんでした: " + message);
        closeButton.setEnabled(true);
        closeButton.setText("閉じる");
    }

    private String getKindTitle() {
        if (KIND_PHOTO.equals(kind)) return "写真を変換";
        if (KIND_VIDEO.equals(kind)) return "動画を変換";
        return "3Dモデルを変換";
    }

    private String getDefaultInputName() {
        if (KIND_PHOTO.equals(kind)) return "image";
        if (KIND_VIDEO.equals(kind)) return "video";
        return "model.gltf";
    }

    private String buildOutputName() {
        String base = sourceName == null ? "gbmoder" : sourceName;
        int dot = base.lastIndexOf('.');
        if (dot > 0) {
            base = base.substring(0, dot);
        }
        if (KIND_PHOTO.equals(kind)) return base + "-gbmoder.png";
        if (KIND_VIDEO.equals(kind)) return base + "-gbmoder.mp4";
        return base + "-gbmoder." + modelExtension;
    }

    private String getOutputMimeType() {
        if (KIND_PHOTO.equals(kind)) return "image/png";
        if (KIND_VIDEO.equals(kind)) return "video/mp4";
        if ("gltf".equals(modelExtension)) return "model/gltf+json";
        if ("glb".equals(modelExtension)) return "model/gltf-binary";
        if ("obj".equals(modelExtension)) return "text/plain";
        return "application/octet-stream";
    }

    private String queryDisplayName(Uri uri) {
        try (Cursor cursor = getContentResolver().query(
                uri,
                new String[]{OpenableColumns.DISPLAY_NAME},
                null,
                null,
                null
        )) {
            if (cursor != null && cursor.moveToFirst()) {
                int index = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                if (index >= 0) {
                    return cursor.getString(index);
                }
            }
        } catch (Throwable ignored) {
        }
        return null;
    }

    private static String extensionOf(String name) {
        int dot = name == null ? -1 : name.lastIndexOf('.');
        if (dot < 0 || dot == name.length() - 1) return "";
        return name.substring(dot + 1).toLowerCase(Locale.ROOT);
    }

    private LinearLayout.LayoutParams matchWrap() {
        return new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
