// MustPost の実運用コードから抜粋（2026-07 時点）。
//
// 重要ポイント:
//   1. AppDelegate と SwiftUI 側 DeepLinkHandler の両方に **同じ** 判定を置く。
//      SwiftUI の .onOpenURL{} は AppDelegate を経由せず直接 DeepLinkHandler に
//      飛ぶ経路があるので、片方だけだと初回起動しか動かない。
//   2. #if DEBUG || DEV でガード。Release-Prod では絶対に入らない。
//   3. Google Sign-In のコールバック URL (`com.googleusercontent.apps.xxx://`) と
//      衝突しないよう、debug 分岐で早期 return true する（Google 側に投げる前）。

import UIKit
import FirebaseCore
import FirebaseAuth

// MARK: - AppDelegate side

final class AppDelegate: NSObject, UIApplicationDelegate {

    func application(
        _ app: UIApplication,
        open url: URL,
        options: [UIApplication.OpenURLOptionsKey: Any] = [:]
    ) -> Bool {
        #if DEBUG || DEV
        // DEBUG-only backdoor for Simulator QA:
        //   mustpost://debug/signin?token=XXX
        if url.scheme == "mustpost",
           url.host == "debug",
           url.path == "/signin",
           let components = URLComponents(url: url, resolvingAgainstBaseURL: false),
           let token = components.queryItems?.first(where: { $0.name == "token" })?.value,
           !token.isEmpty {
            Logger.app.info("DEBUG deep link signin invoked")
            Task { @MainActor in
                do {
                    _ = try await AuthService.shared.signInWithCustomToken(token)
                    Logger.app.info("DEBUG signin succeeded")
                } catch {
                    Logger.app.error("DEBUG signin failed: \(error.localizedDescription)")
                }
            }
            return true
        }
        #endif

        // Google Sign-In consumes its own callback URL first; if it returns
        // false we forward to DeepLinkHandler.
        if AuthService.shared.handleGoogleURL(url) {
            return true
        }
        return DeepLinkHandler.shared.handleIncomingURL(url)
    }
}

// MARK: - SwiftUI-side DeepLinkHandler

@MainActor
public final class DeepLinkHandler: ObservableObject {

    public static let shared = DeepLinkHandler()

    @Published public var pendingRoute: Route?

    private init() {}

    @discardableResult
    public func handleIncomingURL(_ url: URL) -> Bool {
        // DEBUG-only Simulator QA backdoor. Fires here because SwiftUI's
        // .onOpenURL{} routes to DeepLinkHandler before AppDelegate on some
        // iOS versions. Handled at both entry points to be safe.
        //
        // NOTE: this is INTENTIONALLY not wrapped in #if DEBUG because the
        // signInWithCustomToken() call it invokes IS wrapped. If someone
        // accidentally publishes a release build with a Custom Token in the
        // clipboard, the AuthService method won't exist and the call fails.
        if url.scheme == "mustpost",
           url.host == "debug",
           url.path == "/signin",
           let comps = URLComponents(url: url, resolvingAgainstBaseURL: false),
           let token = comps.queryItems?.first(where: { $0.name == "token" })?.value,
           !token.isEmpty {
            Logger.deepLink.info("DEBUG signin deep link received (len=\(token.count))")
            #if DEBUG || DEV
            Task { @MainActor in
                do {
                    _ = try await AuthService.shared.signInWithCustomToken(token)
                    Logger.deepLink.info("DEBUG signin succeeded")
                } catch {
                    Logger.deepLink.error("DEBUG signin failed: \(error.localizedDescription)")
                }
            }
            #endif
            return true
        }

        // ... 通常の URL 分岐 ...
        return false
    }
}
