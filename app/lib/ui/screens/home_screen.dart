import 'package:flutter/material.dart';

import '../widgets/tide_background.dart';
import '../widgets/wordmark.dart';

/// Home: the user's places on the tide. Filled in by Task 7.
class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) => const Scaffold(
        body: TideBackground(
          layerTops: homeLayerTops,
          child: SafeArea(child: Align(alignment: Alignment.topCenter, child: Padding(padding: EdgeInsets.only(top: 12), child: Wordmark()))),
        ),
      );
}
