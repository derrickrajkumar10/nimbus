import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:nimbus_app/contracts/nimbus.dart';

// Same rule as tool/sync_contracts.sh: until PR #61 is on this branch, the
// Dart models come from CONTRACTS_REF rather than the working tree.
const _defaultRef = 'origin/derrick/contracts-dart-nullable';
const _sourceDart = '../contracts/generated/dart/nimbus.dart';

Future<String> _expectedDart() async {
  final working = File(_sourceDart).readAsStringSync();
  if (working.contains('int? minutesToFlood;')) return working;
  final ref = Platform.environment['CONTRACTS_REF'] ?? _defaultRef;
  final shown = await Process.run('git', ['show', '$ref:contracts/generated/dart/nimbus.dart']);
  if (shown.exitCode != 0) fail('git show $ref failed: ${shown.stderr}');
  return shown.stdout as String;
}

List<dynamic> _fixture(String name) =>
    jsonDecode(File('assets/fixtures/$name').readAsStringSync()) as List<dynamic>;

List<T> _parse<T>(String name, T Function(Map<String, dynamic>) fromJson) =>
    _fixture(name).map((j) => fromJson(j as Map<String, dynamic>)).toList();

void main() {
  test('synced contracts match the source', () async {
    expect(File('lib/contracts/nimbus.dart').readAsStringSync(), await _expectedDart(),
        reason: 'lib/contracts/nimbus.dart is stale: run tool/sync_contracts.sh');

    String names(Directory d) => (d
            .listSync()
            .whereType<File>()
            .map((f) => f.uri.pathSegments.last)
            .where((n) => n.endsWith('.json'))
            .toList()
          ..sort())
        .join(',');
    final source = Directory('../contracts/fixtures');
    final copies = Directory('assets/fixtures');
    expect(names(copies), names(source), reason: 'fixture set differs: run tool/sync_contracts.sh');
    for (final f in source.listSync().whereType<File>().where((f) => f.path.endsWith('.json'))) {
      final name = f.uri.pathSegments.last;
      expect(File('assets/fixtures/$name').readAsBytesSync(), f.readAsBytesSync(),
          reason: '$name is stale: run tool/sync_contracts.sh');
    }
  });

  test('every fixture parses', () {
    expect(_parse('segments.json', Segment.fromJson), hasLength(21));
    final risk = _parse('risk.json', SegmentRisk.fromJson);
    expect(risk, hasLength(21));
    expect(risk.any((r) => r.minutesToFlood == null), isTrue);
    expect(_parse('readings.json', Reading.fromJson), isNotEmpty);
    expect(_parse('hazards.json', Hazard.fromJson), isNotEmpty);
    expect(_parse('sos.json', Sos.fromJson), isNotEmpty);
    final routes = _parse('routes.json', RouteResponse.fromJson);
    expect(routes[1].geometry, isNull);
    expect(_parse('route_requests.json', RouteRequest.fromJson), hasLength(2));
  });
}
