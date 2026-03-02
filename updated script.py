import os, time, random, logging, requests, json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, WebDriverException

# ---------- USER INPUT ----------
base_url = input("Enter website URL (e.g. https://login.example.com): ").strip()
if not base_url.startswith("http"): base_url = "https://" + base_url
username = input("Enter username: ").strip()
password = input("Enter password: ").strip()

# ---------- CONFIG ----------
BASE_DIR = "screenshots"
SUCCESS, FAILED, STEPS = [os.path.join(BASE_DIR, x) for x in ("success", "failed", "steps")]
for d in [SUCCESS, FAILED, STEPS]: os.makedirs(d, exist_ok=True)
logging.basicConfig(filename="module_test_log.txt", format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# ---------- DRIVER ----------
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
options.set_capability("goog:loggingPrefs", {"browser": "ALL"})
driver = webdriver.Chrome(service=Service(), options=options)
actions, results, step_counter = ActionChains(driver), [], 1

# ---------- UTILS ----------
def log(msg): print(msg); logging.info(msg)
def wait_page(): WebDriverWait(driver, 20).until(lambda d: driver.execute_script("return document.readyState") == "complete")
def hwait(a=1.5, b=3.5): time.sleep(random.uniform(a, b))
def scroll(el): driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el); hwait(.5,1)

def screenshot(name, folder=STEPS):
    global step_counter
    path = os.path.join(folder, f"{step_counter:03d}_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
    step_counter += 1
    try:
        driver.save_screenshot(path)
    except Exception as e:
        log(f"❌ Screenshot failed: {e}")
    return path

def clean_err(e): return e.msg.split("\n")[0] if isinstance(e, WebDriverException) else str(e)

# ---------- LOGIN ----------
def login():
    log("\U0001f510 Logging in..."); driver.get(base_url); wait_page()
    try:
        driver.find_element(By.ID, "txtuser").send_keys(username)
        driver.find_element(By.ID, "txtpass").send_keys(password)
    except:
        log("Default IDs not found, trying alternate fields...")
        user_field = driver.find_element(By.XPATH, "//input[@type='text' or @name='username']")
        pass_field = driver.find_element(By.XPATH, "//input[@type='password']")
        user_field.send_keys(username)
        pass_field.send_keys(password)
    try:
        driver.find_element(By.ID, "btnLogin").click()
    except:
        driver.find_element(By.XPATH, "//button[contains(.,'Login') or contains(@class,'btn')]").click()
    log("\u2705 Logged in."); screenshot("login_success"); hwait(2,4)

# ---------- MODULE DETECTION ----------
def get_modules():
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "LnkHeaderMasterMenu"))).click()
    screenshot("menu_opened")
    hwait(2,3)
    modules = driver.find_elements(By.CSS_SELECTOR, "div.icon-main")
    module_list = []
    for idx, m in enumerate(modules, 1):
        name = m.get_attribute("class")
        module_list.append((idx, m, name))
        print(f"{idx}. {name}")
    return module_list

# ---------- MODULE CLICK ----------
def click_module(module_el):
    driver.execute_script("arguments[0].click();", module_el)
    hwait(2,3)
    if "HR" in module_el.get_attribute("class"):
        log("HR Payroll selected. Following HR Payroll flow...")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "txtOperationalMonth"))).send_keys("01/05/2025")
        btn = driver.find_element(By.ID, "btnLogin")
        driver.execute_script("arguments[0].click();", btn)
        screenshot("hr_operational_button")
        wait_page()
    else:
        log("Generic module selected.")
        wait_page()
    screenshot("module_opened")

# ---------- SUBMODULE LINK COLLECTION ----------
def collect_all_links():
    log("\U0001f50d Collecting all nested submenu links...")
    visited, links = set(), []

    def recurse_menus(parent):
        try:
            items = parent.find_elements(By.XPATH, ".//a[@href]")
            for item in items:
                href = item.get_attribute("href")
                if href and href.startswith("http") and href not in visited:
                    visited.add(href)
                    links.append({"href": href})
            dropdowns = parent.find_elements(By.XPATH, ".//a[contains(@class,'dropdown-toggle')]")
            for dd in dropdowns:
                try:
                    scroll(dd)
                    driver.execute_script("arguments[0].click();", dd)
                    hwait(1,1.5)
                    submenu = dd.find_element(By.XPATH, "./following-sibling::ul")
                    recurse_menus(submenu)
                except: continue
        except: pass

    recurse_menus(driver.find_element(By.TAG_NAME, "body"))
    log(f"\u2705 Total collected links: {len(links)}")
    return links

# ---------- PERFORMANCE ----------
def analyze_perf(url):
    try:
        t = time.time()
        r = requests.get(url, timeout=15, allow_redirects=True)
        return {"status": r.status_code, "time": round(time.time() - t, 2), "redirects": len(r.history)}
    except: return {"status": "ERROR", "time": None, "redirects": None}

# ---------- VISIT LINKS ----------
def visit_links(links):
    for idx, link in enumerate(links, 1):
        url = link["href"]
        log(f"\u27a1\ufe0f [{idx}/{len(links)}] {url}")
        issues, page_error = [], False
        shot = os.path.join(SUCCESS, f"page_{idx}.png")
        try:
            t = time.time(); driver.get(url); wait_page(); load = time.time() - t
            if load > 5: issues.append(f"Slow load: {round(load,2)}s"); page_error = True
            try:
                driver.save_screenshot(shot)
            except Exception as e:
                log(f"❌ Screenshot failed: {e}")
            logs = driver.get_log("browser")
            if any(l["level"] == "SEVERE" for l in logs): issues.append("Console errors detected"); page_error = True
            if not driver.find_elements(By.TAG_NAME, "h1"): issues.append("Missing H1 heading"); page_error = True
            perf = analyze_perf(url)
            if perf["status"] != 200: issues.append(f"HTTP status {perf['status']}"); page_error = True
            if perf["redirects"] > 0: issues.append(f"Redirected {perf['redirects']} times"); page_error = True
            if page_error:
                os.replace(shot, os.path.join(FAILED, os.path.basename(shot)))
                shot = os.path.join(FAILED, os.path.basename(shot))
            results.append({"url": url, "issues": issues, "screenshot": shot, "load_time": load,
                            "visited_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "js_logs": logs})
        except Exception as e:
            err = clean_err(e)
            log(f"❌ Failed: {err}")
            shot_fail = os.path.join(FAILED, f"page_{idx}.png")
            try:
                driver.save_screenshot(shot_fail)
            except Exception as ee:
                log(f"❌ Screenshot skipped: {ee}")
            results.append({"url": url, "issues": [f"Visit failed: {err}"], "screenshot": shot_fail, "load_time": 0,
                            "visited_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "js_logs": []})
        hwait(2,4)

# ---------- MAIN ----------
if __name__ == "__main__":
    try:
        login()
        modules = get_modules()
        choice = int(input("Enter module number to test: ").strip())
        module_el = modules[choice - 1][1]
        click_module(module_el)
        links = collect_all_links()
        visit_links(links)
        with open("results.json", "w", encoding="utf-8") as f: json.dump(results, f, indent=2)
        log(f"\ud83d\udcc4 Results saved to results.json ({len(results)} pages)")
    except Exception as e:
        log(f"❌ Script error: {clean_err(e)}")
    finally:
        driver.quit()
        log("\U0001f6d1 Browser closed.")
