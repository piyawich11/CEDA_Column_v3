# Method – strength, slenderness, shear, ties, f'c, lap (engine: design.py, colsurf.py)

Units in the engine: kg, cm, ksc; moments kg-m. Reports: t, t-m, ksc. Tags: **Code** / **Practice** / **Judgment** / **Assumption**.
Basis document: `Column_Design_Basis_Rev1.pdf` (11 Oct 2026); Excel review: `Column_Excel_Review_Rev0.pdf`.

## 1 Section strength (colsurf.py)
- Strain compatibility, εcu = 0.003, Es = 2.04×10⁶ ksc, Ec = 15,100√f'c (ACI 19.2.2.1, ksc form) – **Code**.
- Concrete: ACI rectangular block on a fibre grid (≥ 30 fibres per side), β1 = 0.85 − 0.05(f'c − 280)/70, 0.65 ≤ β1 ≤ 0.85 (ACI 22.2.2.4.3) – **Code**.
- Steel: elastic–perfectly plastic ±fy; bars at their true positions incl. bundle offsets (layout.bars_cm) – **Code / Practice**.
- Po = 0.85 f'c (Ag − Ast) + fy Ast (ACI 22.4.2.2); φPn,max = 0.80 φ Po tied, 0.85 φ Po spiral (ACI 22.4.2.1) – **Code**.
- φ (กฎกระทรวงกำหนดการออกแบบโครงสร้างอาคาร … พ.ศ. 2566 ข้อ 8 วรรคสอง, quality-controlled column): tied 0.70, spiral 0.75,
  flexure / tension 0.90, shear 0.85, bearing 0.70 – **Code**.
- φ transition: φ = φc + (0.90 − φc)(εt − εty)/0.003 between εty and εty + 0.003 (ACI 318-19 21.2.2; not in กฎกระทรวง) – **Code (ACI)**.

## 2 Biaxial check (colsurf.Section.surface / dc)
- Points (φPn, φMnx, φMny) for neutral-axis angle θ (72 values) × depth c (60 values, geometric + linear), axial capped at φPn,max,
  pure tension −φt fy Ast; convex hull of the points scaled by (φPn,max, φPn,max·h/4, φPn,max·b/4) – **Judgment** (agreed).
- D/C = radial distance origin → demand / origin → hull along the same ray; on the capped part D/C = max(uncapped, Pu/φPn,max).
  No Bresler – **Judgment**.

## 3 Slenderness – non-sway (design.magnified)
- Sway test: Q = ΣPu Δo / (Vus lc) per story and direction; Q > 0.05 → STOP (δs not automated) (ACI 6.6.4.3) – **Code**.
- r = 0.3 h (rect), 0.25 D (circle) (ACI 6.2.5.2); limit kLu/r ≤ 22 with M1/M2 = +1 – **Code / Practice**.
- (EI)eff = (0.2 Ec Ig + Es Ise)/(1 + βd), Ise from the true bar positions (ACI 6.6.4.4.4(a)) – **Code**.
- Pc = π²(EI)eff/(k Lu)², **without φ** (designer decision D3) – **Judgment**.
- δ = Cm / (1 − Pu / 0.75 Pc) ≥ 1, **Cm = 1 always** – **Practice**; δ > 1.4 reported (ACI 6.2.5.3).
- Mu = sign(M)·max(|M|, M2,min)·δ, M2,min = Pu (15 + 0.03 h) mm = Pu (1.5 + 0.03 h) cm, applied only when slender (ACI 6.6.4.5.4) – **Code**.
- βd = [1.4(DL + SDL) + 0.25·1.7 LL] / [1.4(DL + SDL) + 1.7 LL] per column-story from the load cases at the column bottom
  (25 % of LL sustained, conservative) – **Judgment (Rev.1)**; a single value from Criteria when the cases are not exported.
- Defaults: k = 1.0, Lu = column length from connectivity (conservative); per story / per column overrides – **Judgment**.

## 4 Shear (design.shear_check, design_shear)
- Each direction separately; Vc = 0.53 √f'c bw d, **no axial-compression increase**; tension: Vc × max(1 + Nu/(35 Ag), 0) – **Practice / Code**.
- Vs = Av fyt d / s ≤ 2.1 √f'c bw d; only legs running the full depth count; Av,min = max(0.2√f'c, 3.5) bw s / fyt when Vu > 0.5 φ Vc – **Code**.
- fyt for shear: DB12 4,000 ksc; DB16–DB32 ≤ 4,200 ksc (Ash uses the actual fyt) – **Practice**.
- IMF: Ve = lesser of 2 Mn/Lu (max Mn over the Pu range) and 2 × seismic-combo shear (มยผ. 5.2.7.2 / ACI 18.4.3.1, upper bound) – **Code / Judgment**.
- When shear fails: s → 150 mm, then full-depth crossties, then s 100 mm, otherwise DB16 ties / revise – **Practice**.

## 5 Minimum ties – IMF level for every column (design.imf_ties)
ประกาศกระทรวงมหาดไทย 2564 ข้อ 26(1) = มยผ. 1301/1302-61 5.2.7.4 – **Code**:
so ≤ min(8 db,min, 24 dt, c/2, 300 mm); lo ≥ max(Lu/6, c1, 500 mm); first tie ≤ so/2; outside lo s ≤ 2 so.
Joint Av ≥ 3.5 c1 s / fy (มยผ. 5.2.7.4.4) – not automated, remind. SMF (ACI 18.7) – not automated.

## 6 f'c study (design.choose_fc)
Standard f'c 210, 240, 280, 320, 400, 450, 500, 560, 600, 700 ksc (S-00-04-04). Bottom f'c = lowest value giving ρ ≤ 6 % for every column
of the lowest story; reduce **once** to the typical f'c at the lowest story where ≥ 50 % of the columns need ρ ≤ 1.5 % and every column
above works with ρ ≤ 6 %; otherwise move the reduction up – **Practice**. ACI 15.5 check when column f'c > 1.4 × slab f'c – **Code**.

## 7 Lap splices (design.lap_length, run.py)
Lst = Class B tension lap from the project table S-00-04-04 ("other bar") – **Practice**; never invented.
Each project has its own table – VOCO (S-00-04-04): 400 ksc DB25/28/32 = 1550/1875/2325, 560 ksc = 1325/1600/1975
(`S-00-04-04_lap_table.pdf`); BKMPH02 (TABLE 11.04, cover 40 mm, Lst "other bar"): 400 ksc = 1125/1350/1700, 600 ksc = 925/1125/1400.
Never carry a lap table from one project to another.
12 m stock: laps only where bundles ≤ 2 bars; 3–4-bar bundles are spliced with couplers (CEDA 21 Oct 2026); a lap inside a
3/4-bar bundle would need ×1.2 / ×1.33 (ACI 25.6.1.5) – **Code / Practice**.

## 8 Status and engineer decisions (design.choose_step, run._status, prepare_inputs)
- OK: D/C ≤ 1 and ρ ≤ 6 %. ASK_RHO: passes only with 6 % < ρ ≤ 8 % – needs approval (size restricted). REVISE: nothing fits.
- ACCEPTED: 1 < D/C ≤ dc_max that the designer stated for that label-story (Accept_overload) – **Judgment**, ACI 318 needs φSn ≥ U.
  Asked **every time** (CEDA 21 Oct 2026): rows are applied only with `prepare_inputs.py --overload-confirmed` after the designer
  confirmed them in the session; the lowest steel with D/C ≤ dc_max is used; reported on the calc page ("OVERLOAD ACCEPTED BY THE
  ENGINEER") and in the Summary notes.
- δ > 1.4 (ACI 6.2.5.3): reported; accepted only per label-story by the designer (Accept_delta, **Judgment**).
- Non-sway without Story Forces / Drifts: only when the designer says so (`slender.sway = non-sway`, **Judgment**, reported).
- f'c study: column-stories failing with every standard f'c are excluded from the study and listed (enlarge the section).
- ACI 15.5: column f'c > 1.4 × slab f'c → joint check flagged for the stories concerned (slab f'c asked at start).
