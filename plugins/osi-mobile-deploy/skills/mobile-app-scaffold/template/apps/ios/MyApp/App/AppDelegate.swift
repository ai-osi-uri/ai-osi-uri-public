import UIKit
import FirebaseCore
import os.log

/// UIKit-side bridging for the SwiftUI `MyAppApp`.
///
/// Firebase is configured **only if** GoogleService-Info.plist is present in the
/// bundle. This guard prevents startup crashes when the plist is missing from a
/// build (e.g. CI without the secret, or a preview build without Firebase).
final class AppDelegate: NSObject, UIApplicationDelegate {

    static let log = OSLog(subsystem: "com.example.myapp", category: "AppDelegate")

    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        configureFirebaseIfPossible()
        return true
    }

    /// Guarded Firebase configuration.
    ///
    /// Rationale: `FirebaseApp.configure()` crashes with SIGABRT if called
    /// without a valid GoogleService-Info.plist. We check for the file and
    /// bail out gracefully so the app can at least render its Hello World.
    private func configureFirebaseIfPossible() {
        guard let path = Bundle.main.path(forResource: "GoogleService-Info", ofType: "plist"),
              let opts = FirebaseOptions(contentsOfFile: path) else {
            os_log("GoogleService-Info.plist not found — skipping Firebase configuration",
                   log: AppDelegate.log, type: .info)
            return
        }
        guard FirebaseApp.app() == nil else { return }   // idempotent
        FirebaseApp.configure(options: opts)
        os_log("Firebase configured (project=%{public}@)",
               log: AppDelegate.log, type: .info, opts.projectID ?? "?")
    }
}
