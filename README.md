# CEDA RC Column Design – Streamlit (v3)

Front end for the **ceda-column-design** skill. `engine/ceda-column-design/` is a verbatim copy of the skill folder
(SKILL.md, scripts, tests, references, assets). The app calls the skill scripts and never re-implements a design or input rule.
When the skill is updated: replace `engine/ceda-column-design/` with the new skill folder and run the tests.

## Run
```bash
pip install -r requirements.txt
python3 tests/test_app.py "<BKMPH02 folder>"     # must print ALL PASS (without the folder: A + B only)
streamlit run app.py
```

## 1. Upload – the BKMPH02 file set
| # | file | BKMPH02 | required |
|---|---|---|---|
| 1.1 | Seismic model (above ground, reduced stiffness) – ETABS export | `01 Seismic model.xlsx` | yes |
| 1.2 | Full model – Gravity / unreduced stiffness | `02 Full Gravity.xlsx` | yes (or 1.3) |
| 1.3 | Full model – reduced stiffness | – | optional |
| 1.4 | Load Combination Definitions (separate file) | `04 Load Combination.xlsx` | optional |
| 1.5 | CEDA development-length table (TABLE 11.04, sheet per cover) | `Development of Reinforcement Table.xlsx` | optional |
| 1.6 | CEDA input workbook | `BKMPH02_Column_Input_v136.xlsx` | optional |

Model routing (skill v1.3.6 `route_models`):
- 1.2 only → used as the primary full model (geometry, βd, basement ΔP, gravity combos) – **ASSUMPTION**, shown in the input check
  (Rev.1 uses the reduced-stiffness model).
- 1.2 + 1.3 → 1.3 reduced stiffness is the primary full model; gravity combos are enveloped with 1.2.
- 1.4 → used in every model, replaces the ETABS definition of the same combo names (no double factors).
- 1.5 → fills the Lap table when the input workbook has no Lap rows (Lst = Class B tension lap, other bar).

From each ETABS model export: Element Forces – Columns (combos + DL/SDL/LL for every story), Column Object Connectivity,
Point Object Connectivity, Frame Assignments – Section Properties, section definitions; seismic model also Story Forces / Drifts.

## 2. Inputs – on screen or Excel (both, not either)
Tabs = sheets of the input workbook: Project, Seismic, Materials & detailing (incl. sway), Stories / Lu / k / f'c, Columns (Lu per
column-story, e.g. ramp columns), Sections (per label-story), Load combinations + exclude, Lap table, Marks & story ranges
(criterion A + **Story_ranges**), ρ / δ (Approve_rho, Accept_delta), Overload (proposed Accept_overload rows).
"Save the inputs on screen as an input workbook" writes everything back to Excel; upload it next time.

## 3–5. Check → Run → Designer decisions
- Input check (✔/✖) incl. the model routing and the story-range coverage.
- **Overload (D/C > 1) is never applied without the designer** (CEDA 21 Oct 2026): after the run, section 5 lists every
  REVISE / ACCEPTED / proposed row with the D/C reached with the most steel that fits; tick each accepted row, give the D/C limit,
  "Confirm the ticked rows and run again". Unticked workbook rows stay pending (not applied, listed). New uploads clear every
  confirmation.
- ASK ρ 6–8 % and δ > 1.4 rows are listed; decide them in the ρ / δ tab and run again.

## 6. Outputs
Label → mark, Table of Column, interaction surface (mark + story range), DXF view, **column plan per story** (plan_map – PDF A1 +
DXF), downloads: Decision, **Decisions log**, calc PDF and back-up Excel (all and per mark), Table of Column PDF/DXF, schedule for
Revit, input workbook used, ZIP; detailed CEDA-style Excel per mark-range.

## Tests (`tests/test_app.py`)
- A skill self-test ALL PASS
- B routing (unreduced only / reduced + unreduced) and app pipeline == skill CLI on the synthetic 3-model set
- C BKMPH02: app == final BKMPH02 run (1,277 label-stories), confirmed rows only → ACCEPTED, the rest pending/REVISE,
  decisions log, column plan B2, workbook round trip incl. Story_ranges / Accept_*.
- `tests/ui/ui_bkmph02.py` – browser run with the BKMPH02 files (Playwright).

## Not covered (same as the skill)
Sway frames (δs), SMF detailing, joint shear, L-shaped columns, spiral φ. Outputs are drafts for engineer review.
