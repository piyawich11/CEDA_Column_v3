---
name: "ceda-column-design"
description: "CEDA RC column design from ETABS exports (+ CEDA input workbook) – combo check (กฎกระทรวง 2566), basement load assembly, biaxial 3D interaction surface D/C, slenderness, bars/ties per CEDA rules, f'c reduction, story ranges, marks with envelope, calc PDF, back-up Excel, draft Table of Column (PDF/DXF/Excel) and column mapping plan. Use for ออกแบบเสา, column design, table of column."
---

# CEDA RC Column Design (v1.3.6)

Units: cm, kg, ksc internally; reports in t, t-m, ksc only. Tag every item **Code requirement (clause) / Common practice /
Engineering judgment / Assumption**. Keep CEDA numbering, terminology and report style; reply in formal, concise Thai.
Never calculate before Step 1 is answered and confirmed. Never change an agreed rule or assumption silently.
**Overload (D/C > 1) is never accepted without asking the designer – every time, every project, every run** (CEDA 21 Oct 2026).
This file holds the workflow, the start-up questions and the CEDA rules; every formula is in `scripts/`, the method and
coefficients in `references/`, the correct values in `tests/`.

## Package
```
ceda-column-design/
├─ SKILL.md            workflow, start-up questions, CEDA rules (no calculation code)
├─ scripts/            engine – JSON in / JSON out
│  ├─ prepare_inputs.py   uploads (ETABS + CEDA input workbook) -> config.json, input_check.json
│  ├─ run.py              config.json -> results.json, state.pkl, <job>_Column_Decision.xlsx
│  ├─ make_outputs.py     results -> calc PDF, back-up Excel, Table of Column PDF/DXF/Excel (--per-mark, --detail)
│  ├─ plan_map.py         column mapping plan of one story: true-size sections, mark + label (PDF A1 + DXF)
│  ├─ design.py layout.py colsurf.py etabs_io.py input_workbook.py + output writers
│  └─ selftest.py         python3 -I selftest.py <skill folder>  -> must print ALL PASS
├─ tests/              expected.json (correct values + source), fixtures/ (incl. paattern.dxf), voco_regression/ (vs issued drawing),
│                      bkmph02_regression/ (first real project record + decisions log)
├─ references/         method.md, bars_ranges_marks.md, loads_and_inputs.md, design basis Rev.1, Excel review, lap sheet
└─ assets/             CEDA_Column_Input_TEMPLATE.xlsx, config_template.json, ceda_logo.jpeg
```
Master copy: `D:\OneDrive - CEDA Company Limited\99999 AI Project\Skill\Column\Ceda\Claude skills\ceda-column-design\`
(stage the whole folder; in claude.ai chat ask the designer to upload it). Apps (Streamlit) call these scripts, never re-implement them.

## 1. Ask first (AskUserQuestion; the CEDA input workbook may already answer them – show its values and ask to confirm)
1. Project header: name, location, building, job no., date, calculated / checked / approved by.
2. **Seismic**: required? zone, importance; **category ก/ข/ค/ง**; lateral system with **R / Ω0 / Cd** (มยผ. 1301/1302-61 Table 2.3-1,
   e.g. building frame + ordinary RC shear wall R 5, Ω0 2.5, Cd 4.5); columns **gravity / IMF / SMF**. Category ง with ordinary walls:
   height ≤ 60 m and seismic force +40 % – remind.
3. Materials: typical f'c of the project (columns reduce to it), f'c auto study or fixed, fy, fyt, cover, tie size, slab f'c.
4. Lu / k per story band (default k 1.0, Lu = column length from connectivity) – ask for **each basement band**, never one value for all
   (VOCO: B6-B5 Lu 2.75 m).
5. Column size restricted? (only then ρ 6–8 % may be approved, never > 8 %).
6. Lap table S-00-04-04 of the project for every f'c and bar size (never invent a lap).
7. Marks: envelope on (criterion A: per label ≤ 25 % extra steel, project ≤ 10 %) or exact match only.
8. Story ranges fixed by the designer (e.g. a story without a real floor merged with the next)? Basement stories (from ETABS, else ask).
9. Special columns: Lu from the clear height where deep beams / ramps frame in (ask the beam depth), k if not 1.0.
Unanswered items: list them with the proposed value and wait for confirmation. Do not take values from memory or another project.

## 2. Inputs
- ETABS exports per model (seismic / full reduced / full unreduced) – tables in `references/loads_and_inputs.md` §1. From the full
  model ask for **Element Forces – Columns (combos + DL/SDL/LL for every story)**, **Column Object Connectivity**, **Point Object
  Connectivity** (X, Y, Z: story order, Lu, plan), Frame Assignments – Section Properties, section definitions (incl. Concrete Circle);
  optional Frame Assignments – Local Axes, Grid Lines, Story Forces / Drifts. Load Combination Definitions may come as a separate file.
  ETABS: Display → Show Tables (Ctrl+T) → tick the tables → Export to Excel. A sheet pasted without its 'TABLE:' row is read by its
  sheet name. Labels with forces but no connectivity/section → list them in Excel for the designer (never drop them silently).
- CEDA input workbook (`assets/CEDA_Column_Input_TEMPLATE.xlsx`) for everything the export lacks or the designer sets:
  Criteria, Stories, Columns (connectivity, Lu/k per column-story), Sections (per label-story), Combos, Lap, Exclude, Approve_rho,
  Accept_overload, Accept_delta, Story_ranges (designer ranges, every story once). The workbook wins per item and is reported.
- Same file set as BKMPH02: seismic model, full model gravity (unreduced), full model reduced stiffness (optional), a separate
  Load Combination Definitions file (used in every model, replaces the same combo names), the CEDA development-length table
  (TABLE 11.04, sheet per cover – Lst fills the Lap sheet when the workbook has none). **Only an unreduced full model → it is used
  as the primary full model (geometry, βd, basement ΔP) – ASSUMPTION, reported**; with a reduced model, reduced = primary (Rev.1).
- `prepare_inputs.py --template` writes a workbook prefilled from the ETABS uploads for the designer to complete.

## 3. Run
1. Copy the skill folder to the scratchpad. Packages: numpy, scipy, matplotlib, openpyxl, ezdxf (`pip install --break-system-packages ezdxf`);
   LibreOffice for Excel recalculation.
2. **Self-test** from an empty folder: `python3 -I <skill>/scripts/selftest.py <skill>` → **ALL PASS**, else stop and report.
3. `python3 -I prepare_inputs.py W --seismic … [--full-reduced …] [--full-unreduced …] [--combos LC.xlsx]
   [--lap-table DevLength.xlsx --lap-sheet 40mm] [--workbook input.xlsx]` → show
   `input_check.json` (✔/✖); missing → ask or fill the workbook. (Or write `config.json` from `assets/config_template.json`.)
   Rows in Accept_overload are applied only with `--overload-confirmed`, and only after the designer confirmed each row **in this
   session** (show label, story, D/C reached with the most steel that fits, alternatives); otherwise they stay pending (exit 2).
4. `python3 -I run.py W/config.json W/OUT` → `python3 -I make_outputs.py W/OUT --per-mark`;
   on request `make_outputs.py W/OUT --detail <MARK> <bottom story>` and `plan_map.py <full model xlsx> W/OUT/results.json <prefix> <story>`.
5. Recalculate every Excel (xlsx skill `recalc.py`) – zero errors before delivery.

## 4. Review checkpoints (stop and ask)
- Combo check ข้อ 7 mismatches (never judge a combo by its name) → include or exclude.
- Sway Q > 0.05 (ACI 6.6.4.3) → STOP (δs not automated); no Story Forces/Drifts → ask: export them, or non-sway assumed by the
  engineer (`slender.sway = non-sway`, reported as Engineering judgment).
- ASK_RHO (6 % < ρ ≤ 8 %) → ask; REVISE → never accept on your own: show for each label-story the most steel that fits (125–150 grid,
  wider grid, inner bars where allowed) and its D/C, then **ask** with the options: enlarge the section (size that passes), higher f'c,
  approve ρ 6–8 %, or accept the overload up to a D/C the designer states (Engineering judgment – ACI 318 needs φSn ≥ U). Only the
  designer's answer goes into Accept_overload (label, story, dc_max) → status ACCEPTED, lowest steel with D/C ≤ dc_max, reported on
  the calc page and the Summary. Never relax detailing. Accepted δ > 1.4: ask the same way → Accept_delta (label, story, delta_max).
- Sections changed by the designer (enlarged) are checked with the current ETABS forces – say so and ask for an ETABS update + rerun.
- Ranges on the wider grid (3–4-bar bundles, c/c ≤ 160)
  and the stories pulled onto it by the never-less-than-above rule → show and confirm (couplers, congestion).
  Inner bars used → show e/h of the governing combo and confirm the column is compression-dominated.
- Story ranges, mark envelopes and rotated members, section changes along the height, less steel below the f'c change,
  3/4-bar bundle runs longer than 12 m − Lst → show and confirm.
- δ > 1.4 (ACI 6.2.5.3) → engineer review; the fix is stiffness or shorter kLu, not more steel.
- f'c study → designer confirms the bottom f'c and the reduction story (column-stories failing at every f'c are listed separately).
- Column plan (plan_map): local axis angle 0 assumed unless Frame Assignments – Local Axes is exported; columns without points listed.

## 5. CEDA rules (method and clauses: `references/`)
- **Strength / φ**: กฎกระทรวง 2566 ข้อ 8 วรรคสอง (QC column) tied 0.70, spiral 0.75, flexure 0.90, shear 0.85; φ transition ACI 21.2.2;
  φPn,max 0.80/0.85 φPo; biaxial = 3D φ-surface, radial D/C (no Bresler).
- **Slenderness** non-sway: Pc without φ, Cm = 1, M2,min when slender, βd with 25 % LL sustained, k 1.0 / Lu from connectivity by default.
- **Loads** Rev.1: gravity from both full models; seismic above ground from the seismic model; basement P by ΔP of DL/SDL/LL, M/V the larger
  of carried-down and gravity; P sign kept.
- **Bars**: face ≤ 200 / 540 / 660 mm → 2 / 3 / 4 bars, else c/c 125–150 for singles and 2-bar bundles; smallest bar by long side
  DB12/16/20; 1 % pattern; lowest story up to DB32 then symmetric DB32 bundles – **start at the tie corners and complete each bundle size
  over the whole section before the next** (2 everywhere, then 3, then 4; CEDA 20 Oct 2026, bundles allowed at any position); when the
  125–150 grid cannot
  carry the load, a range may use a wider grid **c/c ≤ 160 mm with 3–4-bar bundles only** (CEDA 20 Oct 2026; clear spacing ACI 25.2.3 with
  db√n – DB32: 83 mm for 3, 96 mm for 4); going up bundles off first, then size; never less than the story above except below the f'c
  change (a story below a wider-grid range moves to that grid); ρ ≤ 6 % (6–8 % only approved).
  **Inner bars** (CEDA pattern, paattern.dxf 20 Oct 2026): one bar at each crossing of the inner hoops, added to the full perimeter –
  **last resort only**, after the perimeter (125–150 grid, then wider grid) cannot carry the load, and only for basement stories
  (compression-dominated – governing e/h reported) or label-stories approved for ρ > 6 % whose perimeter is full; not for circles.
- **Ties**: ACI 25.7.2.3 with the CEDA symmetric centre-out pattern; minimum = IMF (ประกาศ มท. 2564 ข้อ 26(1)) for every column;
  shear Vc without compression benefit; fyt shear DB12 4000 / DB16–32 ≤ 4200 ksc.
- **f'c**: one reduction for the project to the typical f'c (≥ 50 % of columns ρ ≤ 1.5 %, all above ρ ≤ 6 %); column-stories that
  fail with every f'c are left out of the study and listed (enlarge the section); ACI 15.5 check against the slab f'c.
- **Story ranges**: common rows; basement every story; above ground 2–3 stories / 12 m + Lst with early breaks; f'c change always a break;
  every range a row, no row limit.
- **Marks**: same label = same mark; same section (90° rotation included) in every row, same span; envelope = **criterion A**
  (CEDA 20 Oct 2026): each label may take ≤ 25 % extra longitudinal steel (weight = As × range height), the project ≤ 10 %, no limit
  on rows or ladder steps, never above ρ 6 % unless approved; ties = critical of the mark; names C1, C2 … by size. The added steel
  of the project is reported (Summary notes).
- **Lap**: Class B from the project lap table; laps where bundles ≤ 2 bars; **couplers for 3–4-bar bundles** (CEDA 20 Oct 2026) and
  ρ > 4 %; a lap inside a 3–4-bar bundle would need ×1.2/×1.33 (ACI 25.6.1.5).

## 6. Deliver (commit to the designer's folder, reply in Thai, short)
Criteria summary + checkpoint list; `<job>_Column_Decision.xlsx` (Summary with criteria, f'c study and notes; Decision label × story with
section, f'c, bars, ρ, D/C, governing combo, kLu/r, δ, shear, ties, status, recommendation; Schedule mark × range with Lst);
`<job>_Column_Calc.pdf` (one page per mark per range: CEDA header/footer, 3D surface, P–Mx, P–My, Mx–My) and `<job>_Column_Backup.xlsx`
(live formulas + engine D/C check), all marks and per mark in `marks/`; `<job>_Table_of_Column_DRAFT.pdf/.dxf` (layers G-ANNO-TEXT,
A-DETL-GENF, CED_0_10/13/18_Solid, S-DIMS; [CHECK] on G-ANNO-CHECK – freeze before issue) + `<job>_Column_Schedule_DRAFT.xlsx`
(bar coordinates for Revit); the input workbook used; a decisions log (every designer decision with its basis and date); column mapping
plan per story on request. Drafts only – not construction drawings. Detailed CEDA-style Excel per mark-range
on request (9-point X/Y diagrams, load sheet, XY_check with rotated NA).

## 7. Not covered (say so)
Sway frames (δs); SMF detailing (ACI 18.7), joint shear / Av; deformation compatibility (category ง, มยผ. 2.11.5 → ACI 318-14 18.14);
spiral φ not wired (circular treated as tied); L-shaped / bent wall-columns (VOCO C8, C11). On the first real project spot-check 2–3
columns (P, M, basement P) against ETABS by hand.

## Change log
- v1.3.6 (21 Oct 2026, Streamlit v3 inputs): input layer only, design rules unchanged (BKMPH02 rerun from the raw files identical,
  1,277 label-stories) – `route_models`: unreduced full model alone promoted to primary (ASSUMPTION), separate combination file
  merged per combo (no double factors); `read_lap_table` for CEDA TABLE 11.04; sheet Story_ranges + coverage check; CLI flags
  --combos / --lap-table / --lap-sheet; T14; fixtures lap_table_TABLE_11_04.xlsx, bkmph02_load_combination.xlsx.
- v1.3.5 (21 Oct 2026, package audit): paattern.dxf stored as a test fixture and read by the self-test (T10b); plan_map smoke test (T13);
  BKMPH02 regression record + decisions log in tests/; method.md §8 (status, overload asked every time, δ, sway, f'c study exclusion,
  ACI 15.5), project lap tables never carried over; references/tests README updated (T8 exception documented); config_template with
  slender.sway / accept_overload / accept_delta.
- v1.3.4 (21 Oct 2026): overload never accepted without asking – Accept_overload rows applied only with `--overload-confirmed`
  (else pending, exit 2; T12); `plan_map.py` column mapping plan (true-size sections, mark + label, PDF A1 + DXF); ETABS sheets pasted
  without their 'TABLE:' row read by sheet name (T12); inputs list incl. Point Object Connectivity; ask Lu of ramp / deep-beam columns.
- v1.3.3b (21 Oct 2026, BKMPH02 decisions): engineer-accepted overload (Accept_overload, status ACCEPTED) and δ (Accept_delta);
  ladder order – each bundle size completed over the section (tie corners first) before the next, non-corner bundles no longer an
  assumption (T1/T2/T8/T9 expected values updated, sources noted); couplers for 3–4-bar bundles; `slender.sway = non-sway` option;
  f'c study ignores column-stories that fail at every f'c; input workbook Sections with story_from/to now replace only those stories
  (was the whole label); ACI 15.5 note in story order; T11.
- v1.3.3 (20 Oct 2026): mark criterion A – per label ≤ 25 % / project ≤ 10 % extra steel, row and step limits removed (configurable),
  envelope blocked when it would exceed ρ 6 % without approval; BKMPH02 43 → 29 marks (+4.8 % steel).
- v1.3.2 (20 Oct 2026): inner bars at the inner-hoop crossings (grid key 'I' / 'WI') as the last step of the ladder for basement or
  approved-ρ columns – positions checked against paattern.dxf (T10); 2-bar bundles stacked inward / diagonal at corners confirmed by the
  same drawing; section cache keyed by grid.
- v1.3.1 (20 Oct 2026, BKMPH02 test): wider grid c/c ≤ 160 mm for 3–4-bar bundles (grid key 'W', own marks, note at the grid change);
  fixes – basement assembly skipped silently when the export has no Z (designer story order now used), βd re-read the forces per
  column-story (minutes → seconds), circular ties missing ncross, ladder of the wrong section used for ranges / bundle-run check when the
  section changes along the height; new T9. Open: f'c study should ignore columns that fail at every f'c.
- v1.3 (20 Oct 2026): package restructured – SKILL.md (no code) / scripts (engine, JSON in-out) / tests (expected.json with sources,
  fixtures, VOCO regression) / references (method, rules, loads, basis Rev.1, Excel review, lap sheet) / assets (input template, config
  template, logo); `prepare_inputs.py` + `input_workbook.py` (Excel input path, input check); self-test takes the skill path and reads
  `tests/expected.json`; new T7 (Excel input) and T8 (issued C1 bars D/C ≤ 1, S-04-01-01 R3). Engine rules unchanged from v1.2.
- v1.2 (19 Oct 2026): small-face bar count; singles that break clear spacing dropped; marks include ties; 90° rotation = same mark;
  envelope ≤ 2 rows / ≤ 1 step / ≤ 20 % with critical ties; note at section changes; less steel allowed below the f'c change;
  Lu asked per basement band; story order fallback; `--per-mark` outputs; VOCO regression vs issued drawing.
- v1.1 (19 Oct 2026): CEDA bottom-up bar method, 1 % pattern, common story ranges (no ≤ 8-row merge), bundle-run check.
- v1 (Oct 2026): first release from the VOCO C1 study (Rev.1 basis, c/c 125–150 grid, tie-corner ladder, symmetric ties, ρ 6/8 %, βd Rev.1,
  φ ข้อ 8, combo check ข้อ 7).
