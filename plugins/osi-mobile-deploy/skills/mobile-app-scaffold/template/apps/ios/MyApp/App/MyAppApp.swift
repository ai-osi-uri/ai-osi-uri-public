import SwiftUI

/// Root SwiftUI App entry point for MyApp.
///
/// Firebase configuration and UIKit-lifecycle hooks live in `AppDelegate`
/// which is bridged in via `@UIApplicationDelegateAdaptor`.
///
/// This is the Hello World shell. Real feature screens go under `Features/`.
@main
struct MyAppApp: App {

    @UIApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}
