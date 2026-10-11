import 'dart:typed_data';

import 'package:fake_async/fake_async.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nimbus_app/contracts/nimbus.dart';
import 'package:nimbus_app/data/api_exception.dart';
import 'package:nimbus_app/report/report_flow.dart';
import 'package:nimbus_app/state/providers.dart';
import 'package:nimbus_app/ui/widgets/tide_map.dart';

import '../support/fake_api.dart';

/// No Reading ever arrives.
class UnverifiedApi extends FakeApi {
  var polls = 0;

  @override
  Future<List<Reading>> readings(String runId, {String? reportId}) async {
    polls++;
    return const [];
  }
}

/// The Replay hasn't started.
class NotStartedApi extends FakeApi {
  @override
  Future<Report> createReport({required String reportId, required String runId, required GeoPoint location, String? note}) =>
      Future.error(const ApiException(409, ApiException.runNotStarted, 'Run replay-michaung has not started'));
}

final _jpeg = Uint8List.fromList([0xFF, 0xD8, 0xFF, 0xD9]);

/// Collects every state [flow] emits over [time] of fake time.
List<ReportState> _run(ReportFlow Function() flow, Duration time) {
  final states = <ReportState>[];
  fakeAsync((async) {
    final sub = flow().submit(_jpeg, velachery).listen(states.add);
    async.elapse(time);
    sub.cancel();
    async.flushMicrotasks();
  });
  return states;
}

void main() {
  test('emits Uploading, Verifying, Verified for the fixture reading', () {
    final states = _run(() => ReportFlow(FakeApi(), demoRun), const Duration(seconds: 8));
    expect(states.map((s) => s.runtimeType).toList(), [Uploading, Verifying, Verified]);
    final reportId = (states[1] as Verifying).reportId;
    expect(reportId, matches(RegExp(r'^rp-[0-9A-Z]{26}$')));
    final v = states[2] as Verified;
    expect(v.reading.readingId, 'rd-0001');
    expect(v.segment.segmentId, '27480309-1');
    expect(v.risk?.segmentId, '27480309-1');
    expect([for (final h in v.hazards) h.hazardId], ['hz-0001']);
  });

  test('emits StillChecking after 30 s with no reading', () {
    final early = _run(() => ReportFlow(UnverifiedApi(), demoRun), const Duration(seconds: 29));
    expect(early.last, isA<Verifying>());
    final states = _run(() => ReportFlow(UnverifiedApi(), demoRun), const Duration(seconds: 31));
    expect(states.map((s) => s.runtimeType).toList(), [Uploading, Verifying, StillChecking]);
    expect((states.last as StillChecking).reportId, (states[1] as Verifying).reportId);
  });

  test('run_not_started becomes Failed with that code', () {
    final states = _run(() => ReportFlow(NotStartedApi(), demoRun), const Duration(seconds: 2));
    expect(states.map((s) => s.runtimeType).toList(), [Uploading, Failed]);
    expect((states.last as Failed).e.code, ApiException.runNotStarted);
  });

  test('polling stops when the listener cancels', () {
    final api = UnverifiedApi();
    fakeAsync((async) {
      final sub = ReportFlow(api, demoRun).submit(_jpeg, velachery).listen((_) {});
      async.elapse(const Duration(seconds: 5));
      sub.cancel();
      async.flushMicrotasks();
      final polls = api.polls;
      async.elapse(const Duration(seconds: 20));
      expect(api.polls, polls);
    });
  });
}
