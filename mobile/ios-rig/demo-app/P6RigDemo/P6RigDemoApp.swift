// P6RigDemoApp.swift — P6 iOS RIG DEMO (LAB ONLY — see policy §1/§7 banner
// in AppDelegate.swift). SwiftUI app entry: replace the contents of the file
// Xcode generates for the project's @main App with this.

import SwiftUI

@main
struct P6RigDemoApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) var delegate

    var body: some Scene {
        WindowGroup {
            BridgeHost()
        }
    }
}

/// Hosts the WKWebView demo view controller (where the deliberate C7 flaw
/// lives — see ViewController.swift).
struct BridgeHost: UIViewControllerRepresentable {
    func makeUIViewController(context: Context) -> ViewController {
        ViewController()
    }
    func updateUIViewController(_ uiViewController: ViewController, context: Context) {}
}
