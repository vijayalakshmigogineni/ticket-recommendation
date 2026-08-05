"""Phase 1 pilot benchmark customer roster (20 customers), generated per
docs/benchmark_dataset_spec.md v2. Distinct from data/sample_dataset/ (the
small hand-authored harness-validation fixture, kept as-is) -- this is the
real Phase 1 pilot corpus.

`multi_sender_alt` on 5 customers records a second, plausible-but-unregistered
staff contact used by (a) a handful of corpus interactions for realism, and
(b) eval queries testing the multi_sender_unregistered customer-identification
scenario (docs/benchmark_dataset_spec.md v2 section 7.4). This field is
generation-time-only -- never persisted, mirrors Customer.inbox_email being
the only real, persisted identifying address.
"""

from __future__ import annotations

CUSTOMERS = [
    {"key": "cedar_grove", "name": "Cedar Grove Family Practice",
     "inbox_email": "billing@cedargrovefamily.com"},
    {"key": "summit", "name": "Summit Orthopedic Group",
     "inbox_email": "billing@summitortho.com",
     "multi_sender_alt": {"name": "Maria Chen", "role": "Office Manager", "email": "m.chen@summitortho.com"}},
    {"key": "brightside", "name": "Brightside Pediatrics",
     "inbox_email": "office@brightsidepeds.com"},
    {"key": "pacific", "name": "Pacific Cardiology Associates",
     "inbox_email": "ar@pacificcardiology.com"},
    {"key": "meadowbrook", "name": "Meadowbrook Women's Health",
     "inbox_email": "frontdesk@meadowbrookwomens.com"},
    {"key": "clearskin", "name": "ClearSkin Dermatology",
     "inbox_email": "billing@clearskinderm.com",
     "multi_sender_alt": {"name": "Dr. Raj Patel", "role": "Physician", "email": "r.patel@clearskinderm.com"}},
    {"key": "northgate", "name": "Northgate Behavioral Health",
     "inbox_email": "admin@northgatebh.com"},
    {"key": "ironwood", "name": "Ironwood Pain Specialists",
     "inbox_email": "billing@ironwoodpain.com"},
    {"key": "bayview", "name": "Bayview Urgent Care",
     "inbox_email": "billing@bayviewurgentcare.com",
     "multi_sender_alt": {"name": "Sam Okafor", "role": "Front Desk Lead", "email": "s.okafor@bayviewurgentcare.com"}},
    {"key": "stonebridge", "name": "Stonebridge Physical Therapy",
     "inbox_email": "office@stonebridgept.com"},
    {"key": "hillcrest", "name": "Hillcrest Internal Medicine",
     "inbox_email": "billing@hillcrestim.com"},
    {"key": "vanguard", "name": "Vanguard Urology Associates",
     "inbox_email": "ar@vanguardurology.com"},
    {"key": "eastside", "name": "Eastside Endocrinology",
     "inbox_email": "billing@eastsideendo.com",
     "multi_sender_alt": {"name": "Linda Park", "role": "Billing Coordinator", "email": "l.park@eastsideendo.com"}},
    {"key": "golden_gate", "name": "Golden Gate Neurology",
     "inbox_email": "office@goldengateneuro.com"},
    {"key": "westfield", "name": "Westfield Gastroenterology",
     "inbox_email": "billing@westfieldgastro.com"},
    {"key": "parkview", "name": "Parkview ENT & Allergy",
     "inbox_email": "front@parkviewent.com"},
    {"key": "lakeshore", "name": "Lakeshore Podiatry Group",
     "inbox_email": "billing@lakeshorepodiatry.com"},
    {"key": "cornerstone", "name": "Cornerstone Rheumatology",
     "inbox_email": "ar@cornerstonerheum.com",
     "multi_sender_alt": {"name": "Dana Reyes", "role": "Billing Specialist", "email": "dana.reyes@cornerstonerheum.com"}},
    {"key": "maple_ridge", "name": "Maple Ridge Psychiatry",
     "inbox_email": "admin@mapleridgepsych.com"},
    {"key": "horizon", "name": "Horizon Oncology Partners",
     "inbox_email": "billing@horizononcology.com"},
]

MULTI_SENDER_CUSTOMER_KEYS = [c["key"] for c in CUSTOMERS if "multi_sender_alt" in c]
