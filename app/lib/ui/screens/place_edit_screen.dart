import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:uuid/uuid.dart';

import '../../contracts/nimbus.dart';
import '../../data/api_exception.dart';
import '../../domain/place_view.dart';
import '../../l10n/app_localizations.dart';
import '../../state/providers.dart';
import '../icons.dart';
import '../theme/tide_colors.dart';
import '../widgets/pill_button.dart';
import '../widgets/place_row.dart';
import '../widgets/round_button.dart';
import '../widgets/tide_background.dart';
import '../widgets/tide_map.dart';

/// The kinds a citizen can pick. `OTHER` isn't offered.
const placeKinds = [SavedPlaceKind.HOME, SavedPlaceKind.OFFICE, SavedPlaceKind.SCHOOL, SavedPlaceKind.VEHICLE_PARKING];

const _minRadius = 50.0;
const _maxRadius = 1000.0;
const _defaultRadius = 150.0;

/// Add a Saved Place, or edit one when [placeId] is given: a kind, a label,
/// a pin under the map's centre, and a radius.
class PlaceEditScreen extends ConsumerWidget {
  const PlaceEditScreen({super.key, this.placeId});

  final String? placeId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final id = placeId;
    // Wait for what decides where the pin starts, so the map opens there.
    if (id != null) {
      final places = ref.watch(placesProvider);
      if (!places.hasValue) return const _Waiting();
      final view = places.value!.where((p) => p.id == id).firstOrNull;
      if (view == null) return _Message(AppLocalizations.of(context).placeGone);
      return _PlaceForm(existing: view, start: view.place.location);
    }
    if (ref.watch(runIdProvider) == demoRun) return _PlaceForm(start: velachery);
    final gps = ref.watch(currentPositionProvider);
    if (gps.isLoading) return _Waiting(label: AppLocalizations.of(context).findingYou);
    return _PlaceForm(start: gps.value ?? velachery);
  }
}

class _PlaceForm extends ConsumerStatefulWidget {
  const _PlaceForm({this.existing, required this.start});

  final PlaceView? existing;
  final GeoPoint start;

  @override
  ConsumerState<_PlaceForm> createState() => _PlaceFormState();
}

class _PlaceFormState extends ConsumerState<_PlaceForm> {
  late final _label = TextEditingController(text: widget.existing?.place.label ?? '');
  late var _kind = widget.existing?.place.kind ?? SavedPlaceKind.HOME;
  late var _radius = (widget.existing?.place.radiusM ?? _defaultRadius).clamp(_minRadius, _maxRadius);
  late var _pin = widget.start;
  var _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    if (!placeKinds.contains(_kind)) _kind = SavedPlaceKind.HOME;
    _label.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _label.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final l = AppLocalizations.of(context);
    final runId = ref.read(runIdProvider);
    final existing = widget.existing;
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await ref.read(placesProvider.notifier).save(
            placeId: existing?.id ?? 'pl-${const Uuid().v4()}',
            label: _label.text.trim(),
            kind: _kind,
            location: _pin,
            radiusM: _radius,
            runIds: existing == null ? [runId] : {...existing.runIds, runId}.toList(),
          );
      if (mounted) Navigator.of(context).maybePop();
    } on ApiException catch (e) {
      if (mounted) {
        setState(() {
          _saving = false;
          _error = e.code == ApiException.tooManyPlaces ? l.tooManyPlaces : l.saveFailed;
        });
      }
    }
  }

  Future<void> _delete() async {
    final l = AppLocalizations.of(context);
    final sure = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: TideColors.deep,
        title: Text(l.removePlaceTitle),
        content: Text(l.removePlaceBody, style: const TextStyle(color: TideColors.muted)),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(false), child: Text(l.cancel)),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: Text(l.remove, style: const TextStyle(color: TideColors.likely)),
          ),
        ],
      ),
    );
    if (sure != true || !mounted) return;
    setState(() => _saving = true);
    try {
      await ref.read(placesProvider.notifier).remove(widget.existing!.id);
      // Place detail for this place is now empty, so go back past it.
      if (mounted) Navigator.of(context).popUntil((r) => r.isFirst);
    } on ApiException {
      if (mounted) {
        setState(() {
          _saving = false;
          _error = l.saveFailed;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final segments = ref.watch(segmentsProvider).value ?? const <Segment>[];
    final canSave = !_saving && _label.text.trim().isNotEmpty;

    return Scaffold(
      body: LayoutBuilder(builder: (context, box) {
        final mapHeight = box.maxHeight * 0.42;
        // The body's constraints are loose: without expand the Stack would
        // end under the map and clip the panel to 40 px.
        return Stack(fit: StackFit.expand, children: [
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            height: mapHeight + 40,
            child: Stack(children: [
              TideMap(
                segments: segments,
                risk: const {},
                focus: widget.start,
                zoom: 16,
                onCentre: (at) => _pin = at,
              ),
              // The pin stays at the centre; the map moves under it.
              Positioned.fill(
                bottom: 40,
                child: IgnorePointer(
                  child: Center(
                    child: Transform.translate(
                      offset: const Offset(0, -14),
                      child: nimbusIcon(NimbusIcon.drop, size: 30, color: TideColors.accent),
                    ),
                  ),
                ),
              ),
            ]),
          ),
          Positioned(
            top: 0,
            left: 0,
            child: SafeArea(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: RoundButton(
                  size: 40,
                  color: TideColors.deep,
                  onTap: () => Navigator.of(context).maybePop(),
                  child: nimbusIcon(NimbusIcon.back, size: 20),
                ),
              ),
            ),
          ),
          Positioned.fill(
            top: mapHeight,
            child: TideBackground(
              layerTops: const [0.0, 0.05, 0.10],
              colors: const [Color(0xFF22557F), Color(0xFF18456E), Color(0xFF10365E)],
              rain: false,
              child: SafeArea(
                top: false,
                child: SingleChildScrollView(
                  padding: const EdgeInsets.fromLTRB(22, 40, 22, 20),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                    Text(widget.existing == null ? l.addPlaceTitle : l.editPlaceTitle,
                        style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w600)),
                    const SizedBox(height: 2),
                    Text(l.pinHint, style: const TextStyle(fontSize: 13, color: TideColors.muted)),
                    const SizedBox(height: 14),
                    Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      for (final k in placeKinds)
                        Expanded(
                          child: _KindChoice(
                            kind: k,
                            label: _kindLabel(k, l),
                            selected: k == _kind,
                            onTap: () => setState(() => _kind = k),
                          ),
                        ),
                    ]),
                    const SizedBox(height: 14),
                    TextField(
                      controller: _label,
                      maxLength: 60,
                      textCapitalization: TextCapitalization.sentences,
                      decoration: InputDecoration(
                        hintText: l.placeLabelHint,
                        counterText: '',
                        filled: true,
                        fillColor: TideColors.deep.withValues(alpha: 0.45),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
                      ),
                    ),
                    const SizedBox(height: 14),
                    Text(l.radiusLabel(_radius.round()), style: const TextStyle(fontSize: 14, color: TideColors.muted)),
                    Slider(
                      value: _radius,
                      min: _minRadius,
                      max: _maxRadius,
                      divisions: ((_maxRadius - _minRadius) / 50).round(),
                      activeColor: TideColors.accent,
                      inactiveColor: TideColors.deep,
                      onChanged: (v) => setState(() => _radius = v),
                    ),
                    if (_error != null)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: Text(_error!, textAlign: TextAlign.center, style: const TextStyle(color: TideColors.watch)),
                      ),
                    PillButton(label: l.save, onTap: canSave ? _save : null),
                    if (widget.existing != null) PillButton(label: l.delete, quiet: true, onTap: _saving ? null : _delete),
                  ]),
                ),
              ),
            ),
          ),
        ]);
      }),
    );
  }
}

String _kindLabel(SavedPlaceKind kind, AppLocalizations l) => switch (kind) {
  SavedPlaceKind.HOME => l.kindHome,
  SavedPlaceKind.OFFICE => l.kindOffice,
  SavedPlaceKind.SCHOOL => l.kindSchool,
  SavedPlaceKind.VEHICLE_PARKING => l.kindParking,
  SavedPlaceKind.OTHER => '',
};

class _KindChoice extends StatelessWidget {
  const _KindChoice({required this.kind, required this.label, required this.selected, required this.onTap});

  final SavedPlaceKind kind;
  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Semantics(
    selected: selected,
    child: GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Column(
        children: [
          AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            width: 46,
            height: 46,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: selected ? TideColors.button : TideColors.deep.withValues(alpha: 0.45),
              border: Border.all(color: selected ? TideColors.accent : Colors.transparent, width: 1.5),
            ),
            child: nimbusIcon(kindIcon(kind), size: 20),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            textAlign: TextAlign.center,
            maxLines: 2,
            style: TextStyle(fontSize: 11.5, color: selected ? TideColors.text : TideColors.muted),
          ),
        ],
      ),
    ),
  );
}

class _Waiting extends StatelessWidget {
  const _Waiting({this.label});

  final String? label;

  @override
  Widget build(BuildContext context) => Scaffold(
    body: TideBackground(
      layerTops: const [0.6, 0.7, 0.8, 0.9],
      child: SafeArea(
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const CircularProgressIndicator(color: TideColors.accent),
              if (label != null) ...[
                const SizedBox(height: 14),
                Text(label!, style: const TextStyle(color: TideColors.muted)),
              ],
            ],
          ),
        ),
      ),
    ),
  );
}

class _Message extends StatelessWidget {
  const _Message(this.text);

  final String text;

  @override
  Widget build(BuildContext context) => Scaffold(
    body: TideBackground(
      layerTops: const [0.6, 0.7, 0.8, 0.9],
      child: SafeArea(
        child: Center(
          child: Text(text, style: const TextStyle(color: TideColors.muted)),
        ),
      ),
    ),
  );
}
