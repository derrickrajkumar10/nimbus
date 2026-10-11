/// Build-time settings. `--dart-define=NIMBUS_API_URL=<citizen API base>`
/// picks the real API; leaving it empty runs on bundled fixtures.
class AppConfig {
  const AppConfig({this.apiBase});

  factory AppConfig.fromEnvironment() {
    const url = String.fromEnvironment('NIMBUS_API_URL');
    return AppConfig(apiBase: url.isEmpty ? null : Uri.parse(url));
  }

  final Uri? apiBase;

  bool get useFixtures => apiBase == null;
}
