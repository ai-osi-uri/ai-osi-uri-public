import SwiftUI

/// Hello World for the freshly-scaffolded MyApp.
///
/// Replace with real feature screens. Keep the structure so that
/// `mobile-app-smoke-test` can at least detect a successful launch.
struct ContentView: View {
    var body: some View {
        VStack(spacing: 24) {
            Image(systemName: "sparkles")
                .font(.system(size: 64))
                .foregroundStyle(.tint)

            Text("Hello, MyApp!")
                .font(.title)
                .bold()

            Text("Built with AI OSI URI osi-mobile-deploy")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(uiColor: .systemBackground))
    }
}

#Preview {
    ContentView()
}
