"""Sequential end-to-end API benchmark; Python standard library only."""
import argparse
import csv
import json
import math
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parent.parent
PAYLOAD = json.dumps({'age': 48, 'sex': 'Female'}).encode()
OPENER = build_opener(ProxyHandler({}))


def request(base, endpoint):
    req = Request(base + endpoint, data=PAYLOAD if endpoint == '/predict' else None,
                  headers={'Content-Type': 'application/json'} if endpoint == '/predict' else {})
    start = time.perf_counter()
    status, error, valid = 0, '', False
    try:
        with OPENER.open(req, timeout=10) as res:
            status = res.status
            body = res.read()
        elapsed = (time.perf_counter() - start) * 1000
        data = json.loads(body)
        valid = (data.get('status') == 'healthy' if endpoint == '/health' else
                 abs(float(data['predicted_treatment_effect']) - 2.552) < 0.0005)
        if not valid:
            error = 'unexpected response body'
    except HTTPError as exc:
        status = exc.code
        exc.close()
        elapsed = (time.perf_counter() - start) * 1000
        error = f'HTTP {status}'
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        error = type(exc).__name__
    return status, elapsed, status == 200 and valid, error


def percentile(values, p):
    return sorted(values)[max(0, math.ceil(len(values) * p / 100) - 1)] if values else ''


def summary(rows, wall):
    good = [r['latency_ms'] for r in rows if r['success']]
    return dict(requests=len(rows), successful=len(good), failed=len(rows)-len(good),
                non_2xx=sum(not 200 <= r['http_status'] < 300 for r in rows if r['http_status']),
                transport_errors=sum(r['http_status']==0 for r in rows),
                duration_s=wall, throughput_rps=len(good)/wall if wall else 0,
                mean_ms=statistics.mean(good) if good else '',
                sd_ms=statistics.stdev(good) if len(good)>1 else (0 if good else ''),
                p50_ms=percentile(good,50), p95_ms=percentile(good,95),
                p99_ms=percentile(good,99), max_ms=max(good) if good else '')


def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows({k: round(v,6) if isinstance(v,float) else v for k,v in r.items()} for r in rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--platform', choices=['openstack','local','aws','public'], required=True)
    parser.add_argument('--url', required=True)
    parser.add_argument('--requests', type=int, default=100)
    parser.add_argument('--runs', type=int, default=3)
    parser.add_argument('--warmup', type=int, default=5)
    parser.add_argument('--pause', type=float, default=2)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if min(args.requests,args.runs)<1 or args.warmup<0 or args.pause<0:
        parser.error('requests/runs must be positive; warmup/pause nonnegative')
    base = args.url.rstrip('/')
    output = args.output or ROOT/'results'/'cloud'/args.platform/'remote_latency'
    output.mkdir(parents=True, exist_ok=True)
    paths = [output / name for name in ('remote_requests.csv','remote_run_summary.csv','remote_endpoint_summary.csv','benchmark_config.json')]
    if any(p.exists() for p in paths):
        parser.error('Output files already exist. Use --output for a new experiment directory.')
    for endpoint in ('/health','/predict'):
        status, _, ok, error = request(base, endpoint)
        if not ok:
            raise SystemExit(f'Preflight failed for {endpoint}: HTTP {status}, {error}. Check tunnel and API.')
    rows, runs, aggregate = [], [], []
    stamp = datetime.now(timezone.utc).isoformat()
    for endpoint in ('/health','/predict'):
        for run in range(1,args.runs+1):
            for _ in range(args.warmup):
                status, _, ok, error = request(base,endpoint)
                if not ok:
                    raise SystemExit(f'Warmup failed: {endpoint} HTTP {status} {error}.')
            start=time.perf_counter()
            batch=[]
            for i in range(1,args.requests+1):
                status, latency, ok, error=request(base,endpoint)
                batch.append(dict(endpoint=endpoint,run=run,request=i,http_status=status,latency_ms=latency,success=ok,error=error))
            wall=time.perf_counter()-start
            rows.extend(batch)
            record=dict(endpoint=endpoint,run=run,**summary(batch,wall))
            runs.append(record)
            print(f"{endpoint} run {run}: {record['successful']}/{args.requests} successful; mean={record['mean_ms']} ms; P95={record['p95_ms']} ms",flush=True)
            time.sleep(args.pause)
        group=[r for r in rows if r['endpoint']==endpoint]
        wall=sum(r['duration_s'] for r in runs if r['endpoint']==endpoint)
        aggregate.append(dict(endpoint=endpoint,runs=args.runs,**summary(group,wall)))
    write_csv(paths[0],rows)
    write_csv(paths[1],runs)
    write_csv(paths[2],aggregate)
    paths[3].write_text(json.dumps(dict(platform=args.platform,started_utc=stamp,requests_per_run=args.requests,runs=args.runs,warmup_per_run=args.warmup,concurrency=1,pause_s=args.pause,timeout_s=10,payload=json.loads(PAYLOAD),percentile_method='nearest rank',latency_definition='request start through complete HTTP body read; fresh HTTP request, successful validated responses only',throughput_definition='validated successful responses divided by measured run wall time; excludes pauses and warmup'),indent=2)+'\n',encoding='utf-8')
    for r in aggregate:
        print(f"{r['endpoint']}: {r['successful']}/{r['requests']} successful, mean={r['mean_ms']:.3f} ms, P95={r['p95_ms']:.3f} ms" if r['successful'] else f"{r['endpoint']}: no successful responses")
    print(f'Saved results to {output}')

if __name__=='__main__':
    main()
