import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/rank.dart';
import '../../l10n/app_localizations.dart';
import '../../state/providers.dart';
import '../format.dart';
import '../icons.dart';
import '../routes.dart';
import '../theme/tide_colors.dart';
import '../widgets/pill_button.dart';
import '../widgets/place_row.dart';
import '../widgets/round_button.dart';
import '../widgets/tide_background.dart';
import '../widgets/wordmark.dart';

/// Home: what to do now, then each Saved Place on its own wave, the worst on
/// the deepest one at the bottom.
class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  static const _bottomBar = 104.0;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final snapshot = ref.watch(riskProvider).value ?? RiskSnapshot.empty;
    final places = ref.watch(placesProvider).value ?? const [];
    final alerts = ref.watch(lastAlertProvider);
    final ranked = rankPlaces(places, snapshot.bySegment);
    final needYou = ranked.where((s) => s.severity >= 1).length;

    return Scaffold(
      body: LayoutBuilder(builder: (context, box) {
        final safeTop = MediaQuery.paddingOf(context).top;
        final waveStart = math.max(box.maxHeight * 0.32, safeTop + 176);
        final n = math.max(ranked.length, 1);
        final room = box.maxHeight - waveStart - _bottomBar;
        final spacing = (room / n).clamp(58.0, 74.0);
        final height = math.max(box.maxHeight, waveStart + n * spacing + _bottomBar);
        final rowTops = [for (var i = 0; i < n; i++) waveStart + i * spacing];
        final layerTops = [
          for (final t in rowTops) t / height,
          (waveStart + n * spacing) / height,
        ];

        return Stack(children: [
          SingleChildScrollView(
            child: SizedBox(
              height: height,
              child: TideBackground(
                layerTops: layerTops,
                colors: tideShades(layerTops.length),
                child: Stack(children: [
                  Positioned(
                    top: safeTop,
                    left: 0,
                    right: 0,
                    child: _Header(
                      runId: ref.watch(runIdProvider),
                      snapshot: snapshot,
                      headline: needYou > 0 ? l.placesNeedYou(needYou) : l.allClear,
                    ),
                  ),
                  if (ranked.isEmpty)
                    Positioned(
                      top: waveStart + 18,
                      left: 40,
                      right: 40,
                      child: PillButton(
                          label: l.addPlace, onTap: () => Navigator.of(context).pushNamed(Routes.placeEdit)),
                    ),
                  for (var i = 0; i < ranked.length; i++)
                    Positioned(
                      top: rowTops[i] + spacing * 0.18,
                      left: 16,
                      right: 16,
                      child: PlaceRow(
                        status: ranked[i],
                        lastAlert: alerts[ranked[i].view.id],
                        onTap: () => Navigator.of(context).pushNamed(Routes.place(ranked[i].view.id)),
                      ),
                    ),
                ]),
              ),
            ),
          ),
          const Positioned(left: 0, right: 0, bottom: 0, child: _ActionBar()),
        ]);
      }),
    );
  }
}

class _Header extends ConsumerWidget {
  const _Header({required this.runId, required this.snapshot, required this.headline});

  final String runId;
  final RiskSnapshot snapshot;
  final String headline;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final t = snapshot.simTime;
    final demo = runId == demoRun;
    final runLine = t == null
        ? (demo ? l.runLineReplayNoTime : l.runLineLiveNoTime)
        : (demo ? l.runLineReplay(stormTime(t, l.localeName)) : l.runLineLive(stormTime(t, l.localeName)));
    final lang = ref.watch(languageProvider);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12),
      child: Column(children: [
        SizedBox(
          height: 44,
          child: Row(children: [
            _SmallRound(
              semantics: l.addAnotherPlace,
              onTap: () => Navigator.of(context).pushNamed(Routes.placeEdit),
              child: nimbusIcon(NimbusIcon.plus, size: 16),
            ),
            const Expanded(child: Center(child: Wordmark())),
            _SmallRound(
              semantics: l.language,
              onTap: () => ref.read(languageProvider.notifier).set(lang == 'ta' ? 'en' : 'ta'),
              child: Text(l.language,
                  style: const TextStyle(fontFamily: 'NotoSansTamil', fontSize: 13, fontWeight: FontWeight.w600)),
            ),
          ]),
        ),
        const SizedBox(height: 8),
        Text(runLine,
            maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 11.5, color: TideColors.muted)),
        const SizedBox(height: 8),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12),
          child: Text(headline,
              textAlign: TextAlign.center,
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w500, height: 1.15)),
        ),
        const SizedBox(height: 6),
        if (snapshot.stale)
          _OfflineTag(text: l.offlineUpdated(t == null ? '—' : clockTime(t)))
        else
          Text(l.yourPlaces, style: const TextStyle(fontSize: 11, color: TideColors.muted)),
      ]),
    );
  }
}

class _OfflineTag extends StatelessWidget {
  const _OfflineTag({required this.text});
  final String text;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
        decoration: BoxDecoration(color: Colors.black.withValues(alpha: 0.22), borderRadius: BorderRadius.circular(20)),
        child: Text(text, style: const TextStyle(fontSize: 11, color: TideColors.muted)),
      );
}

class _SmallRound extends StatelessWidget {
  const _SmallRound({required this.child, required this.onTap, required this.semantics});

  final Widget child;
  final VoidCallback onTap;
  final String semantics;

  @override
  Widget build(BuildContext context) => Semantics(
        button: true,
        label: semantics,
        child: InkResponse(
          onTap: onTap,
          radius: 22,
          child: Container(
            width: 34,
            height: 34,
            alignment: Alignment.center,
            decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.12), shape: BoxShape.circle),
            child: child,
          ),
        ),
      );
}

class _ActionBar extends StatelessWidget {
  const _ActionBar();

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    void go(String route) => Navigator.of(context).pushNamed(route);
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 0, 12, 10),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceAround,
          children: [
            RoundButton(label: l.report, onTap: () => go(Routes.report), child: nimbusIcon(NimbusIcon.camera, size: 19)),
            RoundButton(label: l.route, onTap: () => go(Routes.route), child: nimbusIcon(NimbusIcon.route, size: 19)),
            RoundButton(label: l.map, onTap: () => go(Routes.map), child: nimbusIcon(NimbusIcon.map, size: 19)),
            RoundButton(
              label: l.help,
              color: TideColors.sos,
              onTap: () => go(Routes.sos),
              child: Text(l.sos, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
            ),
          ],
        ),
      ),
    );
  }
}
