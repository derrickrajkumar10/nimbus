import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nimbus_app/ui/widgets/tide_background.dart';

const _tops = [0.3, 0.42, 0.54, 0.66, 0.78, 0.9];

Widget _host({required bool disableAnimations}) => MediaQuery(
      data: MediaQueryData(size: const Size(360, 720), disableAnimations: disableAnimations),
      child: const Directionality(
        textDirection: TextDirection.ltr,
        child: TideBackground(layerTops: _tops),
      ),
    );

void main() {
  test('layerRects returns one top per layer, increasing', () {
    final tops = TideBackground.layerRects(const Size(360, 720), _tops);
    expect(tops, hasLength(_tops.length));
    expect(tops.first, closeTo(216, 0.001));
    for (var i = 1; i < tops.length; i++) {
      expect(tops[i], greaterThan(tops[i - 1]));
    }
  });

  testWidgets('animates by default', (tester) async {
    await tester.pumpWidget(_host(disableAnimations: false));
    expect(tester.hasRunningAnimations, isTrue);
  });

  testWidgets('does not animate when disableAnimations is true', (tester) async {
    await tester.pumpWidget(_host(disableAnimations: true));
    expect(tester.hasRunningAnimations, isFalse);
  });
}
