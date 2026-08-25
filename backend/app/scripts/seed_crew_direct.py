"""Seed test crew directly into SQLite."""
import sqlite3, uuid
from datetime import date, timedelta

DB = "/home/shawn/projects/pararig-ops/backend/pararig_ops.db"
ORG_ID = "63ff4eec-3c0e-44d0-b140-4e11d89611f1"
TODAY = date.today()

crew = [
    # (id, org, first, last, email, role, license_type, license_num, lic_country, lic_exp, med_class, med_exp, passport, passport_exp, base, status, doh, last_prof, last_90d, last_12m)
    # BT-67 crew
    (str(uuid.uuid4()), ORG_ID, "Marcus", "Reeves", "marcus@pararig.com", "captain", "atpl", "MR-CPT-0001", "US", str(TODAY+timedelta(days=730)), "class_1", str(TODAY+timedelta(days=180)), "P123456", str(TODAY+timedelta(days=1095)), "MYNN", "active", str(TODAY-timedelta(days=730)), str(TODAY-timedelta(days=30)), 120.0, 480.0),
    (str(uuid.uuid4()), ORG_ID, "Diego", "Vasquez", "diego@pararig.com", "captain", "atpl", "DV-CPT-0002", "US", str(TODAY+timedelta(days=730)), "class_1", str(TODAY+timedelta(days=200)), "P234567", str(TODAY+timedelta(days=1095)), "MYNN", "active", str(TODAY-timedelta(days=700)), str(TODAY-timedelta(days=45)), 95.0, 420.0),
    (str(uuid.uuid4()), ORG_ID, "Andre", "Fontaine", "andre@pararig.com", "first_officer", "cpl", "AF-FO-0003", "US", str(TODAY+timedelta(days=365)), "class_1", str(TODAY+timedelta(days=150)), "P345678", str(TODAY+timedelta(days=730)), "MYNN", "active", str(TODAY-timedelta(days=500)), str(TODAY-timedelta(days=20)), 85.0, 350.0),
    # King Air 350 crew
    (str(uuid.uuid4()), ORG_ID, "Sarah", "Chen", "sarah@pararig.com", "captain", "atpl", "SC-CPT-0004", "US", str(TODAY+timedelta(days=730)), "class_1", str(TODAY+timedelta(days=190)), "P456789", str(TODAY+timedelta(days=1095)), "MYNN", "active", str(TODAY-timedelta(days=720)), str(TODAY-timedelta(days=15)), 130.0, 510.0),
    (str(uuid.uuid4()), ORG_ID, "James", "Okonkwo", "james@pararig.com", "captain", "atpl", "JO-CPT-0005", "US", str(TODAY+timedelta(days=365)), "class_1", str(TODAY+timedelta(days=210)), "P567890", str(TODAY+timedelta(days=1095)), "MYNN", "active", str(TODAY-timedelta(days=690)), str(TODAY-timedelta(days=10)), 110.0, 460.0),
    (str(uuid.uuid4()), ORG_ID, "Elena", "Rossi", "elena@pararig.com", "first_officer", "cpl", "ER-FO-0006", "US", str(TODAY+timedelta(days=365)), "class_1", str(TODAY+timedelta(days=140)), "P678901", str(TODAY+timedelta(days=730)), "MYNN", "active", str(TODAY-timedelta(days=480)), str(TODAY-timedelta(days=25)), 75.0, 310.0),
    # King Air 200 crew
    (str(uuid.uuid4()), ORG_ID, "Tom", "Brennan", "tom@pararig.com", "captain", "atpl", "TB-CPT-0007", "US", str(TODAY+timedelta(days=730)), "class_1", str(TODAY+timedelta(days=170)), "P789012", str(TODAY+timedelta(days=1095)), "MYNN", "active", str(TODAY-timedelta(days=710)), str(TODAY-timedelta(days=35)), 105.0, 440.0),
    (str(uuid.uuid4()), ORG_ID, "Kofi", "Adjei", "kofi@pararig.com", "first_officer", "cpl", "KA-FO-0008", "US", str(TODAY+timedelta(days=365)), "class_1", str(TODAY+timedelta(days=160)), "P890123", str(TODAY+timedelta(days=730)), "MYNN", "active", str(TODAY-timedelta(days=450)), str(TODAY-timedelta(days=5)), 65.0, 280.0),
    # Caravan crew
    (str(uuid.uuid4()), ORG_ID, "Luis", "Martinez", "luis@pararig.com", "captain", "atpl", "LM-CPT-0009", "US", str(TODAY+timedelta(days=730)), "class_1", str(TODAY+timedelta(days=220)), "P901234", str(TODAY+timedelta(days=1095)), "MYNN", "active", str(TODAY-timedelta(days=680)), str(TODAY-timedelta(days=40)), 90.0, 390.0),
    (str(uuid.uuid4()), ORG_ID, "Hannah", "Berg", "hannah@pararig.com", "first_officer", "cpl", "HB-FO-0010", "US", str(TODAY+timedelta(days=365)), "class_1", str(TODAY+timedelta(days=130)), "P012345", str(TODAY+timedelta(days=730)), "MYNN", "active", str(TODAY-timedelta(days=420)), str(TODAY-timedelta(days=12)), 55.0, 220.0),
    # Chief Pilot
    (str(uuid.uuid4()), ORG_ID, "Shawn", "Tufts", "shawn.tufts@pararig.com", "captain", "atpl", "ST-CPT-0011", "US", str(TODAY+timedelta(days=730)), "class_1", str(TODAY+timedelta(days=250)), "P999999", str(TODAY+timedelta(days=1095)), "MYNN", "active", str(TODAY-timedelta(days=1095)), str(TODAY-timedelta(days=7)), 140.0, 560.0),
    # Support
    (str(uuid.uuid4()), ORG_ID, "Maria", "Santos", "maria@pararig.com", "dispatcher", None, None, None, None, None, None, None, None, "MYNN", "active", str(TODAY-timedelta(days=365)), None, 0, 0),
    (str(uuid.uuid4()), ORG_ID, "David", "Kim", "david@pararig.com", "mechanic", "mechanics", "DK-MECH-0012", "US", str(TODAY+timedelta(days=365)), None, None, None, None, "MYNN", "active", str(TODAY-timedelta(days=600)), None, 0, 0),
]

quals = [
    # Marcus (idx 0) - BT67
    (str(uuid.uuid4()), crew[0][0], "type_rating", "BT67", str(TODAY-timedelta(days=365)), str(TODAY+timedelta(days=365))),
    (str(uuid.uuid4()), crew[0][0], "proficiency_check", "BT67", str(TODAY-timedelta(days=180)), str(TODAY+timedelta(days=185))),
    # Diego (1) - BT67
    (str(uuid.uuid4()), crew[1][0], "type_rating", "BT67", str(TODAY-timedelta(days=730)), str(TODAY+timedelta(days=365))),
    (str(uuid.uuid4()), crew[1][0], "proficiency_check", "BT67", str(TODAY-timedelta(days=200)), str(TODAY+timedelta(days=165))),
    # Andre (2) - BT67 + K35X
    (str(uuid.uuid4()), crew[2][0], "type_rating", "BT67", str(TODAY-timedelta(days=365)), str(TODAY+timedelta(days=365))),
    (str(uuid.uuid4()), crew[2][0], "type_rating", "K35X", str(TODAY-timedelta(days=365)), str(TODAY+timedelta(days=365))),
    # Sarah (3) - K35X
    (str(uuid.uuid4()), crew[3][0], "type_rating", "K35X", str(TODAY-timedelta(days=730)), str(TODAY+timedelta(days=365))),
    (str(uuid.uuid4()), crew[3][0], "proficiency_check", "K35X", str(TODAY-timedelta(days=180)), str(TODAY+timedelta(days=185))),
    # James (4) - K35X + K200
    (str(uuid.uuid4()), crew[4][0], "type_rating", "K35X", str(TODAY-timedelta(days=730)), str(TODAY+timedelta(days=365))),
    (str(uuid.uuid4()), crew[4][0], "type_rating", "K200", str(TODAY-timedelta(days=365)), str(TODAY+timedelta(days=365))),
    (str(uuid.uuid4()), crew[4][0], "proficiency_check", "K35X", str(TODAY-timedelta(days=200)), str(TODAY+timedelta(days=165))),
    # Elena (5) - K35X + BT67
    (str(uuid.uuid4()), crew[5][0], "type_rating", "K35X", str(TODAY-timedelta(days=365)), str(TODAY+timedelta(days=365))),
    (str(uuid.uuid4()), crew[5][0], "type_rating", "BT67", str(TODAY-timedelta(days=365)), str(TODAY+timedelta(days=365))),
    # Tom (6) - K200
    (str(uuid.uuid4()), crew[6][0], "type_rating", "K200", str(TODAY-timedelta(days=730)), str(TODAY+timedelta(days=365))),
    (str(uuid.uuid4()), crew[6][0], "proficiency_check", "K200", str(TODAY-timedelta(days=180)), str(TODAY+timedelta(days=185))),
    # Kofi (7) - K200 + T300
    (str(uuid.uuid4()), crew[7][0], "type_rating", "K200", str(TODAY-timedelta(days=365)), str(TODAY+timedelta(days=365))),
    (str(uuid.uuid4()), crew[7][0], "type_rating", "T300", str(TODAY-timedelta(days=365)), str(TODAY+timedelta(days=365))),
    # Luis (8) - T300
    (str(uuid.uuid4()), crew[8][0], "type_rating", "T300", str(TODAY-timedelta(days=730)), str(TODAY+timedelta(days=365))),
    (str(uuid.uuid4()), crew[8][0], "proficiency_check", "T300", str(TODAY-timedelta(days=180)), str(TODAY+timedelta(days=185))),
    # Hannah (9) - T300 + K200
    (str(uuid.uuid4()), crew[9][0], "type_rating", "T300", str(TODAY-timedelta(days=365)), str(TODAY+timedelta(days=365))),
    (str(uuid.uuid4()), crew[9][0], "type_rating", "K200", str(TODAY-timedelta(days=365)), str(TODAY+timedelta(days=365))),
    # Shawn (10) - all 4
    (str(uuid.uuid4()), crew[10][0], "type_rating", "BT67", str(TODAY-timedelta(days=730)), str(TODAY+timedelta(days=365))),
    (str(uuid.uuid4()), crew[10][0], "type_rating", "K35X", str(TODAY-timedelta(days=730)), str(TODAY+timedelta(days=365))),
    (str(uuid.uuid4()), crew[10][0], "type_rating", "K200", str(TODAY-timedelta(days=730)), str(TODAY+timedelta(days=365))),
    (str(uuid.uuid4()), crew[10][0], "type_rating", "T300", str(TODAY-timedelta(days=730)), str(TODAY+timedelta(days=365))),
    (str(uuid.uuid4()), crew[10][0], "proficiency_check", "BT67", str(TODAY-timedelta(days=180)), str(TODAY+timedelta(days=185))),
    (str(uuid.uuid4()), crew[10][0], "proficiency_check", "K35X", str(TODAY-timedelta(days=180)), str(TODAY+timedelta(days=185))),
    (str(uuid.uuid4()), crew[10][0], "proficiency_check", "K200", str(TODAY-timedelta(days=180)), str(TODAY+timedelta(days=185))),
    (str(uuid.uuid4()), crew[10][0], "proficiency_check", "T300", str(TODAY-timedelta(days=180)), str(TODAY+timedelta(days=185))),
    # Maria (11) - dispatcher
    (str(uuid.uuid4()), crew[11][0], "hazmat", None, str(TODAY-timedelta(days=180)), str(TODAY+timedelta(days=185))),
    (str(uuid.uuid4()), crew[11][0], "dgr", None, str(TODAY-timedelta(days=180)), str(TODAY+timedelta(days=185))),
    # David (12) - mechanic
    (str(uuid.uuid4()), crew[12][0], "type_rating", "BT67", str(TODAY-timedelta(days=365)), str(TODAY+timedelta(days=365))),
    (str(uuid.uuid4()), crew[12][0], "type_rating", "K35X", str(TODAY-timedelta(days=365)), str(TODAY+timedelta(days=365))),
]

conn = sqlite3.connect(DB)
c = conn.cursor()

# Check if crew already seeded
c.execute("SELECT COUNT(*) FROM crew_members WHERE organization_id = ?", (ORG_ID,))
if c.fetchone()[0] > 0:
    print("Crew already seeded. Delete crew_members + crew_qualifications to re-seed.")
    conn.close()
    exit()

# Insert crew
NOW = date.today().isoformat()
c.executemany("""INSERT INTO crew_members (id, organization_id, first_name, last_name, email, role, license_type, license_number, license_country, license_expiry, medical_class, medical_expiry, passport_number, passport_expiry, base_airport, status, date_of_hire, last_proficiency_date, last_90d_hours, last_12m_hours, created_at, updated_at)
VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", [list(r) + [NOW, NOW] for r in crew])

# Insert quals
c.executemany("""INSERT INTO crew_qualifications (id, crew_id, qual_type, aircraft_type, issued_date, expiry_date, status, created_at)
VALUES (?,?,?,?,?,?,'current',?)""", [list(r) + [NOW] for r in quals])

conn.commit()
print(f"Seeded {len(crew)} crew members with {len(quals)} qualifications.")
conn.close()
