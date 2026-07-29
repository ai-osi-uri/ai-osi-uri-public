// MustPost の AuthService から抜粋。keychainError 17995 を soft-success として
// 扱うヘルパと、DEBUG 用の Custom Token サインインメソッド。

import Foundation
import FirebaseAuth

@MainActor
public final class AuthService: NSObject, ObservableObject {

    public static let shared = AuthService()

    // MARK: - DEBUG-only Custom Token sign-in

    #if DEBUG || DEV
    /// DEBUG-only: sign in with a Firebase Custom Token issued by the backend/IAM.
    /// Used from Simulator via deep link `mustpost://debug/signin?token=XXX`
    /// so Claude/QA can reach signed-in screens without going through
    /// Google/Apple UI (which is IME-cursed in the Simulator).
    @discardableResult
    public func signInWithCustomToken(_ token: String) async throws -> AuthDataResult {
        Logger.auth.info("DEBUG signInWithCustomToken invoked (len=\(token.count))")
        let auth = try await Self.signInIgnoringKeychainError {
            try await Auth.auth().signIn(withCustomToken: token)
        }
        try? await refreshClaims(forceRefresh: true)
        if auth == nil {
            // Keychain persist failed but sign-in itself may have succeeded server-side.
            if Auth.auth().currentUser == nil {
                throw APIError.internalError("Sign-in failed and currentUser is nil")
            }
            // Re-attempt to get an AuthDataResult; caller usually discards it.
            return try await Auth.auth().signIn(withCustomToken: token)
        }
        return auth!
    }
    #endif

    // MARK: - Keychain-error resilience

    /// Wraps a Firebase sign-in call and swallows `.keychainError` (17995),
    /// which happens in the iOS Simulator when the app isn't code-signed with
    /// keychain-access-groups. Sign-in itself still succeeds on the server;
    /// only local persistence fails. Returns nil if we ignored a keychain error
    /// so the caller can consult `Auth.auth().currentUser`.
    private static func signInIgnoringKeychainError(
        _ op: () async throws -> AuthDataResult
    ) async throws -> AuthDataResult? {
        do {
            return try await op()
        } catch let error as NSError {
            // FirebaseAuth keychain error = 17995
            // Underlying macOS keychain code = -34018 (errSecMissingEntitlement)
            let underlying = error.userInfo["NSUnderlyingError"] as? NSError
            let isKeychain =
                error.code == 17995 ||
                underlying?.code == -34018 ||
                error.localizedDescription.lowercased().contains("keychain")
            if isKeychain {
                Logger.auth.warning(
                    "Firebase sign-in threw keychain error but user may still be signed in; treating as soft success."
                )
                return nil
            }
            throw error
        }
    }
}
