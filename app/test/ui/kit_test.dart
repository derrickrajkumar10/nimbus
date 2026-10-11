import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nimbus_app/contracts/nimbus.dart';
import 'package:nimbus_app/l10n/app_localizations.dart';
import 'package:nimbus_app/ui/icons.dart';
import 'package:nimbus_app/ui/theme/tide_colors.dart';
import 'package:nimbus_app/ui/widgets/band_chip.dart';
import 'package:nimbus_app/ui/widgets/round_button.dart';

Widget _host(Widget child) => MaterialApp(home: Scaffold(body: Center(child: child)));

void main() {
  test('bandColor maps flooded to water and likely to likely', () {
    expect(bandColor(RiskBand.FLOODED), TideColors.water);
    expect(bandColor(RiskBand.LIKELY), TideColors.likely);
    expect(bandColor(RiskBand.WATCH), TideColors.watch);
    expect(bandColor(RiskBand.LOW), TideColors.low);
  });

  testWidgets('nimbusIcon renders every NimbusIcon without throwing', (tester) async {
    for (final icon in NimbusIcon.values) {
      await tester.pumpWidget(_host(nimbusIcon(icon, size: 24, color: TideColors.text)));
      expect(tester.takeException(), isNull, reason: icon.name);
    }
  });

  testWidgets('RoundButton shows its label and calls onTap', (tester) async {
    var taps = 0;
    await tester.pumpWidget(_host(RoundButton(
      onTap: () => taps++,
      label: 'Report',
      child: nimbusIcon(NimbusIcon.camera),
    )));
    expect(find.text('Report'), findsOneWidget);
    await tester.tap(find.byType(RoundButton));
    expect(taps, 1);
  });

  testWidgets('BandChip formats 100 minutes as 1h 40m', (tester) async {
    final l = lookupAppLocalizations(const Locale('en'));
    await tester.pumpWidget(_host(BandChip(band: RiskBand.LIKELY, minutesToFlood: 100, l: l)));
    expect(find.text('Likely · 1h 40m'), findsOneWidget);

    await tester.pumpWidget(_host(BandChip(band: RiskBand.LOW, minutesToFlood: 100, l: l)));
    expect(find.text('Low'), findsOneWidget);
  });
}
