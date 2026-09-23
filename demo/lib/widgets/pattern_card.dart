import 'package:flutter/material.dart';

import '../models/pattern_result.dart';
import 'pattern_trail.dart';

/// Tek bir varyantı (öneri ya da reddedilen aday) gösteren kart. Aynı bileşen hem
/// "Önerilenler" hem "Önerilmeyenler" sekmesinde kullanılır; yalnızca vurgu rengi ve
/// alt bilgi satırı [pattern.recommended] durumuna göre değişir -- ikisinde de gösterilen
/// alışkanlık dizisi (pattern) aynı bileşenden (PatternTrail) gelir.
class PatternCard extends StatelessWidget {
  final VariantPattern pattern;

  const PatternCard({super.key, required this.pattern});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final recommended = pattern.recommended;

    final accent = recommended ? const Color(0xFF1B8A5A) : const Color(0xFFB5750B);
    final accentSurface = recommended ? const Color(0xFFE4F5EC) : const Color(0xFFFBEFDD);

    final title = recommended
        ? (pattern.destinationScreen ?? pattern.target ?? 'Kısayol önerisi')
        : _titleForRejected(pattern);

    return Card(
      elevation: 0,
      color: scheme.surface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: scheme.outlineVariant),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(7),
                  decoration: BoxDecoration(color: accentSurface, shape: BoxShape.circle),
                  child: Icon(
                    recommended ? Icons.bolt_rounded : Icons.hourglass_bottom_rounded,
                    size: 18,
                    color: accent,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    title,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
                  ),
                ),
                if (recommended && pattern.mode != null) _ModeBadge(mode: pattern.mode!),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              'Motorun bulduğu alışkanlık dizisi',
              style: Theme.of(context).textTheme.labelSmall?.copyWith(color: scheme.onSurfaceVariant),
            ),
            const SizedBox(height: 6),
            PatternTrail(steps: pattern.pattern, chipColor: accentSurface, onChipColor: accent),
            const SizedBox(height: 12),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                if (pattern.repeatCount != null)
                  _InfoPill(icon: Icons.repeat_rounded, label: '${pattern.repeatCount} oturumda tekrarlandı'),
                if (pattern.distinctDays != null)
                  _InfoPill(icon: Icons.calendar_today_rounded, label: '${pattern.distinctDays} farklı gün'),
                if (recommended && pattern.savedSteps != null)
                  _InfoPill(
                    icon: Icons.timer_outlined,
                    label: '${pattern.savedSteps} adım kısaltıyor',
                    color: accent,
                    background: accentSurface,
                  ),
              ],
            ),
            if (!recommended && pattern.reasonCodes.isNotEmpty) ...[
              const SizedBox(height: 10),
              Text(
                'Neden önerilmedi',
                style: Theme.of(context).textTheme.labelSmall?.copyWith(color: scheme.onSurfaceVariant),
              ),
              const SizedBox(height: 6),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: pattern.reasonCodes
                    .map((code) => _InfoPill(icon: Icons.info_outline_rounded, label: explainReasonCode(code)))
                    .toList(),
              ),
            ],
          ],
        ),
      ),
    );
  }

  String _titleForRejected(VariantPattern pattern) {
    if (pattern.decision == 'habit_detected') {
      return 'Alışkanlık tespit edildi, ama öneriye dönüşmedi';
    }
    return 'Henüz yeterli kanıt yok';
  }
}

class _ModeBadge extends StatelessWidget {
  final String mode;
  const _ModeBadge({required this.mode});

  @override
  Widget build(BuildContext context) {
    final label = mode == 'navigate' ? 'YÖNLENDİRME' : 'ÖN DOLDURMA';
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.primaryContainer,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 10,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.3,
          color: Theme.of(context).colorScheme.onPrimaryContainer,
        ),
      ),
    );
  }
}

class _InfoPill extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color? color;
  final Color? background;

  const _InfoPill({required this.icon, required this.label, this.color, this.background});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      decoration: BoxDecoration(
        color: background ?? scheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 13, color: color ?? scheme.onSurfaceVariant),
          const SizedBox(width: 4),
          Text(
            label,
            style: TextStyle(fontSize: 11.5, color: color ?? scheme.onSurfaceVariant, fontWeight: FontWeight.w600),
          ),
        ],
      ),
    );
  }
}
