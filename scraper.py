"""
Felles scraping-logikk for finn_tracker.py (Excel) og finn_tracker_db.py (SQLite).
"""

import time
import re
import json

SEARCH_URL = (
    "https://www.finn.no/realestate/homes/search.html"
    "?location=1.20016.20318&is_new_property=false"
    "&sort=PUBLISHED_DESC"
)

SEARCH_DELAY = 3
AD_DELAY     = 2

POSTNUMMER = {
    # Sentrum / indre by
    "7010": "Midtbyen",       "7011": "Midtbyen",       "7012": "Singsaker",
    "7013": "Øya",            "7014": "Midtbyen",       "7015": "Tempe",
    "7016": "Midtbyen",       "7017": "Midtbyen",       "7018": "Ila",
    "7019": "Midtbyen",       "7020": "Trondheim",      "7021": "Byåsen",
    "7022": "Byåsen",         "7023": "Nardo",          "7024": "Stavne",
    "7025": "Brundalen",      "7026": "Trondheim",      "7027": "Lademoen",
    "7028": "Bromstad",       "7029": "Trondheim",      "7030": "Elgeseter",
    "7031": "Elgeseter",      "7032": "Trondheim",      "7033": "Risvollan",
    "7034": "Moholt",         "7035": "Trondheim",      "7036": "Trondheim",
    "7037": "Rosenborg",      "7038": "Trondheim",      "7039": "Trondheim",
    "7040": "Trondheim",      "7041": "Nedre Lade",     "7042": "Øvre Lade",
    "7043": "Møllenberg",     "7044": "Nedre Elvehavn", "7045": "Trolla",
    "7046": "Trondheim",      "7047": "Trondheim",      "7048": "Strindheim",
    "7049": "Vikåsen",        "7050": "Trondheim",      "7051": "Charlottenlund",
    "7052": "Trondheim",
    # Øst / Ranheim
    "7053": "Ranheim",        "7054": "Ranheim",        "7055": "Ranheim",
    "7056": "Ranheim",        "7057": "Jonsvatnet",     "7058": "Jakobsli",
    "7059": "Jakobsli",
    # Klæbu (del av Trondheim kommune fra 2020)
    "7060": "Klæbu",          "7066": "Trondheim",      "7067": "Trondheim",
    "7068": "Trondheim",      "7069": "Trondheim",
    # Sør / Heimdal / Tiller
    "7070": "Bosberg",        "7071": "Trondheim",      "7072": "Heimdal",
    "7074": "Spongdal",       "7075": "Tiller",         "7078": "Saupstad",
    "7079": "Flatåsen",       "7080": "Heimdal",        "7081": "Sjetnemarka",
    "7082": "Kattem",         "7083": "Leinstrand",     "7088": "Heimdal",
    "7089": "Heimdal",        "7091": "Tiller",         "7092": "Tiller",
    "7093": "Tiller",         "7097": "Saupstad",       "7098": "Saupstad",
    "7099": "Flatåsen",
    # Klæbu tettsted
    "7540": "Klæbu",          "7541": "Klæbu",          "7548": "Tanem",
    "7549": "Tanem",
}


def accept_cookies(page):
    """Godta cookie-dialogen hvis den dukker opp."""
    try:
        btn = page.query_selector('button:has-text("Godta alle")')
        if btn:
            btn.click()
            time.sleep(1)
    except Exception:
        pass


def fetch_all_listings(page):
    """Henter alle finnkoder fra søkeresultatsidene med Playwright."""
    all_listings = []
    seen = set()
    page_num = 1

    while True:
        url = SEARCH_URL if page_num == 1 else f"{SEARCH_URL}&page={page_num}"
        print(f"  Henter søkeside {page_num}...")

        for attempt in range(3):
            try:
                page.goto(url, wait_until="domcontentloaded")
                time.sleep(1)
                accept_cookies(page)
                page.wait_for_selector("article", timeout=10000)
                break
            except Exception as e:
                err = str(e)
                if "Timeout" in err:
                    print(f"  Side {page_num} har ingen annonser — ferdig med søk.")
                    print(f"  Totalt hentet {page_num - 1} søkesider.")
                    return all_listings
                elif attempt < 2:
                    print(f"    Nettverksfeil, prøver igjen om 10s...")
                    time.sleep(10)
                else:
                    raise

        links = page.eval_on_selector_all(
            'article a[href*="/realestate/"]',
            """elements => elements.map(el => el.href).filter(h => h.includes('/ad.html'))"""
        )

        batch = []
        for href in links:
            m = re.search(r"finnkode=(\d+)", href)
            if not m:
                m = re.search(r"/(\d+)(?:\?|$)", href)
            if m:
                finnkode = m.group(1)
                if finnkode not in seen:
                    seen.add(finnkode)
                    batch.append({"finnkode": finnkode, "url": href})

        if not batch:
            print(f"  Ingen nye annonser på side {page_num} — ferdig med søk.")
            break

        all_listings.extend(batch)
        page_num += 1
        time.sleep(SEARCH_DELAY)

    print(f"  Totalt hentet {page_num - 1} søkesider.")
    return all_listings


def scrape_ad(page, url):
    """Scraper en enkelt annonse med Playwright."""
    try:
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_selector("h1", timeout=15000)
        time.sleep(1)
    except Exception:
        return {}

    data = {}
    html = page.content()

    def find_val(label_text):
        try:
            for dt in page.query_selector_all("dt"):
                if label_text.lower() in dt.inner_text().lower():
                    dd = dt.evaluate("el => el.nextElementSibling?.textContent?.trim()")
                    if dd:
                        return dd
            for th in page.query_selector_all("th"):
                if label_text.lower() in th.inner_text().lower():
                    td = th.evaluate("el => el.nextElementSibling?.textContent?.trim()")
                    if td:
                        return td
        except Exception:
            pass
        return None

    def parse_kr(text):
        if not text:
            return None
        digits = re.sub(r"[^\d]", "", text)
        return int(digits) if digits else None

    try:
        h1 = page.query_selector("h1")
        data["adresse"] = h1.inner_text().strip() if h1 else None
    except Exception:
        data["adresse"] = None

    try:
        price_el = page.query_selector('[data-testid="pricing-incicative-price"]')
        if price_el:
            spans = price_el.query_selector_all("span")
            data["prisantydning"] = parse_kr(spans[1].inner_text()) if len(spans) >= 2 else None
        else:
            data["prisantydning"] = None
    except Exception:
        data["prisantydning"] = None

    data["fellesgjeld"]   = parse_kr(find_val("Fellesgjeld"))
    data["felleskost"]    = parse_kr(find_val("Felleskost"))
    data["fellesformue"]  = parse_kr(find_val("Fellesformue"))
    data["type"]          = find_val("Boligtype")
    data["bra"]           = find_val("Internt bruksareal") or find_val("Bruksareal") or find_val("Primærrom")
    data["rom"]           = find_val("Soverom")
    data["etasje"]        = find_val("Etasje")

    totalpris_raw = parse_kr(find_val("Totalpris"))
    if totalpris_raw:
        data["totalpris"] = totalpris_raw
    elif data["prisantydning"] and data["fellesgjeld"]:
        data["totalpris"] = data["prisantydning"] + data["fellesgjeld"]
    elif data["prisantydning"]:
        data["totalpris"] = data["prisantydning"]
    else:
        data["totalpris"] = None

    data["megler"] = None
    data["meglerkontor"] = None
    m_org = re.search(r'"orgName"\s*:\s*"([^"]+)"', html)
    m_name = re.search(r'"name"\s*:\s*"([^"]+)"', html)
    if m_org:
        data["meglerkontor"] = m_org.group(1)
    if m_name:
        data["megler"] = m_name.group(1)

    # Postnummer
    pnr = None
    pnr_raw = find_val("Postnummer") or find_val("postnummer")
    if pnr_raw:
        m = re.search(r"\b(\d{4})\b", pnr_raw)
        if m:
            pnr = m.group(1)

    if not pnr:
        for field in ("postCode", "zipCode", "zip_code", "postal_code",
                      "postalCode", "postcode", "zip"):
            m = re.search(rf'"{field}"\s*:\s*"?(\d{{4}})"?', html)
            if m:
                pnr = m.group(1)
                break

    if not pnr:
        m = re.search(r"\b(\d{4})\s+[A-ZÆØÅ]{2,}", html)
        if m:
            pnr = m.group(1)

    if not pnr:
        m = re.search(r"\b(\d{4})\s+[A-ZÆØÅ][a-zA-ZæøåÆØÅ]+", html)
        if m:
            pnr = m.group(1)

    if pnr and not (1000 <= int(pnr) <= 9999):
        pnr = None

    data["postnummer"] = pnr
    data["omrade"] = POSTNUMMER.get(pnr, f"Ukjent ({pnr})") if pnr else None

    data["neste_visning"] = None
    try:
        viewing_el = page.query_selector('[data-testid^="viewings-"]')
        if viewing_el:
            date_el = viewing_el.query_selector(".capitalize-first")
            time_el = viewing_el.query_selector("[class*='font-bold']")
            if date_el and time_el:
                dato = date_el.inner_text().strip()
                tid = re.sub(r"\s+", " ", time_el.inner_text()).strip()
                data["neste_visning"] = f"{dato} {tid}"
    except Exception:
        pass

    return data


def _parse_stream_sold_state(html_text):
    marker = "streamController.enqueue("
    idx = html_text.find(marker)
    if idx < 0:
        return None
    content_start = idx + len(marker)
    raw_str = html_text[content_start:]
    end_idx = raw_str.find(");</script>")
    if end_idx < 0:
        return None
    js_literal = raw_str[:end_idx]
    try:
        inner = json.loads(js_literal)
        arr = json.loads(inner)
    except Exception:
        return None

    try:
        sold_key_idx = arr.index("realEstateSoldState")
    except ValueError:
        return None

    sold_key_str = f"_{sold_key_idx}"
    for item in arr:
        if isinstance(item, dict) and sold_key_str in item:
            val = item[sold_key_str]
            if isinstance(val, int):
                return val >= 0
    return None


def check_sold_status(page, url):
    """Besøker annonsesiden og returnerer årsaken til at den er borte fra søk."""
    try:
        resp = page.goto(url, wait_until="domcontentloaded")
    except Exception:
        return "Ukjent"

    time.sleep(1)
    html = page.content()
    text_lower = html.lower()

    if resp and resp.status == 404:
        return "Trukket"
    if "siden finnes ikke" in text_lower or "page not found" in text_lower:
        return "Trukket"
    if "annonsen er ikke lenger tilgjengelig" in text_lower or "ikke lenger aktiv" in text_lower:
        return "Trukket"

    stream_result = _parse_stream_sold_state(html)
    if stream_result is True:
        return "Solgt"
    if stream_result is False:
        return "Trukket"

    if ("boligen er solgt" in text_lower or ">solgt<" in text_lower
            or '"sold":true' in html or '"isSold":true' in html):
        return "Solgt"

    return "Ukjent"
