import 'package:flutter/material.dart';

import '../models/pattern_result.dart';

/// Motorun bulduğu davranış dizisini ("alışkanlık dizisi") ok işaretleriyle birbirine
/// bağlı adım rozetleri olarak gösterir. Bu, kullanıcının "neden bu öneri çıktı" ya da
/// "neden çıkmadı" sorusuna verilen görsel cevaptır.
class PatternTrail extends StatelessWidget {
  final List<PatternStep> steps;
  final Color chipColor;
  final Color onChipColor;

  const PatternTrail({
    super.key,
    required this.steps,
    required this.chipColor,
    required this.onChipColor,
  });

  @override
  Widget build(BuildContext context) {
    final children = <Widget>[];
    for (var i = 0; i < steps.length; i++) {
      if (i > 0) {
        children.add(
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4),
            child: Icon(Icons.arrow_forward_rounded, size: 16, color: Theme.of(context).colorScheme.outline),
          ),
        );
      }
      children.add(_StepChip(step: steps[i], color: chipColor, onColor: onChipColor));
    }
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: children),
    );
  }
}

class _StepChip extends StatelessWidget {
  final PatternStep step;
  final Color color;
  final Color onColor;

  const _StepChip({required this.step, required this.color, required this.onColor});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            step.action,
            style: TextStyle(color: onColor, fontWeight: FontWeight.w600, fontSize: 12.5),
          ),
          if (step.screen != null)
            Text(
              step.screen!,
              style: TextStyle(color: onColor.withValues(alpha: 0.72), fontSize: 10.5),
            ),
        ],
      ),
    );
  }
}
