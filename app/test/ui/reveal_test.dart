import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nimbus_app/contracts/nimbus.dart';
import 'package:nimbus_app/report/report_flow.dart';
import 'package:nimbus_app/ui/screens/reveal_screen.dart';
import 'package:nimbus_app/ui/widgets/tide_map.dart';

import '../support/fixtures.dart';
import '../support/host.dart';

final _photo = base64Decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=');
const _segmentId = '27480309-1';

/// The fixture Reading rd-0001 with its Segment, risk row and Hazard.
Verified _verified({double? thresholdMm}) {
  final row = fixtureJson('risk.json').firstWhere((j) => j['segment_id'] == _segmentId);
  return Verified(
    fixtureReading(),
    fixtureSegments().firstWhere((s) => s.segmentId == _segmentId),
    SegmentRisk.fromJson({...row, 'flood_threshold_mm': ?thresholdMm}),
    fixtureHazards(),
  );
}

void main() {
  final noMap = [mapEnabledProvider.overrideWithValue(false)];
  late StreamController<ReportState> states;

  setUp(() {
    states = StreamController<ReportState>.broadcast();
    final view = TestWidgetsFlutterBinding.instance.platformDispatcher.views.first;
    view.physicalSize = const Size(390, 844);
    view.devicePixelRatio = 1;
  });
  tearDown(() {
    states.close();
    TestWidgetsFlutterBinding.instance.platformDispatcher.views.first.reset();
    TestWidgetsFlutterBinding.instance.platformDispatcher.clearAccessibilityFeaturesTestValue();
  });

  Future<void> pumpReveal(WidgetTester tester) => pumpScreen(
        tester,
        RevealScreen(submission: ReportSubmission(photo: _photo, reportId: 'rp-1', states: states.stream)),
        overrides: noMap,
      );

  /// Steps through every stage (the waves and ripples never settle).
  Future<void> playAll(WidgetTester tester) async {
    for (var i = 0; i < 100; i++) {
      await tester.pump(const Duration(milliseconds: 100));
    }
  }

  Future<void> reveal(WidgetTester tester, Verified v) async {
    await pumpReveal(tester);
    states.add(v);
    await playAll(tester);
  }

  testWidgets('shows Knee-deep after the stages complete', (tester) async {
    await pumpReveal(tester);
    expect(find.text('Verifying…'), findsOneWidget);
    expect(find.text('Knee-deep'), findsNothing);
    states.add(_verified());
    await playAll(tester);
    expect(find.text('Knee-deep'), findsOneWidget);
    expect(find.text('முழங்கால் அளவு நீர்'), findsOneWidget);
  });

  testWidgets('shows two red crosses and one green check', (tester) async {
    await reveal(tester, _verified());
    expect(find.byKey(const ValueKey('pass-no')), findsNWidgets(2));
    expect(find.byKey(const ValueKey('pass-ok')), findsOneWidget);
  });

  testWidgets('shows the open manhole warning', (tester) async {
    await reveal(tester, _verified());
    expect(find.text('Open manhole here. Routes keep 30 m clear.'), findsOneWidget);
  });

  testWidgets('fixture threshold shows confirmedPrediction', (tester) async {
    await reveal(tester, _verified());
    expect(find.text('Your photo confirmed the prediction.'), findsOneWidget);
    expect(find.text('You taught the map.'), findsNothing);
  });

  testWidgets('a learned story counts to 55 mm', (tester) async {
    await reveal(tester, _verified(thresholdMm: 55));
    expect(find.text('You taught the map.'), findsOneWidget);
    expect(find.text('Velachery Main Road now floods at 55 mm (was 68).'), findsOneWidget);
  });

  testWidgets('StillChecking shows the calm message and Home button', (tester) async {
    await pumpReveal(tester);
    states.add(const StillChecking('rp-1'));
    await playAll(tester);
    expect(find.text('Still checking your photo'), findsOneWidget);
    expect(find.text('Home'), findsOneWidget);
    expect(find.text('Try again'), findsOneWidget);
  });

  testWidgets('disableAnimations shows the final frame immediately', (tester) async {
    tester.platformDispatcher.accessibilityFeaturesTestValue = const FakeAccessibilityFeatures(disableAnimations: true);
    await pumpReveal(tester);
    states.add(_verified(thresholdMm: 55));
    await tester.pump();
    await tester.pump();
    expect(find.text('Knee-deep'), findsOneWidget);
    expect(find.byKey(const ValueKey('pass-no')), findsNWidgets(2));
    expect(find.text('Velachery Main Road now floods at 55 mm (was 68).'), findsOneWidget);
  });
}
