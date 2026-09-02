#!/usr/bin/env python3
"""MORPH v1.5 — reproducible QOBLIB 50-instance MORPH vs CP-SAT benchmark.

Default protocol: all discovered MIS .gph instances, budgets 10/50/100/1000 ms,
5 seeds, MORPH + CP-SAT = 2000 solver executions for the standard 50-instance set.
CP-SAT uses one worker and explicitly distinguishes no-incumbent UNKNOWN runs from
objective=0. Heuristic feasibility is checked by the native solver itself.
"""
from __future__ import annotations
import argparse, csv, pathlib, subprocess, sys, time

BUDGETS = [10, 50, 100, 1000]
SEEDS = [1, 2, 3, 4, 5]

def run(cmd):
    return subprocess.run(cmd, check=True, text=True, capture_output=True)

def ensure_ortools():
    try:
        from ortools.sat.python import cp_model
        return cp_model
    except ImportError:
        run([sys.executable, '-m', 'pip', 'install', '-q', 'ortools'])
        from ortools.sat.python import cp_model
        return cp_model

def parse_gph(path):
    n = 0; edges = []
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            p = line.split()
            if not p or p[0].lower() in ('c', '#'): continue
            if p[0].lower() == 'p' and len(p) >= 4: n = int(p[-2])
            elif p[0].lower() == 'e' and len(p) >= 3:
                u, v = int(p[1])-1, int(p[2])-1
                if 0 <= u < n and 0 <= v < n and u != v: edges.append((u,v))
    return n, len(edges)

def cpsat(cp_model, path, budget_ms, seed):
    n = 0; edges = []
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            p = line.split()
            if not p or p[0].lower() in ('c', '#'): continue
            if p[0].lower() == 'p' and len(p) >= 4: n = int(p[-2])
            elif p[0].lower() == 'e' and len(p) >= 3: edges.append((int(p[1])-1, int(p[2])-1))
    model = cp_model.CpModel()
    x = [model.NewBoolVar(f'x{i}') for i in range(n)]
    for u, v in edges: model.Add(x[u] + x[v] <= 1)
    model.Maximize(sum(x))
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = budget_ms / 1000.0
    s.parameters.num_search_workers = 1
    s.parameters.random_seed = int(seed)
    s.parameters.log_search_progress = False
    t0 = time.perf_counter(); status = s.Solve(model); wall = (time.perf_counter()-t0)*1000
    has_inc = status in (cp_model.FEASIBLE, cp_model.OPTIMAL)
    objective = int(round(s.ObjectiveValue())) if has_inc else ''
    return dict(n=n, edges=len(edges), objective=objective, has_incumbent=int(has_inc),
                wall_ms=wall, valid=1 if has_inc else 0, status=s.StatusName(status),
                bound=s.BestObjectiveBound(), branches=s.NumBranches(), conflicts=s.NumConflicts())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--qoblib', default='/content/QOBLIB')
    ap.add_argument('--out', default='results/qoblib_morph_vs_cpsat.csv')
    ap.add_argument('--solver', default='./morph_qoblib_solver')
    ap.add_argument('--limit', type=int, default=0, help='0 = all discovered instances')
    args = ap.parse_args()
    cp_model = ensure_ortools()
    qob = pathlib.Path(args.qoblib)
    if not qob.exists():
        run(['git','clone','--depth','1','https://github.com/ZIB-AOPT/QOBLIB.git',str(qob)])
    candidates = list((qob/'07-independentset'/'instances').glob('*.gph'))
    instances = sorted(candidates, key=lambda p: (parse_gph(p)[0], p.name))
    if args.limit: instances = instances[:args.limit]
    if not instances: raise SystemExit('No QOBLIB MIS .gph instances found.')
    out = pathlib.Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    fields = ['instance','n','edges','budget_ms','seed','solver','objective','has_incumbent','wall_ms','valid','status','bound','branches','conflicts']
    total = len(instances)*len(BUDGETS)*len(SEEDS)*2
    print(f'Instances: {len(instances)} | executions: {total}')
    rows=[]; count=0
    for path in instances:
        n,m = parse_gph(path)
        print(f'INSTANCE {path.stem} (n={n}, edges={m})')
        for budget in BUDGETS:
            for seed in SEEDS:
                count += 1
                p = run([args.solver,str(path),'morph',str(budget),str(seed)])
                a = p.stdout.strip().split(',')
                if len(a) != 5: raise RuntimeError(f'Unexpected MORPH output: {p.stdout}')
                rows.append(dict(instance=path.name,n=int(a[0]),edges=int(a[1]),budget_ms=budget,seed=seed,solver='morph',objective=int(a[2]),has_incumbent=1,wall_ms=float(a[3]),valid=int(a[4]),status='FEASIBLE',bound='',branches='',conflicts=''))
                count += 1
                r = cpsat(cp_model,path,budget,seed)
                r.update(instance=path.name,budget_ms=budget,seed=seed,solver='cp-sat')
                rows.append(r)
                if count % 20 == 0: print(f'  [{count}/{total}]')
    with out.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    morph_invalid=[r for r in rows if r['solver']=='morph' and r['valid']!=1]
    if morph_invalid: raise RuntimeError(f'Invalid MORPH rows: {len(morph_invalid)}')
    no_inc=sum(r['solver']=='cp-sat' and not r['has_incumbent'] for r in rows)
    print(f'DONE: {len(rows)} rows | CP-SAT no-incumbent: {no_inc} | output: {out}')

if __name__ == '__main__': main()
