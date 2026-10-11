import 'package:nimbus_app/contracts/nimbus.dart';
import 'package:nimbus_app/data/fixture_api.dart';

import 'file_bundle.dart';

/// The fixture API with no delay, plus hooks to make single calls fail.
class FakeApi extends FixtureNimbusApi {
  FakeApi() : super(FileBundle(), delay: Duration.zero);

  /// Replaces `risk()` when set; the call number starts at 1.
  Future<List<SegmentRisk>> Function(String runId, int call)? onRisk;
  int riskCalls = 0;

  @override
  Future<List<SegmentRisk>> risk(String runId) {
    riskCalls++;
    final hook = onRisk;
    return hook != null ? hook(runId, riskCalls) : super.risk(runId);
  }
}
