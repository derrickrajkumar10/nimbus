import 'dart:async';
import 'dart:typed_data';

import '../contracts/nimbus.dart';
import '../data/api_exception.dart';
import '../data/nimbus_api.dart';
import '../domain/geo.dart';

/// Where a photo Report is, from upload to its Reading.
sealed class ReportState {
  const ReportState();
}

class Uploading extends ReportState {
  const Uploading();
}

/// Sent; the Verifier is looking at it.
class Verifying extends ReportState {
  const Verifying(this.reportId);
  final String reportId;
}

/// The Reading for this Report, with its Segment, the Segment's latest risk
/// row, and the Hazards within 50 m of it.
class Verified extends ReportState {
  const Verified(this.reading, this.segment, this.risk, this.hazards);
  final Reading reading;
  final Segment segment;
  final SegmentRisk? risk;
  final List<Hazard> hazards;
}

/// No Reading after 30 s. Polling goes on, and a push will follow.
class StillChecking extends ReportState {
  const StillChecking(this.reportId);
  final String reportId;
}

class Failed extends ReportState {
  const Failed(this.e);
  final ApiException e;
}

/// A sent Report handed to the reveal: the photo and the states still to come.
class ReportSubmission {
  const ReportSubmission({required this.photo, required this.reportId, required this.states});
  final Uint8List photo;
  final String reportId;
  final Stream<ReportState> states;
}

/// Uploads a photo Report and waits for its Reading: `uploadUrl`, then the
/// photo `PUT`, then `createReport`, then `readings?report_id=` every 2 s.
class ReportFlow {
  ReportFlow(this.api, this.runId);

  final NimbusApi api;
  final String runId;

  static const pollEvery = Duration(seconds: 2);
  static const stillCheckingAfter = Duration(seconds: 30);

  /// Polling stops here; the push carries the result after that.
  static const giveUpAfter = Duration(minutes: 5);

  static const hazardRadiusM = 50.0;

  /// Single-subscription. Cancelling stops the polling before its next call.
  Stream<ReportState> submit(Uint8List jpeg, GeoPoint location) {
    var cancelled = false;
    late final StreamController<ReportState> out;
    out = StreamController<ReportState>(
      onListen: () => _run(jpeg, location, out.add, () => cancelled).whenComplete(out.close),
      onCancel: () => cancelled = true,
    );
    return out.stream;
  }

  Future<void> _run(Uint8List jpeg, GeoPoint location, void Function(ReportState) emit, bool Function() cancelled) async {
    emit(const Uploading());
    final String reportId;
    try {
      final ticket = await api.uploadUrl(runId);
      await api.uploadPhoto(ticket, jpeg);
      reportId = ticket.reportId;
      await api.createReport(reportId: reportId, runId: runId, location: location);
    } on ApiException catch (e) {
      emit(Failed(e));
      return;
    }
    emit(Verifying(reportId));

    // Time is counted in polls, never read from the clock.
    final stillAt = stillCheckingAfter.inMilliseconds ~/ pollEvery.inMilliseconds;
    final maxPolls = giveUpAfter.inMilliseconds ~/ pollEvery.inMilliseconds;
    for (var poll = 1; poll <= maxPolls; poll++) {
      await Future<void>.delayed(pollEvery);
      if (cancelled()) return;
      try {
        final found = await api.readings(runId, reportId: reportId);
        if (found.isNotEmpty) {
          final verified = await _verified(found.first);
          if (!cancelled()) emit(verified);
          return;
        }
      } on ApiException {
        // A failed poll is retried on the next one.
      }
      if (poll == stillAt && !cancelled()) emit(StillChecking(reportId));
    }
  }

  Future<Verified> _verified(Reading reading) async {
    final segment = (await api.segments()).firstWhere((s) => s.segmentId == reading.segmentId);
    SegmentRisk? latest;
    try {
      for (final r in await api.risk(runId)) {
        if (r.segmentId == segment.segmentId && (latest == null || r.simTime.isAfter(latest.simTime))) latest = r;
      }
    } on ApiException {
      latest = null;
    }
    List<Hazard> hazards;
    try {
      hazards = [
        for (final h in await api.hazards(runId))
          if (distanceToLineM(h.location, segment.geometry) <= hazardRadiusM) h,
      ];
    } on ApiException {
      hazards = const [];
    }
    return Verified(reading, segment, latest, hazards);
  }
}
