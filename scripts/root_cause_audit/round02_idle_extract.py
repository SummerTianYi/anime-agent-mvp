"""Reduce verified snapshot to real idle template/receipt evidence only."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3

p = argparse.ArgumentParser()
p.add_argument('--snapshot-dir', type=Path, required=True)
p.add_argument('--baseline-dir', type=Path, required=True)
p.add_argument('--samples', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
identity = json.loads((a.snapshot_dir / 'identity.json').read_text(encoding='utf-8'))
baseline = json.loads((a.baseline_dir / 'identity.json').read_text(encoding='utf-8'))
assert baseline['status'] == 'captured'
assert all(baseline['normal_identity'][k] == identity['normal_identity'][k] for k in ('volume_serial', 'file_index'))
baseline_event_id = baseline['snapshot_watermarks']['events'][0]
snapshot = a.snapshot_dir / 'transaction-snapshot.sqlite3'
assert identity['status'] == 'captured'
assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == identity['snapshot_sha256']
samples = json.loads(a.samples.read_text(encoding='utf-8'))['samples']
last_tick = samples[-1]['last_input_tick']
episode = [r for r in samples if r['last_input_tick'] == last_tick]
start, end = episode[0]['utc'], identity['utc']
with sqlite3.connect(snapshot.as_uri() + '?mode=ro', uri=True) as db:
    db.row_factory = sqlite3.Row
    malformed = [dict(r) for r in db.execute('SELECT id,event_type FROM events WHERE id>? AND julianday(created_at) IS NULL', (baseline_event_id,))]
    candidates = [dict(r) for r in db.execute('SELECT * FROM events WHERE julianday(created_at)>=julianday(?) AND julianday(created_at)<=julianday(?) ORDER BY id', (start, end))]
    for row in candidates:
        row['payload'] = json.loads(row['payload'])
    events = [r for r in candidates if (r['event_type'].startswith('proactive.') or
              r['payload'].get('request_id', r['payload'].get('requestId')) == 'proactive-idle')]
    utterances = {r['payload'].get('utteranceId') for r in events} - {None}
    included = {r['id'] for r in events}
    events.extend(r for r in candidates if r['id'] not in included and r['payload'].get('utteranceId') in utterances)
    transports = [r for r in candidates if r['event_type'] == 'provider.transport']
result = {'layer': 'real Windows idle samples + verified SQLite read-transaction snapshot',
          'source_identity': {k: identity['normal_identity'][k] for k in ('volume_serial', 'file_index')},
          'snapshot_sha256': identity['snapshot_sha256'],
          'time_selection': {'rule': 'julianday, excludes unparseable timestamps',
                             'baseline_snapshot_sha256': baseline['snapshot_sha256'], 'baseline_event_id': baseline_event_id,
                             'malformed_timestamp_events_after_baseline': malformed,
                             'all_malformed_timestamp_count': identity['malformed_event_timestamps']},
          'observed_episode': {'first_sample': start, 'snapshot_utc': end, 'last_input_tick': last_tick,
                               'max_idle_seconds': max(r['idle_seconds'] for r in episode)},
          'proactive_idle_events': sum(r['event_type'] == 'proactive.idle' for r in events),
          'provider_transport_events_in_episode': len(transports),
          'human_audio': 'not yet confirmed for this reminder', 'events': sorted(events, key=lambda r: r['id'])}
with a.output.open('x', encoding='utf-8') as target:
    json.dump(result, target, ensure_ascii=False, indent=2)
print(json.dumps(result, ensure_ascii=False))
