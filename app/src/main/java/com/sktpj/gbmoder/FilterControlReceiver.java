package com.sktpj.gbmoder;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.util.Log;

public class FilterControlReceiver extends BroadcastReceiver {
    public static final String ACTION_STOP = "com.sktpj.gbmoder.action.ACCESSIBILITY_STOP";
    private static final String TAG = "GBModerControl";

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null || !ACTION_STOP.equals(intent.getAction())) {
            return;
        }

        FilterAccessibilityService service = FilterAccessibilityService.getInstance();
        if (service != null) {
            service.stopWindowFilter();
            Log.i(TAG, "Window filter stopped from notification");
        } else {
            Log.w(TAG, "Stop requested but accessibility service is not connected");
        }
    }
}
