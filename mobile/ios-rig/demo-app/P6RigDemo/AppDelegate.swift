// AppDelegate.swift — P6 iOS RIG DEMO — DELIBERATELY FLAWED-BY-DESIGN (LAB ONLY).
//
// AUTHORIZATION — LAB ONLY per docs/governance/policy.md §1 and §7: run only
// on the project's iOS Simulator / owned test devices. This app exists to
// demonstrate the C7 class (app-authored bridge input-validation flaws) as the
// iOS analogue of the Android C1 rig: on iOS there is NO platform bridge
// surface to exploit (addJavascriptInterface has no equivalent — see
// mobile/docs/ios-surfaces.md §1), so the flaw must be the app author's own
// bridge design. That is the contrast finding this app embodies.
//
// NOTE: this delegate is NOT @main — the app entry point is
// P6RigDemoApp.swift (SwiftUI lifecycle + UIApplicationDelegateAdaptor), which
// matches what a current Xcode "App" template generates.

import UIKit

final class AppDelegate: NSObject, UIApplicationDelegate {

    // Custom-scheme entry (p6rigdemo://...): lets the harness measure scheme
    // dispatch (C4-shape reachability on iOS). The URL is handed to the
    // WebView in ViewController — verbatim, trusted (part of the deliberate
    // flaw: the demo trusts any payload that reaches it).
    func application(_ app: UIApplication,
                     open url: URL,
                     options: [UIApplication.OpenURLOptionsKey: Any] = [:]) -> Bool {
        NotificationCenter.default.post(name: .p6rigOpenURL, object: url)
        return true
    }
}

extension Notification.Name {
    static let p6rigOpenURL = Notification.Name("p6rigOpenURL")
}
