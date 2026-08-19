package com.sktpj.gbmoder;

import android.Manifest;
import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.media.projection.MediaProjectionManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.util.Log;
import android.view.Gravity;
import android.view.View;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.SeekBar;
import android.widget.Spinner;
import android.widget.Switch;
import android.widget.TextView;

import java.lang.reflect.Field;
import java.lang.reflect.Method;

public class MainActivity extends Activity {
    private static final String TAG = "GBModerMain";
    private static final int REQUEST_OVERLAY = 1001;
    private static final int REQUEST_CAPTURE = 1002;
    private static final int REQUEST_NOTIFICATIONS = 1003;

    private MediaProjectionManager projectionManager;
    private Spinner modeSpinner;
    private SeekBar brightnessSeek;
    private SeekBar contrastSeek;
    private Switch ditherSwitch;
    private TextView brightnessValue;
    private TextView contrastValue;
    private TextView statusText;
    private boolean pendingStartAfterOverlay = false;
    private boolean pendingStartAfterNotification = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        projectionManager = (MediaProjectionManager) getSystemService(Context.MEDIA_PROJECTION_SERVICE);
        setContentView(buildContentView());
    }

    private View buildContentView() {
        int pad = dp(20);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(pad, pad, pad, pad);
        root.setBackgroundColor(Color.rgb(226, 230, 214));

        TextView title = text("GBModer", 26, true);
        root.addView(title, matchWrap());

        TextView description = text(
                "他アプリをGame Boy風に表示します。開始後のAndroid共有画面では「1つのアプリ」を選択してください。",
                14,
                false
        );
        description.setPadding(0, dp(8), 0, dp(20));
        root.addView(description, matchWrap());

        root.addView(text("表示モード", 14, true), matchWrap());
        modeSpinner = new Spinner(this);
        String[] modes = {
                "Game Boy / 4階調",
                "Game Boy Color / RGB555",
                "Game Boy Advance / RGB555"
        };
        ArrayAdapter<String> adapter = new ArrayAdapter<>(this, android.R.layout.simple_spinner_item, modes);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        modeSpinner.setAdapter(adapter);
        root.addView(modeSpinner, matchWrap());

        brightnessValue = text("明るさ: 6", 14, false);
        brightnessValue.setPadding(0, dp(16), 0, 0);
        root.addView(brightnessValue, matchWrap());
        brightnessSeek = new SeekBar(this);
        brightnessSeek.setMax(160);
        brightnessSeek.setProgress(86);
        brightnessSeek.setOnSeekBarChangeListener(simpleSeekListener(() ->
                brightnessValue.setText("明るさ: " + getBrightness())));
        root.addView(brightnessSeek, matchWrap());

        contrastValue = text("コントラスト: 122", 14, false);
        contrastValue.setPadding(0, dp(8), 0, 0);
        root.addView(contrastValue, matchWrap());
        contrastSeek = new SeekBar(this);
        contrastSeek.setMax(150);
        contrastSeek.setProgress(72);
        contrastSeek.setOnSeekBarChangeListener(simpleSeekListener(() ->
                contrastValue.setText("コントラスト: " + getContrast())));
        root.addView(contrastSeek, matchWrap());

        ditherSwitch = new Switch(this);
        ditherSwitch.setText("ディザ");
        ditherSwitch.setChecked(true);
        ditherSwitch.setPadding(0, dp(8), 0, dp(16));
        root.addView(ditherSwitch, matchWrap());

        LinearLayout buttons = new LinearLayout(this);
        buttons.setOrientation(LinearLayout.HORIZONTAL);
        buttons.setGravity(Gravity.CENTER_VERTICAL);

        Button startButton = new Button(this);
        startButton.setText("フィルター開始");
        startButton.setOnClickListener(v -> beginStartFlow());
        buttons.addView(startButton, new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f));

        Button stopButton = new Button(this);
        stopButton.setText("停止");
        stopButton.setOnClickListener(v -> {
            Intent stopIntent = new Intent(this, FilterCaptureService.class);
            stopIntent.setAction(FilterCaptureService.ACTION_STOP);
            startService(stopIntent);
            statusText.setText("停止しました");
        });
        LinearLayout.LayoutParams stopParams = new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f);
        stopParams.setMarginStart(dp(8));
        buttons.addView(stopButton, stopParams);
        root.addView(buttons, matchWrap());

        statusText = text("停止中", 13, false);
        statusText.setPadding(0, dp(16), 0, 0);
        root.addView(statusText, matchWrap());

        TextView note = text(
                "画面全体共有ではGBModer自身の表示が再キャプチャされるため使用しません。" +
                        " Android 17以降では全画面共有を選択肢から除外し、Android 14〜16では共有画面で必ず「1つのアプリ」を選択してください。" +
                        " 通知欄の「解除」からいつでも停止できます。 DRM/FLAG_SECURE等で保護された画面は取得できません。",
                12,
                false
        );
        note.setPadding(0, dp(20), 0, 0);
        root.addView(note, matchWrap());

        return root;
    }

    private void beginStartFlow() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU
                && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            pendingStartAfterNotification = true;
            requestPermissions(
                    new String[]{Manifest.permission.POST_NOTIFICATIONS},
                    REQUEST_NOTIFICATIONS
            );
            statusText.setText("通知欄に解除を表示するため通知を許可してください");
            return;
        }

        beginOverlayFlow();
    }

    private void beginOverlayFlow() {
        pendingStartAfterNotification = false;
        if (!Settings.canDrawOverlays(this)) {
            pendingStartAfterOverlay = true;
            Intent overlayIntent = new Intent(
                    Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                    Uri.parse("package:" + getPackageName())
            );
            startActivityForResult(overlayIntent, REQUEST_OVERLAY);
            statusText.setText("「他のアプリの上に表示」を許可してください");
            return;
        }
        requestScreenCapture();
    }

    private void requestScreenCapture() {
        pendingStartAfterOverlay = false;
        statusText.setText("共有する他アプリを選択してください");
        startActivityForResult(createSingleAppPreferredCaptureIntent(), REQUEST_CAPTURE);
    }

    private Intent createSingleAppPreferredCaptureIntent() {
        if (Build.VERSION.SDK_INT >= 37) {
            try {
                Class<?> configClass = Class.forName("android.media.projection.MediaProjectionConfig");
                Class<?> builderClass = Class.forName("android.media.projection.MediaProjectionConfig$Builder");
                Object builder = builderClass.getDeclaredConstructor().newInstance();

                Field displayField = configClass.getField("PROJECTION_SOURCE_DISPLAY");
                Field appField = configClass.getField("PROJECTION_SOURCE_APP");
                int displaySource = displayField.getInt(null);
                int appSource = appField.getInt(null);

                Method setSourceEnabled = builderClass.getMethod(
                        "setSourceEnabled",
                        int.class,
                        boolean.class
                );
                setSourceEnabled.invoke(builder, displaySource, false);
                setSourceEnabled.invoke(builder, appSource, true);

                Method setInitiallySelectedSource = builderClass.getMethod(
                        "setInitiallySelectedSource",
                        int.class
                );
                setInitiallySelectedSource.invoke(builder, appSource);

                Object config = builderClass.getMethod("build").invoke(builder);
                Method createIntent = MediaProjectionManager.class.getMethod(
                        "createScreenCaptureIntent",
                        configClass
                );
                Intent intent = (Intent) createIntent.invoke(projectionManager, config);
                if (intent != null) {
                    Log.i(TAG, "MediaProjection picker restricted to single-app source");
                    return intent;
                }
            } catch (Throwable error) {
                Log.w(TAG, "Single-app-only picker unavailable; using user-choice picker", error);
            }
        }

        Log.i(TAG, "MediaProjection user-choice picker; select one app, not entire display");
        return projectionManager.createScreenCaptureIntent();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (pendingStartAfterOverlay && Settings.canDrawOverlays(this)) {
            requestScreenCapture();
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);

        if (requestCode != REQUEST_NOTIFICATIONS) {
            return;
        }

        boolean granted = grantResults.length > 0
                && grantResults[0] == PackageManager.PERMISSION_GRANTED;
        if (granted && pendingStartAfterNotification) {
            beginOverlayFlow();
        } else {
            pendingStartAfterNotification = false;
            statusText.setText("通知欄の解除を使うため通知権限が必要です");
        }
    }

    @Override
    @SuppressWarnings("deprecation")
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);

        if (requestCode == REQUEST_OVERLAY) {
            if (!Settings.canDrawOverlays(this)) {
                pendingStartAfterOverlay = false;
                statusText.setText("オーバーレイ権限が必要です");
            }
            return;
        }

        if (requestCode != REQUEST_CAPTURE) {
            return;
        }

        if (resultCode != RESULT_OK || data == null) {
            statusText.setText("画面共有がキャンセルされました");
            return;
        }

        Intent serviceIntent = new Intent(this, FilterCaptureService.class);
        serviceIntent.setAction(FilterCaptureService.ACTION_START);
        serviceIntent.putExtra(FilterCaptureService.EXTRA_RESULT_CODE, resultCode);
        serviceIntent.putExtra(FilterCaptureService.EXTRA_RESULT_DATA, data);
        serviceIntent.putExtra(FilterCaptureService.EXTRA_MODE, getSelectedMode());
        serviceIntent.putExtra(FilterCaptureService.EXTRA_BRIGHTNESS, getBrightness());
        serviceIntent.putExtra(FilterCaptureService.EXTRA_CONTRAST, getContrast());
        serviceIntent.putExtra(FilterCaptureService.EXTRA_DITHER, ditherSwitch.isChecked());
        startForegroundService(serviceIntent);
        statusText.setText("フィルターを開始しました");
    }

    private String getSelectedMode() {
        int position = modeSpinner.getSelectedItemPosition();
        if (position == 1) return GameBoyFilter.MODE_GBC;
        if (position == 2) return GameBoyFilter.MODE_GBA;
        return GameBoyFilter.MODE_GB;
    }

    private int getBrightness() {
        return brightnessSeek.getProgress() - 80;
    }

    private int getContrast() {
        return contrastSeek.getProgress() + 50;
    }

    private SeekBar.OnSeekBarChangeListener simpleSeekListener(Runnable update) {
        return new SeekBar.OnSeekBarChangeListener() {
            @Override
            public void onProgressChanged(SeekBar seekBar, int progress, boolean fromUser) {
                update.run();
            }

            @Override
            public void onStartTrackingTouch(SeekBar seekBar) {
            }

            @Override
            public void onStopTrackingTouch(SeekBar seekBar) {
            }
        };
    }

    private TextView text(String value, int sp, boolean bold) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(sp);
        view.setTextColor(Color.rgb(38, 48, 32));
        if (bold) {
            view.setTypeface(view.getTypeface(), android.graphics.Typeface.BOLD);
        }
        return view;
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
