"""Analyze saved ApacheBench and Docker stats logs. Run from repository root.

Usage: python src/analyze_cloud_benchmarks.py [--platform openstack]
Dependencies: matplotlib; other modules are Python standard library.
"""
import argparse
import csv
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean, stdev


def read_ab(path):
    s = path.read_text(encoding='utf-8-sig')
    def field(label, optional=False):
        m = re.search(r'^' + re.escape(label) + r':\s*(\d+(?:\.\d+)?)', s, re.M)
        if not m:
            if optional:
                return 0
            raise ValueError(f'{path.name}: missing {label}')
        return float(m.group(1))
    def percentile(p):
        m = re.search(r'^\s*' + str(p) + r'%\s+(\d+(?:\.\d+)?)', s, re.M)
        if not m:
            raise ValueError(f'{path.name}: missing P{p}')
        return float(m.group(1))
    endpoint = re.search(r'^Document Path:\s*(\S+)', s, re.M)
    if not endpoint:
        raise ValueError(f'{path.name}: missing Document Path')
    return dict(endpoint=endpoint.group(1), concurrency=int(field('Concurrency Level')),
                completed=int(field('Complete requests')), failed=int(field('Failed requests')),
                non_2xx=int(field('Non-2xx responses', True)), duration_s=field('Time taken for tests'),
                throughput_rps=field('Requests per second'), mean_latency_ms=field('Time per request'),
                p50_ms=percentile(50), p95_ms=percentile(95), p99_ms=percentile(99), max_ms=percentile(100))


def read_stats(path, label):
    s = path.read_text(encoding='utf-8-sig')
    rows = []
    stamp = None
    start = None
    factor = {'B': 1/1048576, 'KiB': 1/1024, 'MiB': 1, 'GiB': 1024, 'TiB': 1048576}
    for line in s.splitlines():
        if re.fullmatch(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC', line):
            if stamp is not None:
                raise ValueError(f'{path.name}: missing stats after {stamp}')
            stamp = datetime.strptime(line, '%Y-%m-%d %H:%M:%S UTC')
            continue
        m = re.fullmatch(r'CPU=([\d.]+)% RAM=([\d.]+)(B|KiB|MiB|GiB|TiB) / [\d.]+(?:B|KiB|MiB|GiB|TiB) MEM=([\d.]+)%', line.strip())
        if m and stamp is not None:
            if start is None:
                start = stamp
            rows.append(dict(experiment=label, timestamp_utc=stamp.isoformat()+'Z',
                             elapsed_s=(stamp-start).total_seconds(), cpu_pct=float(m[1]),
                             ram_mib=float(m[2])*factor[m[3]], memory_pct=float(m[4])))
            stamp = None
        elif line.strip():
            raise ValueError(f'{path.name}: unexpected line: {line}')
    if stamp is not None or not rows:
        raise ValueError(f'{path.name}: incomplete monitoring data')
    return rows


def write_csv(path, rows):
    if not rows:
        raise ValueError(f'No rows for {path}')
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows):
    groups = defaultdict(list)
    for r in rows:
        groups[(r['endpoint'], r['workers'], r['concurrency'])].append(r)
    out = []
    for (endpoint, workers, concurrency), group in sorted(groups.items()):
        row = dict(endpoint=endpoint, workers=workers, concurrency=concurrency,
                   runs=len(group), completed=sum(r['completed'] for r in group),
                   failed=sum(r['failed'] for r in group), non_2xx=sum(r['non_2xx'] for r in group))
        for key in ('throughput_rps','mean_latency_ms','p50_ms','p95_ms','p99_ms','max_ms','duration_s'):
            vals = [r[key] for r in group]
            row[key+'_mean'] = round(mean(vals), 6)
            row[key+'_sd'] = round(stdev(vals), 6) if len(vals)>1 else ''
        out.append(row)
    return out


def plot_grouped(plt, rows, categories, series, key, ylabel, title, output):
    fig, ax = plt.subplots(figsize=(7.2, 4.5), layout='constrained')
    width = 0.34
    for i, (label, selector) in enumerate(series):
        picked = [next(r for r in rows if selector(r) and r['concurrency']==c) for c in categories]
        positions = [j + (i-(len(series)-1)/2)*width for j in range(len(categories))]
        ax.bar(positions, [r[key+'_mean'] for r in picked], width,
               yerr=[r[key+'_sd'] for r in picked], capsize=4, label=label)
    ax.set_xticks(range(len(categories)), [str(c) for c in categories])
    ax.set(xlabel='Concurrent requests', ylabel=ylabel, title=title)
    ax.set_ylim(bottom=0)
    ax.grid(axis='y', alpha=.25)
    ax.set_axisbelow(True)
    ax.legend()
    fig.savefig(output, dpi=300)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--platform', default='openstack')
    parser.add_argument('--input', type=Path, help='Override raw benchmark directory')
    parser.add_argument('--output', type=Path, help='Override analysis output directory')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] if Path(__file__).parent.name == 'src' else Path.cwd()
    base = root/'results'/'cloud'/args.platform
    raw = args.input or base/'sleep-cloud-benchmarks'
    dest = args.output or base/'analysis'
    # Validate the full known experimental matrix before writing output.
    endpoint_runs, worker_runs, resource_runs, samples = [], [], [], []
    for endpoint in ('health','predict'):
        for c in (1,10):
            for run in (1,2,3):
                p = raw/f'{endpoint}_c{c}_run{run}.txt'
                r = read_ab(p)
                if (r['endpoint'],r['concurrency'],r['completed']) != ('/'+endpoint,c,1000):
                    raise ValueError(f'Unexpected experimental configuration: {p}')
                endpoint_runs.append(dict(experiment='endpoint',workers=1,run=run,source=p.relative_to(raw).as_posix(),**r))
    for w in (1,2):
        for c in (1,10):
            for run in (1,2,3):
                p = raw/'worker-comparison'/f'w{w}_c{c}_run{run}.txt'
                r = read_ab(p)
                if (r['endpoint'],r['concurrency'],r['completed']) != ('/predict',c,1000):
                    raise ValueError(f'Unexpected experimental configuration: {p}')
                worker_runs.append(dict(experiment='worker',workers=w,run=run,source=p.relative_to(raw).as_posix(),**r))
    for label,w,n,folder,bench,monitor in [
        ('initial_w1',1,1000,raw,'predict_resource_test.txt','resource_monitoring.txt'),
        ('matched_w1',1,3000,raw/'worker-comparison','w1_resource_test.txt','w1_resource_monitoring.txt'),
        ('matched_w2',2,3000,raw/'worker-comparison','w2_resource_test.txt','w2_resource_monitoring.txt')]:
        p = folder/bench
        r = read_ab(p)
        if (r['endpoint'],r['concurrency'],r['completed']) != ('/predict',10,n):
            raise ValueError(f'Unexpected resource workload: {p}')
        resource_runs.append(dict(experiment=label,workers=w,run=1,source=p.relative_to(raw).as_posix(),**r))
        samples.extend(read_stats(folder/monitor,label))
    ep_summary = summarize(endpoint_runs)
    w_summary = summarize(worker_runs)
    peaks=[]
    for r in resource_runs:
        group=[s for s in samples if s['experiment']==r['experiment']]
        peaks.append(dict(**r,samples=len(group),peak_cpu_pct=max(s['cpu_pct'] for s in group),
                          peak_ram_mib=max(s['ram_mib'] for s in group),peak_memory_pct=max(s['memory_pct'] for s in group)))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    dest.mkdir(parents=True,exist_ok=True)
    write_csv(dest/'benchmark_runs.csv', endpoint_runs+worker_runs+resource_runs)
    write_csv(dest/'endpoint_summary.csv',ep_summary)
    write_csv(dest/'worker_summary.csv',w_summary)
    write_csv(dest/'resource_samples.csv',samples)
    write_csv(dest/'resource_summary.csv',peaks)
    for label,rows,series in [
        ('endpoint',ep_summary,[('Health',lambda r:r['endpoint']=='/health'),('Prediction',lambda r:r['endpoint']=='/predict')]),
        ('worker',w_summary,[('1 worker',lambda r:r['workers']==1),('2 workers',lambda r:r['workers']==2)])]:
        for key,ylab,title in [('throughput_rps','Requests/s','Throughput'),('mean_latency_ms','Milliseconds','Mean response latency'),('p95_ms','Milliseconds','Mean run-level P95 latency')]:
            plot_grouped(plt,rows,[1,10],series,key,ylab,f'{args.platform.capitalize()} — {title}',dest/f'{label}_{key}.png')
    for key,ylab,title in [('cpu_pct','Docker CPU (%)','CPU utilization'),('ram_mib','Memory (MiB)','Memory utilization')]:
        fig,ax=plt.subplots(figsize=(7.2,4.5),layout='constrained')
        for label,legend in [('matched_w1','1 worker'),('matched_w2','2 workers')]:
            group=[r for r in samples if r['experiment']==label]
            ax.plot([r['elapsed_s'] for r in group],[r[key] for r in group],marker='o',markersize=3,label=legend)
        ax.set(xlabel='Seconds since first monitoring sample',ylabel=ylab,title=f'{args.platform.capitalize()} — {title}')
        ax.set_ylim(bottom=0)
        ax.grid(alpha=.25)
        ax.legend()
        fig.savefig(dest/f'resource_{key}.png',dpi=300)
        plt.close(fig)
    print(f'Validated {len(endpoint_runs)+len(worker_runs)} repeated runs, {len(resource_runs)} resource runs, {len(samples)} samples.')
    all_runs=endpoint_runs+worker_runs+resource_runs
    print(f'Completed requests: {sum(r["completed"] for r in all_runs)}; reported failures: {sum(r["failed"] for r in all_runs)}; non-2xx: {sum(r["non_2xx"] for r in all_runs)}')
    for r in w_summary:
        print(f'Workers={r["workers"]}, concurrency={r["concurrency"]}: {r["throughput_rps_mean"]:.2f} req/s, {r["mean_latency_ms_mean"]:.3f} ms, P95={r["p95_ms_mean"]:.2f} ms')
    print(f'Saved 5 CSV files and 8 PNG figures to {dest}')

if __name__ == '__main__':
    main()
