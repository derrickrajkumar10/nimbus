import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nimbus_app/contracts/nimbus.dart';
import 'package:nimbus_app/data/api_exception.dart';
import 'package:nimbus_app/domain/place_view.dart';
import 'package:nimbus_app/ui/screens/report_screen.dart';
import 'package:nimbus_app/ui/screens/reveal_screen.dart';
import 'package:nimbus_app/ui/widgets/tide_map.dart';

import '../support/fake_api.dart';
import '../support/fixtures.dart';
import '../support/host.dart';

// A real 1x1 image, so the preview can decode it.
final _photo = base64Decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=');

/// Records where Reports were sent; optionally refuses them.
class ReportApi extends FakeApi {
  ReportApi({super.places, this.refuse, this.noReading = false});

  final ApiException? refuse;
  final bool noReading;
  final sentAt = <GeoPoint>[];
  var polls = 0;

  @override
  Future<List<Reading>> readings(String runId, {String? reportId}) {
    if (reportId != null) polls++;
    return noReading && reportId != null ? Future.value(const []) : super.readings(runId, reportId: reportId);
  }

  @override
  Future<Report> createReport({required String reportId, required String runId, required GeoPoint location, String? note}) {
    sentAt.add(location);
    final e = refuse;
    return e != null ? Future.error(e) : super.createReport(reportId: reportId, runId: runId, location: location);
  }
}

void main() {
  setUp(() {
    final view = TestWidgetsFlutterBinding.instance.platformDispatcher.views.first;
    view.physicalSize = const Size(390, 844);
    view.devicePixelRatio = 1;
  });
  tearDown(() => TestWidgetsFlutterBinding.instance.platformDispatcher.views.first.reset());

  final overrides = [
    mapEnabledProvider.overrideWithValue(false),
    photoPickerProvider.overrideWithValue((_) async => _photo),
  ];

  Future<void> photoAndSend(WidgetTester tester) async {
    await tester.tap(find.text('Take a photo'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));
    await tester.ensureVisible(find.text('Send'));
    await tester.tap(find.text('Send'));
    for (var i = 0; i < 5; i++) {
      await tester.pump(const Duration(milliseconds: 100));
    }
  }

  testWidgets('a Replay that has not started is explained, with Home and Try again', (tester) async {
    final api = ReportApi(refuse: const ApiException(409, ApiException.runNotStarted, 'not started'));
    await pumpScreen(tester, const ReportScreen(), api: api, overrides: overrides);
    await photoAndSend(tester);
    expect(find.text("The Replay hasn't started yet. Start it, then try again."), findsOneWidget);
    expect(find.text('Try again'), findsOneWidget);
    expect(find.text('Home'), findsOneWidget);
  });

  testWidgets('in a Replay the pin starts on the first Saved Place and Verifying opens the reveal', (tester) async {
    final base = place('pl-far', 'Office', ['27320162-0']);
    final far = PlaceView(
      place: SavedPlace(
        deviceId: base.place.deviceId,
        kind: base.place.kind,
        label: base.place.label,
        location: GeoPoint(lat: 12.981, lon: 80.226),
        placeId: base.id,
        segmentIds: base.place.segmentIds,
      ),
      runIds: base.runIds,
    );
    final api = ReportApi(places: [far]);
    await pumpScreen(tester, const ReportScreen(), api: api, overrides: overrides);
    await photoAndSend(tester);
    expect((api.sentAt.single.lat, api.sentAt.single.lon), (12.981, 80.226));
    expect(find.byType(RevealScreen), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
    await tester.pump(const Duration(seconds: 5));
  });

  testWidgets('polling stops once nothing listens to the Report', (tester) async {
    final api = ReportApi(noReading: true);
    await pumpScreen(tester, const ReportScreen(), api: api, overrides: overrides);
    await photoAndSend(tester);
    expect(find.byType(RevealScreen), findsOneWidget);
    await tester.pump(const Duration(seconds: 4));
    expect(api.polls, greaterThan(0), reason: 'the reveal keeps polling while open');
    await tester.pumpWidget(const SizedBox());
    await tester.pump(const Duration(seconds: 3));
    final after = api.polls;
    await tester.pump(const Duration(seconds: 20));
    expect(api.polls, after);
  });
}
