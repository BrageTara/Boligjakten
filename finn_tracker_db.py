"""
Finn-tracker med SQLite-lagring — grunnlag for fremtidig nettside.
Scraping-logikk importeres fra scraper.py.
"""

import sqlite3
import re
import os
from datetime import date, datetime
from playwright.sync_api import sync_playwright
from scraper import fetch_all_listings, scrape_ad, check_sold_status

DB_FILE = "finn_tracker.db"


# ─── Database-oppsett ─────────────────────────────────────────────────────────

def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS annonser (
            finnkode        TEXT PRIMARY KEY,
            adresse         TEXT,
            prisantydning   INTEGER,
            fellesgjeld     INTEGER,
            totalpris       INTEGER,
            kvm_pris        INTEGER,
            felleskost      INTEGER,
            fellesformue    INTEGER,
            type            TEXT,
            bra             TEXT,
            rom             TEXT,
            etasje          TEXT,
            forste_sett     DATE,
            siste_sett      DATE,
            dager_ute       INTEGER,
            antall_visninger INTEGER DEFAULT 0,
            pris_ved_start  INTEGER,
            prisendring     INTEGER,
            status          TEXT DEFAULT 'Aktiv',
            url             TEXT,
            megler          TEXT,
            meglerkontor    TEXT,
            neste_visning   TEXT,
            flagg           TEXT,
            omrade          TEXT,
            postnummer      TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS prishistorikk (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            finnkode      TEXT,
            dato          DATE,
            prisantydning INTEGER,
            totalpris     INTEGER
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS solgte (
            finnkode        TEXT,
            adresse         TEXT,
            prisantydning   INTEGER,
            fellesgjeld     INTEGER,
            totalpris       INTEGER,
            kvm_pris        INTEGER,
            felleskost      INTEGER,
            fellesformue    INTEGER,
            type            TEXT,
            bra             TEXT,
            rom             TEXT,
            etasje          TEXT,
            forste_sett     DATE,
            siste_sett      DATE,
            dager_ute       INTEGER,
            antall_visninger INTEGER,
            pris_ved_start  INTEGER,
            prisendring     INTEGER,
            status          TEXT,
            url             TEXT,
            megler          TEXT,
            meglerkontor    TEXT,
            neste_visning   TEXT,
            flagg           TEXT,
            omrade          TEXT,
            postnummer      TEXT,
            solgt_dato      DATE,
            arsak           TEXT
        )
    """)

    conn.commit()
    conn.close()


# ─── Lese/skrive data ─────────────────────────────────────────────────────────

def load_existing(conn):
    """Returner dict med eksisterende annonser: {finnkode: row}."""
    c = conn.cursor()
    c.execute("SELECT * FROM annonser")
    return {row["finnkode"]: dict(row) for row in c.fetchall()}


def upsert_listing(conn, finnkode, ad, today, existing=None):
    """Sett inn ny eller oppdater eksisterende annonse."""
    forste_sett = today
    pris_ved_start = ad.get("prisantydning")
    antall_visninger = 0

    if existing:
        forste_sett = existing.get("forste_sett") or today
        if isinstance(forste_sett, str):
            forste_sett = date.fromisoformat(forste_sett)
        pris_ved_start = existing.get("pris_ved_start") or ad.get("prisantydning")
        antall_visninger = existing.get("antall_visninger") or 0
        forrige_visning = existing.get("neste_visning")
        ny_visning = ad.get("neste_visning")
        if ny_visning and ny_visning != forrige_visning:
            antall_visninger += 1

    if isinstance(forste_sett, datetime):
        forste_sett = forste_sett.date()
    dager = (today - forste_sett).days if isinstance(forste_sett, date) else 0

    prisendring = None
    if pris_ved_start and ad.get("prisantydning"):
        prisendring = ad["prisantydning"] - pris_ved_start

    kvm_pris = None
    bra_str = ad.get("bra")
    if bra_str and ad.get("prisantydning"):
        import re as _re
        bra_match = _re.search(r"(\d+)", str(bra_str))
        if bra_match:
            bra_num = int(bra_match.group(1))
            if bra_num > 0:
                kvm_pris = round(ad["prisantydning"] / bra_num)

    flagg = []
    if prisendring and prisendring < 0:
        flagg.append("Prisnedsatt")
    if dager >= 14:
        flagg.append("14+ dager")
    if antall_visninger >= 2:
        flagg.append("2+ visninger")
    if ad.get("totalpris") and ad.get("fellesgjeld") and ad["fellesgjeld"] / ad["totalpris"] >= 0.30:
        flagg.append("Høy fellesgjeld")

    c = conn.cursor()
    c.execute("""
        INSERT INTO annonser (
            finnkode, adresse, prisantydning, fellesgjeld, totalpris, kvm_pris,
            felleskost, fellesformue, type, bra, rom, etasje,
            forste_sett, siste_sett, dager_ute, antall_visninger,
            pris_ved_start, prisendring, status, url,
            megler, meglerkontor, neste_visning, flagg, omrade, postnummer
        ) VALUES (
            :finnkode, :adresse, :prisantydning, :fellesgjeld, :totalpris, :kvm_pris,
            :felleskost, :fellesformue, :type, :bra, :rom, :etasje,
            :forste_sett, :siste_sett, :dager_ute, :antall_visninger,
            :pris_ved_start, :prisendring, :status, :url,
            :megler, :meglerkontor, :neste_visning, :flagg, :omrade, :postnummer
        )
        ON CONFLICT(finnkode) DO UPDATE SET
            adresse         = excluded.adresse,
            prisantydning   = excluded.prisantydning,
            fellesgjeld     = excluded.fellesgjeld,
            totalpris       = excluded.totalpris,
            kvm_pris        = excluded.kvm_pris,
            felleskost      = excluded.felleskost,
            fellesformue    = excluded.fellesformue,
            type            = excluded.type,
            bra             = excluded.bra,
            rom             = excluded.rom,
            etasje          = excluded.etasje,
            siste_sett      = excluded.siste_sett,
            dager_ute       = excluded.dager_ute,
            antall_visninger = excluded.antall_visninger,
            prisendring     = excluded.prisendring,
            status          = excluded.status,
            megler          = excluded.megler,
            meglerkontor    = excluded.meglerkontor,
            neste_visning   = excluded.neste_visning,
            flagg           = excluded.flagg,
            omrade          = excluded.omrade,
            postnummer      = excluded.postnummer
    """, {
        "finnkode":         finnkode,
        "adresse":          ad.get("adresse"),
        "prisantydning":    ad.get("prisantydning"),
        "fellesgjeld":      ad.get("fellesgjeld"),
        "totalpris":        ad.get("totalpris"),
        "kvm_pris":         kvm_pris,
        "felleskost":       ad.get("felleskost"),
        "fellesformue":     ad.get("fellesformue"),
        "type":             ad.get("type"),
        "bra":              ad.get("bra"),
        "rom":              ad.get("rom"),
        "etasje":           ad.get("etasje"),
        "forste_sett":      str(forste_sett),
        "siste_sett":       str(today),
        "dager_ute":        dager,
        "antall_visninger": antall_visninger,
        "pris_ved_start":   pris_ved_start,
        "prisendring":      prisendring,
        "status":           "Aktiv",
        "url":              f"https://www.finn.no/realestate/homes/ad.html?finnkode={finnkode}",
        "megler":           ad.get("megler"),
        "meglerkontor":     ad.get("meglerkontor"),
        "neste_visning":    ad.get("neste_visning"),
        "flagg":            " | ".join(flagg) if flagg else None,
        "omrade":           ad.get("omrade"),
        "postnummer":       ad.get("postnummer"),
    })


def log_price_history(conn, finnkode, today, prisantydning, totalpris):
    c = conn.cursor()
    c.execute(
        "INSERT INTO prishistorikk (finnkode, dato, prisantydning, totalpris) VALUES (?, ?, ?, ?)",
        (finnkode, str(today), prisantydning, totalpris)
    )


def mark_sold(conn, finnkode, today, arsak):
    c = conn.cursor()
    c.execute("SELECT * FROM annonser WHERE finnkode = ?", (finnkode,))
    row = c.fetchone()
    if not row:
        return
    row = dict(row)
    c.execute("""
        INSERT INTO solgte (
            finnkode, adresse, prisantydning, fellesgjeld, totalpris, kvm_pris,
            felleskost, fellesformue, type, bra, rom, etasje,
            forste_sett, siste_sett, dager_ute, antall_visninger,
            pris_ved_start, prisendring, status, url,
            megler, meglerkontor, neste_visning, flagg, omrade, postnummer,
            solgt_dato, arsak
        ) VALUES (
            :finnkode, :adresse, :prisantydning, :fellesgjeld, :totalpris, :kvm_pris,
            :felleskost, :fellesformue, :type, :bra, :rom, :etasje,
            :forste_sett, :siste_sett, :dager_ute, :antall_visninger,
            :pris_ved_start, :prisendring, :status, :url,
            :megler, :meglerkontor, :neste_visning, :flagg, :omrade, :postnummer,
            :solgt_dato, :arsak
        )
    """, {**row, "solgt_dato": str(today), "arsak": arsak})

    c.execute(
        "UPDATE annonser SET status = ? WHERE finnkode = ?",
        (arsak, finnkode)
    )


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    today = date.today()
    print(f"\n=== Finn-tracker (DB) kjøres {today} ===\n")

    init_db()
    conn = get_conn()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        pg = context.new_page()

        print("Henter søkeresultater fra Finn.no...")
        try:
            listings = fetch_all_listings(pg)
        except Exception as e:
            print(f"FEIL ved henting av søkeside: {e}")
            browser.close()
            conn.close()
            return

        print(f"  Fant {len(listings)} annonser i søket.\n")

        existing = load_existing(conn)
        found_codes = {l["finnkode"] for l in listings}
        new_count = 0
        updated_count = 0

        try:
            for i, listing in enumerate(listings, 1):
                finnkode = listing["finnkode"]
                url = listing["url"]
                print(f"  [{i}/{len(listings)}] Henter {finnkode}...", end=" ", flush=True)
                ad = scrape_ad(pg, url)
                if not ad:
                    print("ingen data, hopper over.")
                    continue

                is_new = finnkode not in existing
                status = "ny" if is_new else "oppdaterer"
                print(f"{status}  |  {ad.get('adresse', '')}  |  postnr={ad.get('postnummer')}  område={ad.get('omrade')}")

                upsert_listing(conn, finnkode, ad, today, existing.get(finnkode))
                log_price_history(conn, finnkode, today, ad.get("prisantydning"), ad.get("totalpris"))
                conn.commit()

                if is_new:
                    new_count += 1
                else:
                    updated_count += 1

            # Sjekk om noen eksisterende annonser er borte fra søket
            sold_count = 0
            for finnkode, info in existing.items():
                if finnkode not in found_codes and info.get("status") in ("Aktiv", "Ukjent"):
                    ad_url = f"https://www.finn.no/realestate/homes/ad.html?finnkode={finnkode}"
                    arsak = check_sold_status(pg, ad_url)
                    mark_sold(conn, finnkode, today, arsak)
                    conn.commit()
                    print(f"  {finnkode} ikke lenger i søk — status: {arsak}")
                    sold_count += 1

        finally:
            browser.close()
            conn.close()
            print(f"\n=== Ferdig ===")
            print(f"  Nye annonser:     {new_count}")
            print(f"  Oppdaterte:       {updated_count}")
            print(f"  Solgt/trukket:    {sold_count}")
            print(f"  Lagret til:       {DB_FILE}\n")


if __name__ == "__main__":
    main()
