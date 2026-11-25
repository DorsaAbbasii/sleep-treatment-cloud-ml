"""Plot saved sequential API benchmarks without modifying their raw data."""
import argparse
import csv
import json
import math
import statistics
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
ENDPOINTS = ('/health', '/predict')


def read_csv(path):
    with path.open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--platform', choices=['openstack', 'aws', 'public', 'local'], required=True)
    parser.add_argument('--input', type=Path, help='Override benchmark results directory')
    args = parser.parse_args()
    folder = args.input or ROOT / 'results' / 'cloud' / args.platform / 'remote_latency'
    cfg = json.loads((folder / 'benchmark_config.json').read_text(encoding='utf-8'))
    if cfg['platform'] != args.platform:
        raise ValueError('Platform in configuration does not match --platform')
    raw = read_csv(folder / 'remote_requests.csv')
    summary = {r['endpoint']: r for r in read_csv(folder / 'remote_endpoint_summary.csv')}
    runs = read_csv(folder / 'remote_run_summary.csv')
    expected = cfg['requests_per_run'] * cfg['runs']
    if set(summary) != set(ENDPOINTS) or len(raw) != expected * 2 or len(runs) != cfg['runs'] * 2:
        raise ValueError('Unexpected endpoints or request/run count')
    values = {}
    for ep in ENDPOINTS:
        group = [r for r in raw if r['endpoint'] == ep]
        keys = {(int(r['run']), int(r['request'])) for r in group}
        expected_keys = {(i, j) for i in range(1, cfg['runs']+1) for j in range(1, cfg['requests_per_run']+1)}
        if len(group) != expected or keys != expected_keys:
            raise ValueError(f'Missing or duplicated measurements: {ep}')
        group.sort(key=lambda r: (int(r['run']), int(r['request'])))
        good = [(i, float(r['latency_ms'])) for i, r in enumerate(group, 1) if r['success'].lower() == 'true']
        a = [v for _, v in good]
        if not a or any(not math.isfinite(v) or v <= 0 for v in a):
            raise ValueError(f'Missing/invalid successful latencies: {ep}')
        s = summary[ep]
        if len(a) != int(s['successful']) or len(group) != int(s['requests']) or len(group)-len(a) != int(s['failed']):
            raise ValueError(f'Inconsistent summary counts: {ep}')
        if abs(statistics.mean(a) - float(s['mean_ms'])) > 0.00001:
            raise ValueError(f'Inconsistent mean: {ep}')
        for p in (50, 95, 99):
            if abs(sorted(a)[math.ceil(len(a)*p/100)-1] - float(s[f'p{p}_ms'])) > 0.00001:
                raise ValueError(f'Inconsistent percentile: {ep} P{p}')
        values[ep] = good
    out = folder / 'figures'
    out.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False})
    colors = ['#2878B5', '#D97732']
    label = args.platform.upper()
    metrics = [('p50_ms', 'P50'), ('mean_ms', 'Mean'), ('p95_ms', 'P95'), ('p99_ms', 'P99')]
    fig, ax = plt.subplots(figsize=(8.4, 4.8), layout='constrained')
    for i, ep in enumerate(ENDPOINTS):
        bars = ax.bar([j + (i-.5)*.36 for j in range(len(metrics))],
                      [float(summary[ep][key]) for key, _ in metrics], .36, label=ep, color=colors[i])
        ax.bar_label(bars, fmt='%.1f', padding=3, fontsize=9)
    ax.set_xticks(range(len(metrics)), [name for _, name in metrics])
    ax.set_ylabel('Response latency (ms)')
    ax.set_title(f'{label}: remote response latency')
    ax.set_ylim(0, max(float(summary[e][k]) for e in ENDPOINTS for k,_ in metrics)*1.22)
    ax.legend(frameon=False); ax.grid(axis='y', alpha=.2); ax.set_axisbelow(True)
    fig.savefig(out/'remote_latency_summary.png', dpi=300); plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5), layout='constrained')
    for i, ep in enumerate(ENDPOINTS):
        good = values[ep]
        ax.plot([k for k,_ in good], [v for _,v in good], color=colors[i], marker='.', markersize=2.5, linewidth=.65, alpha=.8, label=ep)
    for r in range(1, cfg['runs']):
        ax.axvline(r*cfg['requests_per_run']+.5, color='gray', linestyle='--', linewidth=.8)
    ax.set_yscale('log'); ax.set_xlabel('Measured request index (per endpoint)')
    ax.set_ylabel('Response latency (ms, log scale)'); ax.set_title(f'{label}: remote latency by request')
    ax.legend(frameon=False); ax.grid(axis='y', alpha=.2)
    fig.savefig(out/'remote_latency_sequence.png', dpi=300); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.8), layout='constrained')
    for i, ep in enumerate(ENDPOINTS):
        a = sorted(v for _,v in values[ep]); n=len(a)
        ax.step([a[0]]+a, [0]+[100*j/n for j in range(1,n+1)], where='post', color=colors[i], label=f'{ep} (n={n})')
    ax.set_xscale('log'); ax.set_xlabel('Response latency (ms, log scale)'); ax.set_ylabel('Successful responses at or below latency (%)')
    ax.set_title(f'{label}: empirical latency distribution'); ax.set_ylim(0, 102)
    ax.legend(frameon=False); ax.grid(alpha=.2)
    fig.savefig(out/'remote_latency_ecdf.png', dpi=300); plt.close(fig)
    print(f'Validated {len(raw)} measured requests against summary statistics.')
    print(f'Saved 3 figures to {out}')

if __name__ == '__main__':
    main()
