# PSEUDOCODE:
# 1. Import the Flask app
# 2. Configure it for testing (no real DB needed for route tests)
# 3. Provide a test client fixture used by all route tests
# 4. Provide a temp-DB fixture that creates an in-memory SQLite DB
#    with the same schema as finn_tracker.db, populated with sample rows

import sqlite3
import pytest
from app import create_app


@pytest.fixture
def app():
    app = create_app({"TESTING": True, "DB_PATH": ":memory:"})
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def seeded_app(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE annonser (
            finnkode TEXT PRIMARY KEY,
            adresse TEXT, prisantydning INTEGER, fellesgjeld INTEGER,
            totalpris INTEGER, kvm_pris INTEGER, felleskost INTEGER,
            fellesformue INTEGER, type TEXT, bra TEXT, rom TEXT,
            etasje TEXT, forste_sett DATE, siste_sett DATE,
            dager_ute INTEGER, antall_visninger INTEGER DEFAULT 0,
            pris_ved_start INTEGER, prisendring INTEGER,
            status TEXT DEFAULT 'Aktiv', url TEXT, megler TEXT,
            meglerkontor TEXT, neste_visning TEXT, flagg TEXT,
            omrade TEXT, postnummer TEXT
        );
        CREATE TABLE prishistorikk (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            finnkode TEXT, dato DATE,
            prisantydning INTEGER, totalpris INTEGER
        );
        CREATE TABLE solgte (
            finnkode TEXT, adresse TEXT, prisantydning INTEGER,
            fellesgjeld INTEGER, totalpris INTEGER, kvm_pris INTEGER,
            felleskost INTEGER, fellesformue INTEGER, type TEXT,
            bra TEXT, rom TEXT, etasje TEXT, forste_sett DATE,
            siste_sett DATE, dager_ute INTEGER, antall_visninger INTEGER,
            pris_ved_start INTEGER, prisendring INTEGER, status TEXT,
            url TEXT, megler TEXT, meglerkontor TEXT, neste_visning TEXT,
            flagg TEXT, omrade TEXT, postnummer TEXT,
            solgt_dato DATE, arsak TEXT
        );
        INSERT INTO annonser VALUES
            ('111','Møllenberggata 12',2990000,NULL,2990000,55370,3200,NULL,
             'Leilighet','54','2','2. etasje','2026-04-10','2026-04-21',
             11,0,3200000,-210000,'Aktiv',
             'https://finn.no/realestate/homes/ad.html?finnkode=111',
             'Ole Hansen','DNB Eiendom',NULL,'Prisnedsatt','Møllenberg','7043'),
            ('222','Elgesetergate 24',3450000,NULL,3450000,56557,NULL,NULL,
             'Leilighet','61','3','1. etasje','2026-04-01','2026-04-21',
             20,2,3450000,0,'Aktiv',
             'https://finn.no/realestate/homes/ad.html?finnkode=222',
             NULL,NULL,NULL,'14+ dager | 2+ visninger','Elgeseter','7030'),
            ('333','Nardovegen 8',2650000,1200000,3850000,69737,4500,NULL,
             'Leilighet','38','1','3. etasje','2026-04-18','2026-04-21',
             3,0,2650000,0,'Aktiv',
             'https://finn.no/realestate/homes/ad.html?finnkode=333',
             NULL,NULL,NULL,'Høy fellesgjeld','Nardo','7023');
        INSERT INTO prishistorikk VALUES
            (1,'111','2026-04-10',3200000,3200000),
            (2,'111','2026-04-21',2990000,2990000);
        INSERT INTO solgte VALUES
            ('999','Rosenborg allé 5',3100000,NULL,3100000,64583,NULL,NULL,
             'Leilighet','48','2','1. etasje','2026-04-05','2026-04-19',
             14,1,3100000,0,'Solgt',
             'https://finn.no/realestate/homes/ad.html?finnkode=999',
             NULL,NULL,NULL,NULL,'Rosenborg','7037',
             '2026-04-20','Solgt');
        CREATE TABLE omrade_stats (
            omrade TEXT PRIMARY KEY,
            antall_aktive INTEGER DEFAULT 0,
            antall_solgte INTEGER DEFAULT 0,
            snitt_kvm_pris INTEGER,
            min_kvm_pris INTEGER,
            max_kvm_pris INTEGER,
            histogram_json TEXT,
            oppdatert DATE
        );
    """)
    conn.commit()
    conn.close()
    app = create_app({"TESTING": True, "DB_PATH": db_path})
    yield app


@pytest.fixture
def seeded_client(seeded_app):
    return seeded_app.test_client()
