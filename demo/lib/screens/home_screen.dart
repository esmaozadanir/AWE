import 'package:flutter/material.dart';

import '../models/pattern_result.dart';
import '../services/awe_api_client.dart';
import '../services/demo_scenario.dart';
import '../services/stress_test_scenario.dart';
import '../widgets/pattern_card.dart';

enum _RunState { idle, running, done, error }

enum _ScenarioSource { synthetic, stressTest }

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> with SingleTickerProviderStateMixin {
  late final TabController _tabController;

  String _baseUrl = 'http://10.0.2.2:8000';
  _ScenarioSource _source = _ScenarioSource.synthetic;
  _RunState _state = _RunState.idle;
  String? _errorMessage;
  String? _lastProjectId;
  String? _lastSubjectId;
  List<VariantPattern> _patterns = [];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  List<VariantPattern> get _recommended => _patterns.where((p) => p.recommended).toList();
  List<VariantPattern> get _notRecommended => _patterns.where((p) => !p.recommended).toList();

  Future<void> _runSimulation() async {
    setState(() {
      _state = _RunState.running;
      _errorMessage = null;
    });

    final client = AweApiClient(baseUrl: _baseUrl);

    try {
      await client.checkHealth();

      final String projectId;
      final String subjectId;
      final List<Map<String, dynamic>> events;
      if (_source == _ScenarioSource.stressTest) {
        projectId = StressTestScenario.projectId;
        subjectId = StressTestScenario.subjectId;
        events = await StressTestScenario().loadEvents();
      } else {
        final scenario = DemoScenario();
        projectId = DemoScenario.projectId;
        subjectId = scenario.subjectId;
        events = scenario.buildEvents();
      }

      await client.pushEventsBatch(projectId, events);
      await client.analyzeSubject(projectId, subjectId);
      final patterns = await client.getPatterns(projectId, subjectId);

      if (!mounted) return;
      setState(() {
        _patterns = patterns;
        _lastProjectId = projectId;
        _lastSubjectId = subjectId;
        _state = _RunState.done;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _state = _RunState.error;
        _errorMessage = e.toString();
      });
    }
  }

  Future<void> _openSettings() async {
    final controller = TextEditingController(text: _baseUrl);
    final result = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Backend adresi'),
        content: TextField(
          controller: controller,
          decoration: const InputDecoration(
            labelText: 'Base URL',
            hintText: 'http://10.0.2.2:8000',
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Vazgeç')),
          FilledButton(
            onPressed: () => Navigator.pop(context, controller.text.trim()),
            child: const Text('Kaydet'),
          ),
        ],
      ),
    );
    if (result != null && result.isNotEmpty) {
      setState(() => _baseUrl = result);
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Alışkanlık Motoru Demo'),
        actions: [
          IconButton(
            tooltip: 'Backend ayarları',
            onPressed: _openSettings,
            icon: const Icon(Icons.settings_outlined),
          ),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
            child: _ControlPanel(
              baseUrl: _baseUrl,
              source: _source,
              onSourceChanged: (value) => setState(() => _source = value),
              state: _state,
              errorMessage: _errorMessage,
              lastProjectId: _lastProjectId,
              lastSubjectId: _lastSubjectId,
              onRun: _runSimulation,
            ),
          ),
          if (_state == _RunState.done) ...[
            TabBar(
              controller: _tabController,
              labelColor: scheme.primary,
              tabs: [
                Tab(text: 'Önerilenler (${_recommended.length})'),
                Tab(text: 'Önerilmeyenler (${_notRecommended.length})'),
              ],
            ),
            Expanded(
              child: TabBarView(
                controller: _tabController,
                children: [
                  _PatternList(patterns: _recommended, emptyText: 'Bu çalıştırmada aktif öneri bulunamadı.'),
                  _PatternList(
                    patterns: _notRecommended,
                    emptyText: 'Bu çalıştırmada reddedilen aday bulunamadı.',
                  ),
                ],
              ),
            ),
          ] else
            const Expanded(child: _EmptyState()),
        ],
      ),
    );
  }
}

class _ControlPanel extends StatelessWidget {
  final String baseUrl;
  final _ScenarioSource source;
  final ValueChanged<_ScenarioSource> onSourceChanged;
  final _RunState state;
  final String? errorMessage;
  final String? lastProjectId;
  final String? lastSubjectId;
  final VoidCallback onRun;

  const _ControlPanel({
    required this.baseUrl,
    required this.source,
    required this.onSourceChanged,
    required this.state,
    required this.errorMessage,
    required this.lastProjectId,
    required this.lastSubjectId,
    required this.onRun,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final running = state == _RunState.running;

    return Card(
      elevation: 0,
      color: scheme.surfaceContainerLow,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.dns_outlined, size: 16, color: scheme.onSurfaceVariant),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    baseUrl,
                    style: TextStyle(fontSize: 12.5, color: scheme.onSurfaceVariant, fontFamily: 'monospace'),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            SegmentedButton<_ScenarioSource>(
              segments: const [
                ButtonSegment(
                  value: _ScenarioSource.synthetic,
                  label: Text('Sentetik senaryo'),
                  icon: Icon(Icons.auto_awesome_outlined, size: 16),
                ),
                ButtonSegment(
                  value: _ScenarioSource.stressTest,
                  label: Text('Stres testi (learnloop)'),
                  icon: Icon(Icons.science_outlined, size: 16),
                ),
              ],
              selected: {source},
              onSelectionChanged: running ? null : (values) => onSourceChanged(values.first),
              style: const ButtonStyle(visualDensity: VisualDensity.compact),
            ),
            const SizedBox(height: 10),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: running ? null : onRun,
                icon: running
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                      )
                    : const Icon(Icons.play_arrow_rounded),
                label: Text(running ? 'Simülasyon çalışıyor…' : 'Simülasyonu Çalıştır'),
              ),
            ),
            if (state == _RunState.error) ...[
              const SizedBox(height: 10),
              Text(
                errorMessage ?? 'Bilinmeyen hata',
                style: TextStyle(color: scheme.error, fontSize: 12.5),
              ),
            ],
            if (state == _RunState.done && lastSubjectId != null) ...[
              const SizedBox(height: 8),
              Text(
                'project_id: $lastProjectId  •  subject_id: $lastSubjectId',
                style: TextStyle(fontSize: 11, color: scheme.onSurfaceVariant, fontFamily: 'monospace'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.insights_outlined, size: 48, color: scheme.outline),
            const SizedBox(height: 12),
            Text(
              'Sahte bir kullanıcı geçmişi üretip backend\'e gönderecek, '
              'motora analiz ettirecek ve bulunan alışkanlık dizilerini burada gösterecek.',
              textAlign: TextAlign.center,
              style: TextStyle(color: scheme.onSurfaceVariant),
            ),
          ],
        ),
      ),
    );
  }
}

class _PatternList extends StatelessWidget {
  final List<VariantPattern> patterns;
  final String emptyText;

  const _PatternList({required this.patterns, required this.emptyText});

  @override
  Widget build(BuildContext context) {
    if (patterns.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(emptyText, textAlign: TextAlign.center),
        ),
      );
    }
    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: patterns.length,
      separatorBuilder: (_, __) => const SizedBox(height: 10),
      itemBuilder: (context, index) => PatternCard(pattern: patterns[index]),
    );
  }
}
