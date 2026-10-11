import '../contracts/nimbus.dart';

/// The waterline as a fraction of the figure's height, from the feet.
double waterFraction(DepthBand d) => switch (d) {
      DepthBand.DRY => 0,
      DepthBand.ANKLE => 0.09,
      DepthBand.KNEE => 0.28,
      DepthBand.WAIST => 0.50,
      DepthBand.ABOVE_WAIST => 0.72,
    };
