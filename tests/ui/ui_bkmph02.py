"""Browser test with the BKMPH02 file set:  streamlit run app.py --server.port 8599 &  python3 tests/ui/ui_bkmph02.py <BKMPH02> <shots>
Uploads the 5 files + the input workbook, runs, confirms ONE overload row on screen, reruns, opens every output tab."""
import sys, time, os
from playwright.sync_api import sync_playwright
D, O = sys.argv[1], sys.argv[2]
os.makedirs(O, exist_ok=True)
F = lambda n: os.path.join(D, n)
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={'width': 1700, 'height': 1300})
    pg.goto('http://localhost:8599'); pg.wait_for_selector('text=1. Upload', timeout=60000)
    fi = pg.locator('input[type=file]')
    for i, n in ((0, '01 Seismic model.xlsx'), (1, '02 Full Gravity.xlsx'), (3, '04 Load Combination.xlsx'),
                 (4, 'Development of Reinforcement Table.xlsx'), (5, 'BKMPH02_Column_Input_v136.xlsx')):
        fi.nth(i).set_input_files(F(n)); time.sleep(3)
    time.sleep(10)
    pg.wait_for_selector('[data-testid="stStatusWidget"]', state='detached', timeout=600000); time.sleep(3)
    pg.screenshot(path=f'{O}/1_inputs.png', full_page=True)
    print('assumption shown:', pg.locator('text=ASSUMPTION').count() > 0, '| missing:', pg.locator('text=✖ fill in').count())
    pg.get_by_text('I confirm the inputs').click(); time.sleep(2)
    pg.get_by_role('button', name='▶ Run design').click()
    pg.wait_for_selector('text=5. Designer decisions', timeout=1800000); time.sleep(4)
    pg.screenshot(path=f'{O}/2_after_run.png', full_page=True)
    print('REVISE metric after first run:', pg.locator('[data-testid="stMetric"]').nth(6).inner_text().replace('\n', ' '))
    # tick the first row of the overload table (canvas grid: click the first checkbox cell)
    grid = pg.locator('[data-testid="stDataFrame"]').filter(has=pg.locator('text=accept overload')).first
    grid.scroll_into_view_if_needed(); bb = grid.bounding_box()
    pg.mouse.click(bb['x'] + 30, bb['y'] + 55); time.sleep(1); pg.keyboard.press('Space'); time.sleep(2)
    pg.get_by_role('button', name='✔ Confirm the ticked rows and run again').click()
    time.sleep(15)
    pg.wait_for_selector('[data-testid="stStatusWidget"]', state='detached', timeout=1800000); time.sleep(5)
    pg.screenshot(path=f'{O}/3_after_confirm.png', full_page=True)
    print('ACCEPTED metric after confirm:', pg.locator('[data-testid="stMetric"]').nth(4).inner_text().replace('\n', ' '))
    for t in ['Label → Mark', 'Table of Column', 'Interaction surface', 'DXF', 'Column plan', 'Downloads', 'Decision (label × story)']:
        pg.get_by_role('tab', name=t).click(); time.sleep(12 if t in ('Interaction surface', 'DXF') else 2)
        if t == 'Column plan':
            pg.get_by_role('button', name='Make column plan').click(); time.sleep(40)
        pg.screenshot(path=f'{O}/t_{t.split()[0]}.png', full_page=False)
    print('exceptions:', pg.locator('[data-testid="stException"]').count())
    b.close()
