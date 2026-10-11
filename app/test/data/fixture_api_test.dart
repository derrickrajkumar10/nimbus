import 'package:fake_async/fake_async.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nimbus_app/contracts/nimbus.dart';
import 'package:nimbus_app/data/fixture_api.dart';
import 'package:nimbus_app/data/install_id.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../support/file_bundle.dart';

void main() {
  test('readings for a new report are empty, then rd-0001 after 3 s', () {
    fakeAsync((async) {
      final api = FixtureNimbusApi(FileBundle(), delay: const Duration(milliseconds: 600));
      List<Reading>? got;
      String? reportId;

      api.uploadUrl('replay-michaung').then((t) => reportId = t.reportId);
      async.elapse(const Duration(seconds: 1));
      api.createReport(
        reportId: reportId!,
        runId: 'replay-michaung',
        location: GeoPoint(lat: 12.9777, lon: 80.2212),
      );
      async.elapse(const Duration(milliseconds: 600));

      api.readings('replay-michaung', reportId: reportId).then((r) => got = r);
      async.elapse(const Duration(milliseconds: 600));
      expect(got, isEmpty);

      async.elapse(const Duration(seconds: 2));
      api.readings('replay-michaung', reportId: reportId).then((r) => got = r);
      async.elapse(const Duration(milliseconds: 600));
      expect(got!.single.readingId, 'rd-0001');
    });
  });

  test('live run returns no risk rows', () async {
    final api = FixtureNimbusApi(FileBundle(), delay: Duration.zero);
    expect(await api.risk('live'), isEmpty);
    expect(await api.risk('replay-michaung'), hasLength(21));
  });

  test('putPlace works out segment ids and lists the place', () async {
    final api = FixtureNimbusApi(FileBundle(), delay: Duration.zero);
    final view = await api.putPlace(
      'pl-1',
      label: 'Bike parking',
      kind: SavedPlaceKind.VEHICLE_PARKING,
      location: GeoPoint(lat: 12.9777428, lon: 80.2212061),
      radiusM: 150,
      runIds: ['replay-michaung'],
    );
    expect(view.place.segmentIds, contains('27480309-1'));
    expect((await api.savedPlaces()).single.id, 'pl-1');
    await api.deletePlace('pl-1');
    expect(await api.savedPlaces(), isEmpty);
  });

  test('route returns the detour for a two-wheeler and no_safe_route for a car', () async {
    final api = FixtureNimbusApi(FileBundle(), delay: Duration.zero);
    RouteRequest req(VehicleType v) => RouteRequest(
          runId: 'replay-michaung',
          origin: GeoPoint(lat: 12.9711, lon: 80.2161),
          destination: GeoPoint(lat: 12.9747, lon: 80.2164),
          vehicle: v,
        );
    expect((await api.route(req(VehicleType.TWO_WHEELER))).status, RouteStatus.OK);
    expect((await api.route(req(VehicleType.CAR))).status, RouteStatus.NO_SAFE_ROUTE);
  });

  test('loadInstallId is stable and 8–80 chars', () async {
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    final first = await loadInstallId(prefs);
    expect(first, matches(RegExp(r'^[A-Za-z0-9:_-]{8,80}$')));
    expect(first, startsWith('inst-'));
    expect(first, hasLength(37));
    expect(await loadInstallId(prefs), first);
  });

  test('places survive a restart when given prefs', () async {
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    await FixtureNimbusApi(FileBundle(), delay: Duration.zero, prefs: prefs).putPlace(
      'pl-1',
      label: 'Home',
      kind: SavedPlaceKind.HOME,
      location: GeoPoint(lat: 12.9777428, lon: 80.2212061),
      runIds: ['replay-michaung'],
    );
    final restarted = FixtureNimbusApi(FileBundle(), delay: Duration.zero, prefs: prefs);
    final places = await restarted.savedPlaces();
    expect(places.single.place.label, 'Home');
    expect(places.single.runIds, ['replay-michaung']);
  });
}
