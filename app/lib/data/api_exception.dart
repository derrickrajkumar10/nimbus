/// An error from the citizen API, parsed from its `{"error", "message"}`
/// body. Status 0 with code `offline` means the request never got an answer.
class ApiException implements Exception {
  const ApiException(this.status, this.code, [this.message = '']);

  const ApiException.offline([String message = 'No connection'])
      : this(0, offlineCode, message);

  final int status;
  final String code;
  final String message;

  // The codes the UI handles.
  static const offlineCode = 'offline';
  static const runNotStarted = 'run_not_started';
  static const routingUnavailable = 'routing_unavailable';
  static const photoNotUploaded = 'photo_not_uploaded';
  static const tooManyPlaces = 'too_many_places';

  bool get isOffline => code == offlineCode;

  @override
  String toString() => 'ApiException($status $code: $message)';
}
