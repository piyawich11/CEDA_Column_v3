"""CEDA RC Column Design – Streamlit front end (v3) for the ceda-column-design skill (engine/ceda-column-design = skill folder).

Same inputs as the BKMPH02 project:
  1.1 seismic model · 1.2 full model gravity (unreduced) · 1.3 full model reduced stiffness (optional) · 1.4 load combination
  file · 1.5 CEDA development-length table (lap) · 1.6 CEDA input workbook (optional)
Everything the designer sets can be typed on screen OR uploaded in the input workbook (and saved back to Excel).
Overload (D/C > 1) is never accepted without the designer: rows are confirmed one by one on screen after the run.
The app never re-implements the design or input rules – it calls the skill scripts.
"""
import os, json, hashlib, tempfile, datetime
import pandas as pd
import streamlit as st
import app_io as AIO

INPW = AIO.INPW
st.set_page_config(page_title='CEDA Column Design', layout='wide')
st.title('CEDA RC Column Design')
st.caption(f'Engine = ceda-column-design skill v{AIO.ENGINE_VERSION} (bundled, unchanged). Units t, t-m, ksc. '
           'Draft outputs for engineer review – not construction drawings.')
ss = st.session_state
ss.setdefault('workdir', tempfile.mkdtemp(prefix='ceda_col_'))
ss.setdefault('ovl_ok', {})        # {(label, story): dc_max} confirmed on screen in this session
ss.setdefault('ovl_meta', {})


def _h(files):
    m = hashlib.md5()
    for f in files or []:
        if f is not None:
            m.update(f.name.encode()); m.update(f.getvalue())
    return m.hexdigest()


@st.cache_data(show_spinner='Reading ETABS tables …')
def _read(key, blobs):
    parts, info = [], []
    d = tempfile.mkdtemp()
    for name, data in blobs:
        p = os.path.join(d, name); open(p, 'wb').write(data)
        t, u, i = AIO.read_upload(p)
        parts.append((t, u)); info += i
    T, U = AIO.merge(parts)
    return T, U, info


def _save(name, data):
    p = os.path.join(tempfile.mkdtemp(), name); open(p, 'wb').write(data)
    return p


@st.cache_data(show_spinner=False)
def _read_tpl(key, name, data):
    return INPW.read_template(_save(name, data))


@st.cache_data(show_spinner=False)
def _lap_sheets(key, name, data):
    return INPW.lap_sheets(_save(name, data))


@st.cache_data(show_spinner=False)
def _lap(key, name, data, sheet):
    return INPW.read_lap_table(_save(name, data), sheet)


# ================================================================================================ 1 upload
st.header('1. Upload')
st.markdown('Same files as the BKMPH02 project. ETABS: *Display → Show Tables (Ctrl+T) → Export to Excel*; several workbooks per '
            'model are merged; a sheet pasted without its `TABLE:` row is read by its sheet name. From each model export '
            '**Element Forces – Columns** (combos + DL/SDL/LL for every story), **Column / Point Object Connectivity**, '
            '**Frame Assignments – Section Properties**, section definitions; seismic model also Story Forces / Drifts if available.')
r1 = st.columns(3)
up_files = {}
for col, (key, title), note in zip(r1, AIO.MODELS, ('required – above-ground EQ combos', 'required (BKMPH02 "02 Full Gravity")',
                                                     'optional – when given it is the primary full model (Rev.1)')):
    up_files[key] = col.file_uploader(f'1.{len(up_files) + 1} {title}', type=['xlsx', 'xlsm'], accept_multiple_files=True,
                                      key='up_' + key, help=note)
r2 = st.columns(3)
cf = r2[0].file_uploader('1.4 Load Combination Definitions (separate file, optional)', type=['xlsx'], key='up_combo',
                         help='Used in every model; replaces the ETABS definition of the same combo names.')
lf = r2[1].file_uploader('1.5 Development length table – lap (CEDA TABLE 11.04, optional)', type=['xlsx'], key='up_lap',
                         help='e.g. "Development of Reinforcement Table.xlsx"; Lst = Class B tension lap, other bar.')
tf = r2[2].file_uploader('1.6 CEDA input workbook (optional)', type=['xlsx'], key='up_tpl',
                         help='Every input below can be typed on screen or come from this workbook.')
r2[2].download_button('⬇ Blank input workbook', open(os.path.join(os.path.dirname(__file__), 'templates', 'CEDA_Column_Input_TEMPLATE.xlsx'), 'rb').read(),
                      'CEDA_Column_Input_TEMPLATE.xlsx')
lap_sheet = None
if lf:
    shs = _lap_sheets(_h([lf]), lf.name, lf.getvalue())
    lap_sheet = r2[1].selectbox('Lap table sheet (cover)', shs, index=next((i for i, s in enumerate(shs) if s.startswith('40')), 0))

models = {k: (_read(_h(v), [(f.name, f.getvalue()) for f in v]) if v else None) for k, v in up_files.items()}
combos = _read(_h([cf]), [(cf.name, cf.getvalue())]) if cf else None
tpl_up = _read_tpl(_h([tf]), tf.name, tf.getvalue()) if tf else AIO.empty_tpl()
lap_file = _lap(_h([lf]), lf.name, lf.getvalue(), lap_sheet) if lf else None
for m in list(models.values()) + [combos]:
    for i in (m[2] if m else []):
        st.caption(i)
for i in tpl_up.get('issues', []):
    st.warning(i)
if not models['seismic'] or not (models['full_unreduced'] or models['full_reduced']):
    st.info('Upload the seismic model and at least one full model (gravity / unreduced or reduced stiffness).')
    st.stop()
mdl = {k: (v[0], v[1]) if v else None for k, v in models.items()}
cmb = (combos[0], combos[1]) if combos else None


@st.cache_resource(max_entries=6, show_spinner='Preparing inputs (skill prepare_inputs) …')
def _prep(stamp_, tpl_json):
    """cached per upload stamp + inputs on screen (the uploaded tables are identified by the stamp)."""
    return AIO.prepare(mdl, cmb, json.loads(tpl_json))


up_stamp = _h([f for k in up_files for f in (up_files[k] or [])] + [cf])
p0 = _prep(up_stamp, json.dumps(tpl_up, default=str, sort_keys=True))
found = p0['found']

# ================================================================================================ 2 inputs (screen = workbook)
st.header('2. Inputs – type here or use the Excel workbook')
st.caption('Prefilled from the ETABS uploads, the lap table and the input workbook. What is on screen is what runs; '
           '"Save the inputs on screen" writes it back to the workbook. A new upload resets the screen to the files.')
stamp = _h([f for k in up_files for f in (up_files[k] or [])] + [cf, lf, tf]) + str(lap_sheet)
K = hashlib.md5(stamp.encode()).hexdigest()[:10]
if ss.get('ed_stamp') != K:
    for k in [k for k in ss.keys() if str(k).startswith('ed_') and not str(k).startswith('ed_' + K)]:
        del ss[k]
    ss['ed_stamp'] = K
    ss['ovl_ok'], ss['ovl_meta'] = {}, {}           # new inputs: every overload has to be confirmed again
    ss.pop('out', None)
cv = {k: (tpl_up['criteria'].get(k) if not INPW._blank(tpl_up['criteria'].get(k)) else d) for k, d, u, n in INPW.CRITERIA}
CAT, FRAME = ['ก', 'ข', 'ค', 'ง'], ['gravity', 'IMF', 'SMF']
FCS = [210, 240, 280, 320, 400, 450, 500, 560, 600, 700]
yn = lambda v: str(v).strip().upper().startswith('Y')


def W(container, key, label, kind='text', options=None, help_=None):
    """one criteria widget bound to the workbook key; returns the value in workbook form."""
    k = f'ed_{K}_c_' + key
    v = cv.get(key)
    if kind == 'yn':
        return 'Y' if container.checkbox(label, value=yn(v), key=k, help=help_) else 'N'
    if kind == 'sel':
        opts = [str(o) for o in options]
        sv = str(v) if v is not None else opts[0]
        if sv not in opts:                       # 400.0 from Excel matches option 400
            try:
                sv = next(o for o in opts if o and float(o) == float(sv))
            except (StopIteration, ValueError):
                pass
        return container.selectbox(label, opts, index=opts.index(sv) if sv in opts else 0, key=k, help=help_)
    if kind == 'num':
        try:
            fv = float(v)
        except (TypeError, ValueError):
            fv = 0.0
        return container.number_input(label, value=fv, key=k, help=help_)
    if kind == 'optnum':
        s = container.text_input(label, value='' if INPW._blank(v) else str(v), key=k, help=help_)
        try:
            return None if not s.strip() else float(s)
        except ValueError:
            container.error(f'{label}: not a number'); return None
    return container.text_input(label, value='' if v is None else str(v), key=k, help=help_)


def DF(rows, cols):
    return pd.DataFrame([list(r)[:len(cols)] + [None] * (len(cols) - len(r)) for r in rows], columns=cols)


def back(df):
    return [[None if (isinstance(v, float) and v != v) else v for v in r] for r in df.astype(object).where(pd.notna(df), None).values.tolist()
            if not all(x is None or (isinstance(x, str) and not x.strip()) or (isinstance(x, float) and x != x) for x in r)]


STO = list(found['stories'])
LABS = list(found['labels'])
crit = {}
tb = st.tabs(['Project', 'Seismic', 'Materials & detailing', "Stories / Lu / k / f'c", 'Columns (Lu per column)', 'Sections',
              'Load combinations', 'Lap table', 'Marks & story ranges', 'ρ / δ / exclude', 'Overload (D/C > 1)'])
with tb[0]:
    a_, b_ = st.columns(2)
    for i, (k, lab) in enumerate((('project.name', 'Project'), ('project.location', 'Location'), ('project.building', 'Building'),
                                  ('project.job', 'Job no. (file prefix)'), ('project.date', 'Date'), ('project.calc_by_1', 'Calculated by (name, licence)'),
                                  ('project.calc_by_2', 'Checked by (name, licence)'), ('project.approve_by', 'Approved by (name, licence)'))):
        crit[k] = W(a_ if i % 2 == 0 else b_, k, lab)
with tb[1]:
    a_, b_, c_ = st.columns(3)
    crit['seismic.design'] = W(a_, 'seismic.design', 'Seismic design required', 'yn')
    crit['seismic.category'] = W(b_, 'seismic.category', 'Seismic design category', 'sel', CAT)
    crit['seismic.frame'] = W(c_, 'seismic.frame', 'Columns are', 'sel', FRAME)
    crit['seismic.zone'] = W(a_, 'seismic.zone', 'Zone')
    crit['seismic.importance'] = W(b_, 'seismic.importance', 'Importance factor')
    crit['seismic.system'] = W(c_, 'seismic.system', 'Lateral system (มยผ. 1301/1302-61 Table 2.3-1)')
    crit['seismic.R'] = W(a_, 'seismic.R', 'R', 'num'); crit['seismic.Omega0'] = W(b_, 'seismic.Omega0', 'Ω0', 'num')
    crit['seismic.Cd'] = W(c_, 'seismic.Cd', 'Cd', 'num')
    if crit['seismic.category'] == 'ง':
        st.warning('Category ง with ordinary walls: height ≤ 60 m and seismic force +40 % (มยผ.) – check.')
    if crit['seismic.frame'] == 'SMF':
        st.warning('SMF detailing (ACI 18.7) is not automated – design forces only.')
with tb[2]:
    a_, b_, c_, d_ = st.columns(4)
    crit['materials.fc_typical'] = int(float(W(a_, 'materials.fc_typical', "Typical f'c (ksc, cylinder)", 'sel', FCS)))
    crit['materials.fy'] = W(b_, 'materials.fy', 'fy (ksc) – all bar sizes', 'num')
    crit['materials.fyt'] = W(c_, 'materials.fyt', 'fyt ties (ksc)', 'num')
    crit['materials.fc_slab'] = W(d_, 'materials.fc_slab', "Slab f'c (ksc) – ACI 15.5", 'num')
    crit['materials.fc_mode'] = W(a_, 'materials.fc_mode', "Column f'c", 'sel', ['auto', 'fixed'],
                                  "auto = skill f'c study; fixed = f'c per story in the Stories tab (or bottom f'c below the story given)")
    crit['materials.fc_bottom'] = int(float(W(b_, 'materials.fc_bottom', "Bottom f'c (fixed, when Stories has none)", 'sel', FCS)))
    crit['materials.fc_reduce_at'] = W(c_, 'materials.fc_reduce_at', "Typical f'c from story (fixed)", 'sel', [''] + STO)
    crit['detailing.cover_mm'] = W(d_, 'detailing.cover_mm', 'Cover to ties (mm)', 'num')
    crit['detailing.tie_db'] = int(float(W(a_, 'detailing.tie_db', 'Tie size (mm)', 'sel', [12, 16])))
    crit['detailing.size_restricted'] = W(b_, 'detailing.size_restricted', 'Column size restricted (ρ 6–8 % may be approved)', 'yn')
    crit['slender.k'] = W(c_, 'slender.k', 'Default k', 'num')
    crit['slender.beta_d'] = W(d_, 'slender.beta_d', 'βd (blank = from DL/SDL/LL cases)', 'optnum')
    crit['slender.sway'] = W(a_, 'slender.sway', 'Sway check', 'sel', ['', 'non-sway'],
                             'blank = Q from Story Forces/Drifts (ACI 6.6.4.3); non-sway = Engineering judgment, reported')
    crit['gravity.DL'] = W(b_, 'gravity.DL', 'DL case names'); crit['gravity.SDL'] = W(c_, 'gravity.SDL', 'SDL case names')
    crit['gravity.LL'] = W(d_, 'gravity.LL', 'LL case names')
    st.caption('Bar rules (fixed, skill §5): face ≤ 200/540/660 mm → 2/3/4 bars, else c/c 125–150 mm (singles, 2-bar bundles); '
               'bundles from the tie corners, each size over the whole section before the next; wider grid c/c ≤ 160 mm for 3–4-bar '
               'bundles; inner bars last (basement or approved ρ); ρ ≤ 6 %; couplers for 3–4-bar bundles.')
with tb[3]:
    st.markdown("Bottom → top. Lu_m / k = whole story; basement Y; fc_ksc = fixed f'c per story (f'c mode fixed). "
                "z (m) only when ETABS has no Point Object Connectivity.")
    st0 = tpl_up['stories'] or [[s, *found['z'].get(s, (None, None)), None, None, None, None] for s in STO]
    st_df = st.data_editor(DF(st0, INPW.HDR['Stories']), hide_index=True, width='stretch', num_rows='dynamic', key=f'ed_{K}_stories',
                           column_config={'basement': st.column_config.SelectboxColumn(options=['', 'Y', 'N'])})
with tb[4]:
    st.markdown('One row per column-story: Lu / k of that column only (e.g. ramp columns with deep beams), XY (m) only to match '
                'labels between models.')
    co_df = st.data_editor(DF(tpl_up['columns'], INPW.HDR['Columns']), hide_index=True, width='stretch', num_rows='dynamic',
                           key=f'ed_{K}_columns', column_config={'label': st.column_config.SelectboxColumn(options=LABS),
                                                                  'story': st.column_config.SelectboxColumn(options=STO)})
with tb[5]:
    have = found['sec_of']
    if have:
        with st.expander(f'Sizes read from ETABS ({len(have)} labels)'):
            st.dataframe(pd.DataFrame([dict(label=l, sizes=', '.join(f'{sh} {b}×{h}' + (' (name)' if a else '') for sh, b, h, a in sorted(s)))
                                       for l, s in sorted(have.items(), key=lambda kv: (len(kv[0]), kv[0]))]), hide_index=True, width='stretch')
    st.markdown('**Sizes set by the designer** – replace ETABS only for the label-stories listed (blank stories = all). '
                'b = t2 (My), h = t3 (Mx), mm. The forces stay those of the current ETABS model – update ETABS and rerun.')
    se0 = tpl_up['sections'] or [[l, None, None, 'rect', None, None] for l in LABS if l not in have]
    se_df = st.data_editor(DF(se0, INPW.HDR['Sections']), hide_index=True, width='stretch', num_rows='dynamic', key=f'ed_{K}_sections',
                           column_config={'shape': st.column_config.SelectboxColumn(options=['rect', 'circ']),
                                          'label': st.column_config.SelectboxColumn(options=LABS),
                                          'story_from': st.column_config.SelectboxColumn(options=[''] + STO),
                                          'story_to': st.column_config.SelectboxColumn(options=[''] + STO)})
with tb[6]:
    cases0 = tpl_up['combo_cases'] or list(found['cases']) or ['DL', 'SDL', 'LL', 'EQX', 'EQY']
    ctxt = st.text_input('Load case columns (ETABS load case names, comma separated)', ', '.join(cases0), key=f'ed_{K}_cases')
    cases = [c.strip() for c in ctxt.split(',') if c.strip()]
    st.markdown('Rows here replace the ETABS / combination-file definition of that combo (row wins). Leave empty when the '
                'combination file or ETABS already defines every combo.')
    if tpl_up['combos_rows']:
        cb0 = [[r[0]] + [dict(zip(cases0, r[1:])).get(c) for c in cases] for r in tpl_up['combos_rows']]
    else:
        cb0 = [[c] + [None] * len(cases) for c in p0['undefined']]
    cb_df = st.data_editor(DF(cb0, ['combo'] + list(cases)), hide_index=True, width='stretch', num_rows='dynamic',
                           key=f'ed_{K}_combos_' + hashlib.md5(ctxt.encode()).hexdigest()[:8])
    ex = st.multiselect('Exclude combos', found['combos'], default=[c for c in tpl_up['exclude'] if c in found['combos']], key=f'ed_{K}_excl')
with tb[7]:
    if tpl_up['lap_rows']:
        lap0, lsrc = tpl_up['lap_rows'], 'input workbook (Lap sheet)'
    elif lap_file:
        lap0, lsrc = lap_file[0], f'lap table file – {lap_file[1]}'
    else:
        lap0, lsrc = [[f] + [INPW.LAP_KNOWN.get(f, {}).get(d) for d in (12, 16, 20, 25, 28, 32)] for f in (400, 560)], \
            'not given – fill the project lap table (blank = unknown, never invented)'
    st.markdown(f'Class B tension lap Lst (other bar), mm. Source: **{lsrc}**.')
    lp_df = st.data_editor(DF(lap0, INPW.HDR['Lap']), hide_index=True, width='stretch', num_rows='dynamic', key=f'ed_{K}_lap')
with tb[8]:
    a_, b_, c_ = st.columns(3)
    crit['marks.envelope'] = W(a_, 'marks.envelope', 'Mark envelope (criterion A)', 'yn')
    crit['marks.max_weight_pct'] = W(b_, 'marks.max_weight_pct', 'per label: max extra longitudinal steel (%)', 'num')
    crit['marks.project_max_weight_pct'] = W(c_, 'marks.project_max_weight_pct', 'project: max extra steel (%)', 'num')
    crit['marks.max_rows'] = W(a_, 'marks.max_rows', 'max rows that differ (blank = no limit)', 'optnum')
    crit['marks.max_step'] = W(b_, 'marks.max_step', 'max ladder steps per row (blank = no limit)', 'optnum')
    crit['story_ranges.mode'] = W(c_, 'story_ranges.mode', 'Story ranges (when the table below is empty)', 'sel', ['auto', 'each'],
                                  'auto: basement every story, above ground 2–3 stories / 12 m + Lst')
    st.markdown('**Story ranges fixed by the designer** (optional) – bottom → top, every story exactly once, e.g. `+00 → GF` merged. '
                'Empty = engine ranges.')
    rg0 = ss.pop(f'rg_prefill_{K}', None) or tpl_up.get('ranges') or []
    if f'rg_ver_{K}' not in ss:
        ss[f'rg_ver_{K}'] = 0
    if st.button('Prefill with the ranges of the last run', disabled='out' not in ss):
        ss[f'rg_prefill_{K}'] = json.load(open(os.path.join(ss['out'], 'results.json')))['bands']
        ss[f'rg_ver_{K}'] += 1
        st.rerun()
    rg_df = st.data_editor(DF(rg0, INPW.HDR['Story_ranges']), hide_index=True, width='stretch', num_rows='dynamic',
                           key=f"ed_{K}_ranges_{ss[f'rg_ver_{K}']}",
                           column_config={c: st.column_config.SelectboxColumn(options=STO) for c in INPW.HDR['Story_ranges']})
with tb[9]:
    st.markdown('**ρ 6–8 % approved** (only with "Column size restricted" = Y) – label-story:')
    ap_df = st.data_editor(DF(tpl_up['approve'], INPW.HDR['Approve_rho']), hide_index=True, width='stretch', num_rows='dynamic',
                           key=f'ed_{K}_appr', column_config={'label': st.column_config.SelectboxColumn(options=LABS),
                                                               'story': st.column_config.SelectboxColumn(options=STO)})
    st.markdown('**δ > 1.4 accepted by the engineer** (ACI 6.2.5.3 limit 1.4 – Engineering judgment):')
    dl_df = st.data_editor(DF(tpl_up['delta_ok'], INPW.HDR['Accept_delta']), hide_index=True, width='stretch', num_rows='dynamic',
                           key=f'ed_{K}_delta', column_config={'label': st.column_config.SelectboxColumn(options=LABS),
                                                                'story': st.column_config.SelectboxColumn(options=STO)})
with tb[10]:
    st.markdown('**Proposed overload acceptances** (label, story, dc_max). These are **not applied** until each row is '
                'confirmed on screen after the run (section 5) – CEDA rule: overload is never accepted without asking, every run.')
    ov_df = st.data_editor(DF(tpl_up['overload'], INPW.HDR['Accept_overload']), hide_index=True, width='stretch', num_rows='dynamic',
                           key=f'ed_{K}_ovl', column_config={'label': st.column_config.SelectboxColumn(options=LABS),
                                                              'story': st.column_config.SelectboxColumn(options=STO)})

tpl = dict(criteria=crit, stories=back(st_df), columns=back(co_df),
           sections=[r for r in back(se_df) if r[0] and r[4] is not None],
           combos_rows=[r for r in back(cb_df) if r[0] and any(v not in (None, '') for v in r[1:])], combo_cases=list(cases),
           lap_rows=back(lp_df), exclude=list(ex), approve=back(ap_df), overload=back(ov_df), delta_ok=back(dl_df),
           ranges=[r for r in back(rg_df) if r[0] and r[1]], issues=[])
prep = _prep(up_stamp, json.dumps(tpl, default=str, sort_keys=True))
found = prep['found']
st.download_button('⬇ Save the inputs on screen as an input workbook (Excel)', INPW.make_template(found, tpl),
                   f"{crit.get('project.job') or 'JOB'}_Column_Input.xlsx")

# ================================================================================================ 3 input check
st.header('3. Input check')
for n in prep['route']:
    (st.warning if 'ASSUMPTION' in n else st.caption)(('⚠ ' if 'ASSUMPTION' in n else 'ℹ ') + n)
chk = AIO.input_check(prep)
cdf = pd.DataFrame(chk)
st.dataframe(cdf.assign(ok=cdf['ok'].map({True: '✔', False: '✖ fill in the tab above or the workbook'})), hide_index=True, width='stretch')
with st.expander(f"Merge report ({len(prep['merge_rep'])})"):
    for r in prep['merge_rep']:
        st.caption('ℹ ' + r)
missing = not cdf['ok'].all()
cfg_t = prep['cfg_tpl']
if cfg_t['approved_rho_over_6'] == [] and tpl['approve']:
    st.warning('Approve_rho rows are ignored: "Column size restricted" is N.')
st.caption(f"Overload: {len(ss['ovl_ok'])} row(s) confirmed on screen in this session"
           + (f"; {len([r for r in tpl['overload'] if (r[0], r[1]) not in ss['ovl_ok']])} proposed row(s) not confirmed (not applied)"
              if tpl['overload'] else ''))
confirm = st.checkbox('I confirm the inputs and design criteria above (skill: never run before the criteria are confirmed)')
if missing:
    st.error('Some inputs are missing – fill them in the tabs above (or in the input workbook and upload it again).')


def do_run():
    with st.status('Running engine (run.py → make_outputs.py) …') as stt:
        try:
            cfg = AIO.build_cfg(prep, ss['workdir'], ss['ovl_ok'])
            res, out = AIO.run_engine(ss['workdir'], cfg)
            json.dump(cfg, open(os.path.join(out, 'config_used.json'), 'w'), ensure_ascii=False, indent=1)
            job = cfg['project'].get('job', 'job')
            tpl_used = dict(tpl, overload=[[l, s, d] for (l, s), d in sorted(ss['ovl_ok'].items())] +
                            [r for r in tpl['overload'] if (r[0], r[1]) not in ss['ovl_ok']])
            open(os.path.join(out, f'{job}_Column_Input_used.xlsx'), 'wb').write(INPW.make_template(found, tpl_used))
            open(os.path.join(out, f'{job}_Column_Decisions_Log.xlsx'), 'wb').write(AIO.decisions_log(tpl, cfg, res, prep, ss['ovl_meta']))
            ss['out'] = out
            stt.update(label='Done', state='complete')
        except Exception as e:
            stt.update(label='Engine error', state='error'); st.exception(e); st.stop()


if st.button('▶ Run design', type='primary', disabled=not confirm or missing):
    do_run()
if ss.pop('rerun_req', False):
    do_run()
if 'out' not in ss:
    st.stop()

# ================================================================================================ 4 results
out = ss['out']
res = json.load(open(os.path.join(out, 'results.json')))
R = res['results']
job = res['config']['project'].get('job', 'job')
st.header('4. Results')
cnt = lambda s: sum(1 for r in R for q in r['per'] if q['status'] == s)
m = st.columns(7)
m[0].metric('Labels', len(res['marks'])); m[1].metric('Marks', len(set(res['marks'].values())))
m[2].metric('Story ranges', len(res['bands'])); m[3].metric('OK', cnt('OK')); m[4].metric('ACCEPTED (overload)', cnt('ACCEPTED'))
m[5].metric('ASK ρ 6–8 %', cnt('ASK_RHO')); m[6].metric('REVISE', cnt('REVISE'))
if res['config'].get('accept_overload_pending'):
    st.warning('Proposed overload rows NOT applied (not confirmed): ' +
               ', '.join(f'{a} {b} ≤ {c}' for a, b, c in res['config']['accept_overload_pending']))
with st.expander(f"Review checkpoints / notes ({len(res['notes'])})", expanded=bool(cnt('REVISE') or cnt('ASK_RHO'))):
    for n in res['notes']:
        (st.error if n.startswith(('SWAY', 'combo')) else st.warning)(n)
    fi = res.get('fcinfo', {})
    if fi and not fi.get('fixed'):
        st.info(f"f'c study: bottom {fi.get('fc_bottom')} ksc, reduce to {fi.get('fc_typical')} ksc at {fi.get('reduce_at')}")
        if fi.get('table'):
            st.dataframe(pd.DataFrame(fi['table']), hide_index=True)

# ------------------------------------------------------------------------------------------------ 5 designer decisions
rv = AIO.review_rows(res)
st.header('5. Designer decisions – REVISE / overload')
props = {(r[0], r[1]): r[2] for r in tpl['overload'] if r[0] and r[1]}
ovl_rows = [d for d in rv if d['status'] in ('REVISE', 'ACCEPTED')]
for (l, s_), dmx in props.items():
    if not any(d['label'] == l and d['story'] == s_ for d in ovl_rows):
        ovl_rows.append(dict(status='(proposed)', label=l, story=s_, mark='', section='', fc=None, bars='', rho_pct=None, DC=None, delta=None, combo=''))
if not ovl_rows:
    st.success('No REVISE and no overload – nothing to decide.')
else:
    st.markdown('For each row the engine shows the steel it ended with (REVISE = no ladder step passes on the grids tried: 125–150, '
                'wider grid, inner bars where allowed) and its D/C. Options: enlarge the section (Sections tab), higher f\'c, approve ρ 6–8 % (ρ tab), or accept '
                'the overload up to a D/C you state – **Engineering judgment, ACI 318 requires φSn ≥ U**. Tick only the rows you '
                'accept now; nothing is accepted without the tick.')
    dfo = pd.DataFrame([dict(accept=(d['label'], d['story']) in ss['ovl_ok'], label=d['label'], story=d['story'], status=d['status'],
                             section=d['section'], fc=d['fc'], bars=d['bars'], rho_pct=d['rho_pct'], DC_engine=d['DC'],
                             dc_max=ss['ovl_ok'].get((d['label'], d['story']), props.get((d['label'], d['story']))), combo=d['combo'])
                        for d in ovl_rows])
    ed = st.data_editor(dfo, hide_index=True, width='stretch', key=f"ovl_ed_{os.path.getmtime(os.path.join(out, 'results.json'))}",
                        disabled=[c for c in dfo.columns if c not in ('accept', 'dc_max')],
                        column_config={'accept': st.column_config.CheckboxColumn('accept overload'),
                                       'dc_max': st.column_config.NumberColumn('accepted D/C ≤', min_value=1.0, step=0.01, format='%.2f')})
    bad = [f"{r.label} {r.story}" for r in ed.itertuples() if r.accept and (pd.isna(r.dc_max) or r.dc_max <= 1.0)]
    low = [f"{r.label} {r.story} (D/C {r.DC_engine} > {r.dc_max})" for r in ed.itertuples()
           if r.accept and not pd.isna(r.dc_max) and not pd.isna(r.DC_engine) and r.DC_engine > r.dc_max]
    if bad:
        st.error('Give "accepted D/C ≤" (> 1.0) for: ' + ', '.join(bad))
    if low:
        st.info('Accepted D/C below the D/C shown – the rerun searches every grid again with the new limit and may still '
                'end REVISE: ' + ', '.join(low))
    who = st.text_input('Confirmed by', value=str(crit.get('project.calc_by_1') or ''), key='ovl_who')
    new = {(r.label, r.story): float(r.dc_max) for r in ed.itertuples() if r.accept and not pd.isna(r.dc_max)}
    if st.button('✔ Confirm the ticked rows and run again', type='primary', disabled=bool(bad) or new == ss['ovl_ok']):
        now = datetime.datetime.now().strftime('%d %b %Y %H:%M')
        ss['ovl_meta'] = {k: (ss['ovl_meta'].get(k) if ss['ovl_ok'].get(k) == v else dict(at=now, by=who)) for k, v in new.items()}
        ss['ovl_ok'] = new
        ss['rerun_req'] = True
        st.rerun()
other = [d for d in rv if d['status'] == 'ASK_RHO' or (d['status'] == 'OK' and d['delta'] > 1.4)]
if other:
    with st.expander(f'ASK ρ 6–8 % / δ > 1.4 ({len(other)}) – decide in the "ρ / δ / exclude" tab, then run again'):
        st.dataframe(pd.DataFrame(other), hide_index=True, width='stretch')


def cell(r):
    d = AIO.LY.describe(r['counts'], r.get('phase', 0))
    return f"{r['nbar']}-DB{r['db']}" + (' (' + d.lower().replace('bundle ', 'b').replace(' @ tie corners', '') + ')' if d else '')


marks = sorted(set(res['marks'].values()), key=lambda m_: int(''.join(ch for ch in m_ if ch.isdigit()) or 0))
st.header('6. Outputs')
tabs = st.tabs(['Label → Mark', 'Table of Column', 'Interaction surface', 'DXF', 'Column plan', 'Downloads', 'Decision (label × story)'])
with tabs[0]:
    rows = []
    for lab, mk in sorted(res['marks'].items(), key=lambda kv: (int(''.join(ch for ch in kv[1] if ch.isdigit()) or 0), kv[0])):
        rr = [r for r in R if r['label'] == lab]
        rows.append(dict(label=lab, mark=mk, section=f"{rr[0]['b'] * 10:.0f}×{rr[0]['h'] * 10:.0f}",
                         stories=f"{rr[0]['stories'][0]} → {rr[-1]['stories'][-1]}", rotated='yes' if rr[0].get('rotated') else '',
                         reference='●' if rr[0].get('ref') else '', max_DC=round(max(q['dc'] for r in rr for q in r['per']), 3),
                         status=', '.join(sorted({q['status'] for r in rr for q in r['per']}))))
    st.dataframe(pd.DataFrame(rows), hide_index=True, width='stretch')
with tabs[1]:
    bands = [tuple(b) for b in res['bands']]
    ref = {(r['mark'], tuple(r['band'])): r for r in R if r.get('ref')}
    grid = []
    for b in reversed(bands):
        row = {'story range': f'{b[0]} → {b[1]}', "f'c": res['fc_of'][b[0]]}
        for mk in marks:
            r = ref.get((mk, b))
            if r:
                dcm = max(q['dc'] for x in R if x['mark'] == mk and tuple(x['band']) == b for q in x['per'])
                row[mk] = f"{r['b'] * 10:.0f}×{r['h'] * 10:.0f} | {cell(r)} | {r['nset']}ป DB{r['tie_db']}@{r['so']}/{r['s']} | D/C {dcm:.2f}"
            else:
                row[mk] = ''
        grid.append(row)
    st.dataframe(pd.DataFrame(grid), hide_index=True, width='stretch', height=min(800, 60 + 36 * len(grid)))
with tabs[2]:
    a, b = st.columns(2)
    mk = a.selectbox('Mark', marks, key='smk')
    bl = [tuple(r['band']) for r in R if r['mark'] == mk and r.get('ref')]
    bsel = b.selectbox('Story range', bl, format_func=lambda x: f'{x[0]} → {x[1]}', key='sbd')

    @st.cache_resource(show_spinner='Building the interaction surface …')
    def _surf(out_, mk_, b_, stamp_):
        return AIO.surface_figures(AIO.mark_band_eval(out_, mk_, b_))
    f3, f2, fc_, gov = _surf(out, mk, bsel, os.path.getmtime(os.path.join(out, 'results.json')))
    r = gov['r']
    st.markdown(f"**{mk}  {bsel[0]} → {bsel[1]}** · {r['b'] * 10:.0f}×{r['h'] * 10:.0f} mm · {cell(r)} · f'c {res['fc_of'][bsel[0]]} ksc · "
                f"governing {gov['label']} {gov['story']} – D/C **{gov['ev']['dcmax']:.3f}**")
    st.plotly_chart(f3, width='stretch')
    x1, x2, x3 = st.columns(3)
    x1.plotly_chart(f2[0], width='stretch'); x2.plotly_chart(f2[1], width='stretch'); x3.plotly_chart(fc_, width='stretch')
main_files, per_mark = AIO.files(out)


@st.cache_data(show_spinner='Rendering DXF …')
def _png(p, stamp_, dpi=200):
    return AIO.dxf_png(p, dpi)


with tabs[3]:
    dxf = next((p for p, n, d in main_files if n.endswith('Table_of_Column_DRAFT.dxf')), None)
    if dxf:
        st.download_button('Download DXF', open(dxf, 'rb').read(), os.path.basename(dxf))
        st.image(_png(dxf, os.path.getmtime(dxf)), width='stretch')
with tabs[4]:
    st.markdown('Column mapping plan of one story: true-size sections with mark + label (skill `plan_map.py`, from the Point Object '
                'Connectivity of the primary full model). ASSUMPTION: local axis angle 0 (h along X, b along Y).')
    a, b = st.columns([1, 3])
    pst = a.selectbox('Story', res['stories'], key='pm_story')
    if a.button('Make column plan'):
        try:
            ss['pm'] = (pst,) + AIO.plan_map(ss['workdir'], out, pst)
        except Exception as e:
            st.error(f'plan_map: {e}')
    if ss.get('pm') and ss['pm'][0] == pst and os.path.exists(ss['pm'][2]):
        _, pdf, dxp, prow = ss['pm']
        b.download_button('Column plan PDF (A1)', open(pdf, 'rb').read(), os.path.basename(pdf))
        b.download_button('Column plan DXF', open(dxp, 'rb').read(), os.path.basename(dxp))
        nop = [x['label'] for x in prow if x.get('x') is None]
        if nop:
            st.warning('No point in the export (not drawn): ' + ', '.join(nop))
        st.image(_png(dxp, os.path.getmtime(dxp), 120), width='stretch')
with tabs[5]:
    st.download_button('⬇ All outputs (ZIP)', AIO.zip_all(out), f'{job}_Column_outputs.zip', type='primary')
    iu = os.path.join(out, f'{job}_Column_Input_used.xlsx')
    if os.path.exists(iu):
        st.download_button('⬇ Input workbook used (re-use / archive)', open(iu, 'rb').read(), os.path.basename(iu))
    st.subheader('Project files')
    for p, n, d in main_files:
        st.download_button(f'{n}  –  {d}', open(p, 'rb').read(), n, key='dl_' + n)
    st.subheader('Per mark: calculation sheets + back-up calculation')
    for mk_ in sorted(per_mark, key=lambda m_: int(''.join(ch for ch in m_ if ch.isdigit()) or 0)):
        cA, cB, cC = st.columns([1, 2, 2])
        cA.markdown(f'**{mk_}** – ' + ', '.join(sorted(l for l, m_ in res['marks'].items() if m_ == mk_)))
        if 'Calc.pdf' in per_mark[mk_]:
            cB.download_button(f'{mk_} calculation (PDF)', open(per_mark[mk_]['Calc.pdf'], 'rb').read(), os.path.basename(per_mark[mk_]['Calc.pdf']), key='c_' + mk_)
        if 'Backup.xlsx' in per_mark[mk_]:
            cC.download_button(f'{mk_} back-up (Excel)', open(per_mark[mk_]['Backup.xlsx'], 'rb').read(), os.path.basename(per_mark[mk_]['Backup.xlsx']), key='b_' + mk_)
    st.subheader('Detailed CEDA-style Excel (one mark-range, on request)')
    a, b, c = st.columns(3)
    dmk = a.selectbox('Mark ', marks, key='dmk')
    dbd = b.selectbox('Story range ', [tuple(r['band']) for r in R if r['mark'] == dmk and r.get('ref')], format_func=lambda x: f'{x[0]} → {x[1]}', key='dbd')
    if c.button('Make detailed Excel'):
        p = AIO.detail_excel(out, dmk, dbd[0])
        st.download_button(f'Download {os.path.basename(p)}', open(p, 'rb').read(), os.path.basename(p))
with tabs[6]:
    rows = []
    for r in R:
        for q in r['per']:
            rows.append(dict(mark=r['mark'], label=r['label'], story=q['story'], drawing=f"{q['dwg'][0]}→{q['dwg'][1]}",
                             range=f"{r['band'][0]}→{r['band'][1]}", section=f"{r['b'] * 10:.0f}×{r['h'] * 10:.0f}", fc=q['fc'], bars=cell(r),
                             rho_pct=round(q['rho'] * 100, 2), DC=round(q['dc'], 3), gov_combo=q['gov'].get('combo', ''),
                             Pu_t=round(q['gov']['P'] / 1e3, 1), kLu_r=f"{q['slr_x']:.0f}/{q['slr_y']:.0f}",
                             delta_max=round(max(q['dmax_x'], q['dmax_y']), 2), shear_DC=round(max(v['dc_lo'] for v in q['shear'].values()), 2),
                             ties=f"{r['nset']}ป DB{r['tie_db']}@{r['so']}/{r['s']}", status=q['status']))
    df = pd.DataFrame(rows)
    flt = st.multiselect('Status', sorted(df['status'].unique()), default=sorted(df['status'].unique()))
    st.dataframe(df[df['status'].isin(flt)], hide_index=True, width='stretch')
