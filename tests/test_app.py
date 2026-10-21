"""App tests – run:  python3 tests/test_app.py ["<BKMPH02 folder>"]   -> ALL PASS
A  bundled skill self-test (engine/ceda-column-design) prints ALL PASS
B  model routing (skill v1.3.6): gravity/unreduced only -> primary + ASSUMPTION; with a reduced model -> reduced primary,
   unreduced enveloped; app pipeline == skill CLI on the synthetic 3-model set
C  BKMPH02 (folder with 01 Seismic model.xlsx, 02 Full Gravity.xlsx, 04 Load Combination.xlsx, Development of Reinforcement
   Table.xlsx + BKMPH02_Column_Input_v136.xlsx): app pipeline == skill CLI, overload applied only to the rows confirmed on
   screen, decisions log, column plan at B2, workbook round trip with the v1.3.6 sheets
"""
import os, sys, json, subprocess, tempfile, shutil, copy
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import app_io as AIO  # noqa: E402
import openpyxl       # noqa: E402

fails = []


def check(name, cond, info=''):
    print(('PASS ' if cond else 'FAIL ') + name + (f'  [{info}]' if info else ''))
    if not cond:
        fails.append(name)


SK = AIO.SKILL
PY = [sys.executable, '-I']
tmp = tempfile.mkdtemp()
sig = lambda R: sorted((r['label'], q['story'], r['mark'], r['nbar'], r['db'], tuple(r['counts']), round(q['dc'], 4), q['status'])
                       for r in R['results'] for q in r['per'])
# ---------------------------------------------------------------- A
r = subprocess.run(PY + [os.path.join(SK, 'scripts', 'selftest.py'), SK], cwd=tmp, capture_output=True, text=True)
check(f'A skill v{AIO.ENGINE_VERSION} self-test ALL PASS', 'ALL PASS' in r.stdout, (r.stdout.strip().splitlines() or [r.stderr[-300:]])[-1])

# ---------------------------------------------------------------- B routing + parity (synthetic 3-model set)
subprocess.run(PY + [os.path.join(SK, 'tests', 'fixtures', 'make_synthetic_etabs.py'), tmp], check=True, capture_output=True)
rd = lambda f: AIO.read_upload(os.path.join(tmp, f))[:2]
S, FR, FU = rd('seis.xlsx'), rd('full_red.xlsx'), rd('full_unred.xlsx')
tpl = AIO.empty_tpl(); tpl['exclude'] = ['U_B_99']; tpl['criteria'] = {'project.job': 'PAR', 'slender.sway': 'non-sway'}
p1 = AIO.prepare({'seismic': S, 'full_unreduced': FU, 'full_reduced': None}, None, tpl)
check('B gravity/unreduced only -> used as the primary full model, ASSUMPTION reported',
      p1['models_used'] == {'seismic': True, 'full_reduced': True, 'full_unreduced': False} and any('ASSUMPTION' in n for n in p1['route']))
p3 = AIO.prepare({'seismic': S, 'full_unreduced': FU, 'full_reduced': FR}, None, tpl)
check('B reduced + unreduced -> reduced primary, unreduced kept for the gravity envelope',
      p3['models_used'] == {'seismic': True, 'full_reduced': True, 'full_unreduced': True} and not any('ASSUMPTION' in n for n in p3['route']))
dB = os.path.join(tmp, 'B'); os.makedirs(dB)
resB, _ = AIO.run_engine(dB, AIO.build_cfg(p3, dB, {}))
wb = os.path.join(tmp, 'tplB.xlsx'); open(wb, 'wb').write(AIO.INPW.make_template(p3['found'], tpl))
dC = os.path.join(tmp, 'Bcli')
r = subprocess.run(PY + [os.path.join(SK, 'scripts', 'prepare_inputs.py'), dC, '--seismic', os.path.join(tmp, 'seis.xlsx'),
                         '--full-reduced', os.path.join(tmp, 'full_red.xlsx'), '--full-unreduced', os.path.join(tmp, 'full_unred.xlsx'),
                         '--workbook', wb], capture_output=True, text=True)
subprocess.run(PY + [os.path.join(SK, 'scripts', 'run.py'), os.path.join(dC, 'config.json'), os.path.join(dC, 'OUT')], capture_output=True, check=True)
resC = json.load(open(os.path.join(dC, 'OUT', 'results.json')))
check('B app pipeline == skill CLI (3 models: labels, stories, marks, bars, D/C, status)', sig(resB) == sig(resC), f'{len(sig(resB))} rows')
check('B basement assembled through the app path', bool(resB['input_report'].get('basement_stories')))

# ---------------------------------------------------------------- C BKMPH02
D = sys.argv[1] if len(sys.argv) > 1 else None
if D and os.path.exists(os.path.join(D, '02 Full Gravity.xlsx')):
    S = AIO.read_upload(os.path.join(D, '01 Seismic model.xlsx'))[:2]
    G = AIO.read_upload(os.path.join(D, '02 Full Gravity.xlsx'))[:2]
    C = AIO.read_upload(os.path.join(D, '04 Load Combination.xlsx'))[:2]
    tplK = AIO.INPW.read_template(os.path.join(D, 'BKMPH02_Column_Input_v136.xlsx'))
    lap, note = AIO.INPW.read_lap_table(os.path.join(D, 'Development of Reinforcement Table.xlsx'), '40mm')
    if not tplK['lap_rows']:
        tplK['lap_rows'] = lap
    pK = AIO.prepare({'seismic': S, 'full_unreduced': G, 'full_reduced': None}, C, tplK)
    check('C BKMPH02 input check all ✔ (overload handled on screen)', all(c['ok'] for c in AIO.input_check(pK)),
          str([c for c in AIO.input_check(pK) if not c['ok']]))
    ok = {(a, b): c for a, b, c in tplK['overload']}
    dK = os.path.join(tmp, 'K'); os.makedirs(dK)
    cfgK = AIO.build_cfg(pK, dK, ok)
    resK, outK = AIO.run_engine(dK, cfgK)
    ref = os.path.join(D, 'expected_results.json')
    if os.path.exists(ref):
        resR = json.load(open(ref))
        check('C app == skill CLI / final BKMPH02 run (1,277 label-stories: marks, bars, D/C, status)', sig(resK) == sig(resR),
              f'{len(sig(resK))} vs {len(sig(resR))}')
    st = {}
    for x in resK['results']:
        for q in x['per']:
            st[q['status']] = st.get(q['status'], 0) + 1
    check('C confirmed overload rows -> ACCEPTED, the rest OK (BKMPH02 final: 1,272 OK + 5 ACCEPTED)', st == {'OK': 1272, 'ACCEPTED': 5}, str(st))
    one = dict(list(ok.items())[:1])
    dK2 = os.path.join(tmp, 'K2'); os.makedirs(dK2)
    cfg2 = AIO.build_cfg(pK, dK2, one)
    res2, _ = AIO.run_engine(dK2, cfg2)
    st2 = {}
    for x in res2['results']:
        for q in x['per']:
            st2[q['status']] = st2.get(q['status'], 0) + 1
    check('C only the confirmed row is applied: 1 ACCEPTED, 4 REVISE, 4 listed as pending',
          st2.get('ACCEPTED') == 1 and st2.get('REVISE') == 4 and len(cfg2['accept_overload_pending']) == 4, str(st2))
    rv = AIO.review_rows(res2)
    rmax = {(d['label'], d['story']): d['DC'] for d in rv if d['status'] == 'REVISE'}
    check('C REVISE rows carry the D/C reached with the most steel (> 1, ≤ accepted 1.10)',
          len(rmax) == 4 and all(1.0 < v <= 1.10 for v in rmax.values()), str(rmax))
    log = AIO.decisions_log(tplK, cfg2, res2, pK, {list(one)[0]: dict(at='21 Oct 2026 10:00', by='test')})
    p = os.path.join(tmp, 'log.xlsx'); open(p, 'wb').write(log)
    items = [str(c.value) for c in openpyxl.load_workbook(p)['Decisions']['B'][2:]]
    check('C decisions log: model assumption, Lu overrides, sections, ρ, δ, overload confirmed + pending, story ranges',
          all(any(i.startswith(x) for i in items) for x in ('Models', 'Lu / k override', 'Section (designer)', 'ρ 6–8 % approved',
                                                             'δ accepted', 'Overload accepted', 'Overload in workbook', 'Story ranges fixed')))
    pdf, dxf, rows = AIO.plan_map(dK, outK, 'B2')
    check('C column plan B2 (plan_map): PDF + DXF, every B2 column with mark', os.path.getsize(pdf) > 10000 and os.path.exists(dxf)
          and rows and all(x['mark'] for x in rows), f'{len(rows)} columns, {sum(1 for x in rows if x["x"] is None)} without point')
    # workbook round trip with the v1.3.6 sheets
    t2 = os.path.join(tmp, 'rt.xlsx'); open(t2, 'wb').write(AIO.INPW.make_template(pK['found'], tplK))
    back = AIO.INPW.read_template(t2)
    a_, b_ = AIO.INPW.to_cfg(back), AIO.INPW.to_cfg(tplK)
    check('C input workbook round trip (screen -> Excel -> screen gives the same config, incl. Story_ranges / Accept_*)', a_ == b_,
          str([k for k in a_ if a_[k] != b_.get(k)]))
else:
    print('SKIP C (pass the BKMPH02 folder)')
shutil.rmtree(tmp, ignore_errors=True)
print('ALL PASS' if not fails else f'{len(fails)} FAILED: {fails}')
sys.exit(1 if fails else 0)
