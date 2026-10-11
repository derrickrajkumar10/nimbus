import '../contracts/nimbus.dart';

/// How a Segment's Flood Threshold moved from its Baseline within this Run.
class ThresholdStory {
  const ThresholdStory({required this.from, required this.to});

  final double from;
  final double to;

  /// A Reading nudged the threshold down (more than rounding noise).
  bool get learned => to < from - 0.5;
}

ThresholdStory thresholdStory(Segment s, SegmentRisk r) =>
    ThresholdStory(from: s.baselineThresholdMm, to: r.floodThresholdMm);
