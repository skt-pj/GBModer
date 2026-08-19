package com.sktpj.gbmoder;

import android.Manifest;
import android.accessibilityservice.AccessibilityServiceInfo;
import android.app.Activity;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.pm.ServiceInfo;
import android.graphics.Color;
import android.media.projection.MediaProjectionManager;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.util.Log;
import android.view.Gravity;
import android.view.View;
import android.view.accessibility.AccessibilityManager;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.SeekBar;
import android.widget.Spinner;
import android.widget.Switch;
import android.widget.TextView;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.List;

public class MainActivity extends Activity {
    private static final String TAG = "GBModerMain";
    private static final int REQUEST_CAPTURE = 1002;
    private static final int REQUEST_NOTIFICATIONS = 1003;

    private MediaProjectionManager projectionManager;
    private Spinner modeSpinner;
    private Spinner resolutionSpinner;
    private SeekBar brightnessSeek;
    private SeekBar contrastSeek;
    private Switch ditherSwitch;
    private TextView brightnessValue;
    private TextView contrastValue;
    private TextView statusText;
    private boolean pendingStartAfterAccessibility = false;
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
                "他アプリをGB / GBC / GBA / Nintendo DS風に表示します。初回のみGBModerのユーザー補助サービスを有効にしてください。",
                14,
                false
        );
        description.setPadding(0, dp(8), 0, dp(20));
        root.addView(description, matchWrap());

        root.addView(text("表示モード", 14, true), matchWrap());
        modeSpinner = new Spinner(this);
        String[] modes = {
                "Game Boy / 4階調",
                "Game Boy Color / 32,768色・同時56色",
                "Game Boy Advance / 32,768色",
                "Nintendo DS / 26万色"
        };
        ArrayAdapter<String> modeAdapter = new ArrayAdapter<>(this, android.R.layout.simple_spinner_item, modes);
        modeAdapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        modeSpinner.setAdapter(modeAdapter);
        root.addView(modeSpinner, matchWrap());

        TextView resolutionLabel = text("解像度", 14, true);
        resolutionLabel.setPadding(0, dp(16), 0, 0);
        root.addView(resolutionLabel, matchWrap());
        resolutionSpinner = new Spinner(this);
        String[] resolutions = {
                "GB / 160×144",
                "GBC / 160×144",
                "GBA / 240×160",
                "DS / 256×192",
                "スマホの元解像度"
        };
        ArrayAdapter<String> resolutionAdapter = new ArrayAdapter<>(
                this,
                android.R.layout.simple_spinner_item,
                resolutions
        );
        resolutionAdapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        resolutionSpinner.setAdapter(resolutionAdapter);
        root.addView(resolutionSpinner, matchWrap());

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
        stopButton.setOnClickListener(v -> stopFilter());
        LinearLayout.LayoutParams stopParams = new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f);
        stopParams.setMarginStart(dp(8));
        buttons.addView(stopButton, stopParams);
        root.addView(buttons, matchWrap());

        statusText = text("停止中", 13, false);
        statusText.setPadding(0, dp(16), 0, 0);
        root.addView(statusText, matchWrap());

        TextView note = text(
                "Android 14以降では対象アプリのウィンドウだけを直接取得するため、GBModer自身のフィルター表示は再取得しません。" +
                        " 通知欄の「解除」からいつでも停止できます。DRM/FLAG_SECURE等で保護された画面は取得できません。",
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

        beginAccessibilityFlow();
    }

    private void beginAccessibilityFlow() {
        pendingStartAfterNotification = false;
        if (!isAccessibilityServiceEnabled()) {
            pendingStartAfterAccessibility = true;
            startActivity(new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS));
            statusText.setText("ユーザー補助で「GBModer screen filter」を有効にしてください");
            return;
        }

        if (FilterAccessibilityService.getInstance() == null) {
            pendingStartAfterAccessibility = true;
            statusText.setText("ユーザー補助サービスの接続を待っています");
            statusText.postDelayed(this::continueAfterAccessibilityIfReady, 500L);
            return;
        }

        startFilterForCurrentPlatform();
    }

    private void continueAfterAccessibilityIfReady() {
        if (!pendingStartAfterAccessibility) {
            return;
        }
        if (isAccessibilityServiceEnabled() && FilterAccessibilityService.getInstance() != null) {
            startFilterForCurrentPlatform();
        }
    }

    private void startFilterForCurrentPlatform() {
        pendingStartAfterAccessibility = false;

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            FilterAccessibilityService accessibilityService = FilterAccessibilityService.getInstance();
            if (accessibilityService == null) {
                statusText.setText("ユーザー補助サービスに接続できません");
                return;
            }

            accessibilityService.startWindowFilter(
                    getSelectedMode(),
                    getSelectedResolution(),
                    getBrightness(),
                    getContrast(),
                    ditherSwitch.isChecked()
            );
            statusText.setText("フィルターを開始しました");
            return;
        }

        requestScreenCapture();
    }

    private void stopFilter() {
        FilterAccessibilityService accessibilityService = FilterAccessibilityService.getInstance();
        if (accessibilityService != null) {
            accessibilityService.stopWindowFilter();
            accessibilityService.clearOverlay();
        }

        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            Intent stopIntent = new Intent(this, FilterCaptureService.class);
            stopIntent.setAction(FilterCaptureService.ACTION_STOP);
            startService(stopIntent);
        }

        statusText.setText("停止しました");
    }

    private boolean isAccessibilityServiceEnabled() {
        AccessibilityManager manager =
                (AccessibilityManager) getSystemService(Context.ACCESSIBILITY_SERVICE);
        if (manager == null || !manager.isEnabled()) {
            return false;
        }

        ComponentName expected = new ComponentName(this, FilterAccessibilityService.class);
        List<AccessibilityServiceInfo> enabledServices =
                manager.getEnabledAccessibilityServiceList(AccessibilityServiceInfo.FEEDBACK_ALL_MASK);
        for (AccessibilityServiceInfo info : enabledServices) {
            if (info == null || info.getResolveInfo() == null) {
                continue;
            }
            ServiceInfo serviceInfo = info.getResolveInfo().serviceInfo;
            if (serviceInfo == null) {
                continue;
            }
            ComponentName actual = new ComponentName(serviceInfo.packageName, serviceInfo.name);
            if (expected.equals(actual)) {
                return true;
            }
        }
        return false;
    }

    private void requestScreenCapture() {
        pendingStartAfterAccessibility = false;
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
        if (pendingStartAfterAccessibility) {
            statusText.postDelayed(this::continueAfterAccessibilityIfReady, 300L);
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
            beginAccessibilityFlow();
        } else {
            pendingStartAfterNotification = false;
            statusText.setText("通知欄の解除を使うため通知権限が必要です");
        }
    }

    @Override
    @SuppressWarnings("deprecation")
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);

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
        serviceIntent.putExtra(FilterCaptureService.EXTRA_RESOLUTION, getSelectedResolution());
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
        if (position == 3) return GameBoyFilter.MODE_DS;
        return GameBoyFilter.MODE_GB;
    }

    private String getSelectedResolution() {
        int position = resolutionSpinner.getSelectedItemPosition();
        if (position == 1) return GameBoyFilter.RESOLUTION_GBC;
        if (position == 2) return GameBoyFilter.RESOLUTION_GBA;
        if (position == 3) return GameBoyFilter.RESOLUTION_DS;
        if (position == 4) return GameBoyFilter.RESOLUTION_NATIVE;
        return GameBoyFilter.RESOLUTION_GB;
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
