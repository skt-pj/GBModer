package com.sktpj.gbmoder;

import android.graphics.Bitmap;
import android.graphics.BitmapShader;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.RuntimeShader;
import android.graphics.Shader;
import android.os.Build;

final class GpuFilterRenderer {
    private static final String AGSL =
            "uniform shader input;\n" +
            "uniform float2 viewSize;\n" +
            "uniform float2 sourceSize;\n" +
            "uniform float2 pixelGrid;\n" +
            "uniform float brightness;\n" +
            "uniform float contrast;\n" +
            "uniform float mode;\n" +
            "uniform float ditherEnabled;\n" +
            "\n" +
            "float bayer4(float2 cell) {\n" +
            "    float x = cell.x - 4.0 * floor(cell.x / 4.0);\n" +
            "    float y = cell.y - 4.0 * floor(cell.y / 4.0);\n" +
            "    if (y < 0.5) {\n" +
            "        if (x < 0.5) return 0.0;\n" +
            "        if (x < 1.5) return 8.0;\n" +
            "        if (x < 2.5) return 2.0;\n" +
            "        return 10.0;\n" +
            "    }\n" +
            "    if (y < 1.5) {\n" +
            "        if (x < 0.5) return 12.0;\n" +
            "        if (x < 1.5) return 4.0;\n" +
            "        if (x < 2.5) return 14.0;\n" +
            "        return 6.0;\n" +
            "    }\n" +
            "    if (y < 2.5) {\n" +
            "        if (x < 0.5) return 3.0;\n" +
            "        if (x < 1.5) return 11.0;\n" +
            "        if (x < 2.5) return 1.0;\n" +
            "        return 9.0;\n" +
            "    }\n" +
            "    if (x < 0.5) return 15.0;\n" +
            "    if (x < 1.5) return 7.0;\n" +
            "    if (x < 2.5) return 13.0;\n" +
            "    return 5.0;\n" +
            "}\n" +
            "\n" +
            "half4 main(float2 coord) {\n" +
            "    float2 safeView = max(viewSize, float2(1.0));\n" +
            "    float2 grid = max(pixelGrid, float2(1.0));\n" +
            "    float2 cell = floor((coord / safeView) * grid);\n" +
            "    float2 samplePos = ((cell + 0.5) / grid) * sourceSize;\n" +
            "    half4 sampled = input.eval(samplePos);\n" +
            "    float3 rgb = float3(sampled.rgb);\n" +
            "    float bayer = bayer4(cell) - 7.5;\n" +
            "\n" +
            "    if (mode < 0.5) {\n" +
            "        float lum = dot(rgb, float3(0.299, 0.587, 0.114));\n" +
            "        lum = ((lum - 0.5) * contrast) + 0.5 + brightness;\n" +
            "        if (ditherEnabled > 0.5) {\n" +
            "            lum += bayer * (7.0 / 255.0);\n" +
            "        }\n" +
            "        lum = clamp(lum, 0.0, 1.0);\n" +
            "        if (lum < 0.25) return half4(15.0/255.0, 56.0/255.0, 15.0/255.0, 1.0);\n" +
            "        if (lum < 0.50) return half4(48.0/255.0, 98.0/255.0, 48.0/255.0, 1.0);\n" +
            "        if (lum < 0.75) return half4(139.0/255.0, 172.0/255.0, 15.0/255.0, 1.0);\n" +
            "        return half4(155.0/255.0, 188.0/255.0, 15.0/255.0, 1.0);\n" +
            "    }\n" +
            "\n" +
            "    rgb = ((rgb - 0.5) * contrast) + 0.5 + brightness;\n" +
            "    if (ditherEnabled > 0.5) {\n" +
            "        rgb += float3(bayer * (2.5 / 255.0));\n" +
            "    }\n" +
            "    rgb = clamp(rgb, 0.0, 1.0);\n" +
            "    float steps = mode > 2.5 ? 63.0 : 31.0;\n" +
            "    rgb = floor((rgb * steps) + 0.5) / steps;\n" +
            "    return half4(half3(rgb), sampled.a);\n" +
            "}\n";

    private final RuntimeShader runtimeShader;
    private final Paint paint;

    GpuFilterRenderer() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) {
            throw new UnsupportedOperationException("RuntimeShader requires Android 13+");
        }
        runtimeShader = new RuntimeShader(AGSL);
        paint = new Paint();
        paint.setAntiAlias(false);
        paint.setFilterBitmap(false);
        paint.setShader(runtimeShader);
    }

    void draw(
            Canvas canvas,
            Bitmap source,
            int viewWidth,
            int viewHeight,
            int targetWidth,
            int targetHeight,
            String mode,
            int brightness,
            int contrast,
            boolean dither
    ) {
        BitmapShader input = new BitmapShader(
                source,
                Shader.TileMode.CLAMP,
                Shader.TileMode.CLAMP
        );
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            input.setFilterMode(BitmapShader.FILTER_MODE_NEAREST);
        }

        runtimeShader.setInputShader("input", input);
        runtimeShader.setFloatUniform("viewSize", Math.max(1, viewWidth), Math.max(1, viewHeight));
        runtimeShader.setFloatUniform("sourceSize", source.getWidth(), source.getHeight());
        runtimeShader.setFloatUniform("pixelGrid", Math.max(1, targetWidth), Math.max(1, targetHeight));
        runtimeShader.setFloatUniform("brightness", brightness / 255.0f);
        runtimeShader.setFloatUniform("contrast", contrast / 100.0f);
        runtimeShader.setFloatUniform("mode", modeValue(mode));
        runtimeShader.setFloatUniform("ditherEnabled", dither ? 1.0f : 0.0f);

        canvas.drawRect(0, 0, Math.max(1, viewWidth), Math.max(1, viewHeight), paint);
    }

    private static float modeValue(String mode) {
        if (GameBoyFilter.MODE_DS.equals(mode)) {
            return 3.0f;
        }
        if (GameBoyFilter.MODE_GBA.equals(mode)) {
            return 2.0f;
        }
        if (GameBoyFilter.MODE_GBC.equals(mode)) {
            return 1.0f;
        }
        return 0.0f;
    }
}
