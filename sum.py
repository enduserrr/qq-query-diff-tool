#!/usr/bin/env python3
import os, re, sys, statistics

outdir = sys.argv[1]
ansi = re.compile(r'\x1b\[[0-9;]*m')

passed, failed = 0, []
times_a, times_b = [], []

for name in sorted(os.listdir(outdir)):
    if not name.startswith('sn') or name in ('summary.log',):
        continue
    path = os.path.join(outdir, name)
    if not os.path.isfile(path):
        continue
    txt = ansi.sub('', open(path).read())
    if 'VERDICT: DIFFERENT' in txt:
        failed.append(name)
    elif 'VERDICT: IDENTICAL' in txt:
        passed += 1
    else:
        failed.append('?' + name)
    m = re.search(r'Execution time: ([\d.]+)s in .*?,\s*([\d.]+)s in ', txt)
    if m:
        times_a.append(float(m.group(1)))
        times_b.append(float(m.group(2)))

total = passed + len([f for f in failed if not f.startswith('?')])
pct_p = 100*passed/total if total else 0.0
pct_f = 100*len(failed)/total if total else 0.0

def med(x): return statistics.median(x) if x else 0.0

print(f'pass: {pct_p:.1f}% | fail: {pct_f:.1f}% ({",".join(sorted(failed))})')
print(f'Execution time: a high {max(times_a) if times_a else 0:.3f}, a median {med(times_a):.3f}, a low {min(times_a) if times_a else 0:.3f}, '
      f'b high {max(times_b) if times_b else 0:.3f}, b median {med(times_b):.3f}, b low {min(times_b) if times_b else 0:.3f}')
print(f'Avg. Delta a/b: {med(times_a)-med(times_b):+.3f}')