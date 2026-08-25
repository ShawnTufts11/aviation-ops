# Test Mission: "Caribbean Loop Challenge"
## Seed Data for Demo

## Route (6 Stops)

| Leg | From | To | Est Block | Notes |
|-----|------|----|-----------|-------|
| 1 | MYNN → KMIA | Nassau → Miami | ~1:15 | US customs inbound |
| 2 | KMIA → MMUN | Miami → Cancun | ~2:00 | Mexico landing permit |
| 3 | MMUN → MTPP | Cancun → Port-au-Prince | ~2:15 | Haiti security, NOTAMs |
| 4 | MTPP → MUHA | Port-au-Prince → Havana | ~1:30 | Cuba OFAC permit |
| 5 | MUHA → MDPC | Havana → Punta Cana | ~1:45 | Night arrival, DR customs |
| 6 | MDPC → MYNN | Punta Cana → Nassau | ~1:30 | Return to base |
| | **Total** | | **~10:15** | |

## Crew Swap Point

**Swap at:** KMIA (Miami) — end of Leg 2
- Inbound crew: PIC / SIC — arrive KMIA after MYNN→KMIA→MMUN round
- Outbound crew: fresh PIC / SIC — commercially flown to KMIA, hotel overnight
- *This exercises: commercial flight booking, hotel coordination, duty day reset*

## Aircraft

**Primary:** King Air 350 (long range, fits all legs)
**Test leg:** Swap to Twin Otter (T300) for Leg 3 or 4 to trigger range/fuel flags

## Known Gaps I Need Your Input On

### Aircraft Performance
I can use published specs for KA350 / T300 fuel burn and speeds, but want to confirm:
- **KA350:** ~350 KTAS cruise, ~500 lbs/hr fuel burn per side? Or specific numbers you know?
- **T300:** ~170 KTAS, ~300-400 lbs/hr? 
- **BT-67 & K200:** any specific numbers you want in the seed data even if not in this demo?

### The MEL Scenario
You mentioned "a deferred maintenance item on one leg that requires MEL and waiver" — what specific gripe? Suggestions for something realistic:
- *Inop autopilot on one leg → restricts to 2-pilot IFR only*
- *Cargo door actuator slow → cargo missions only for that leg*
- *Weather radar inop → can't penetrate forecast weather on Leg 3*
Which feels right to demo?

### Customs / Manifest Challenges
The passenger swap issue you mentioned (leaving and returning to foreign countries with different manifests) — can you give me concrete details for the demo:
- Which stop has the manifest change problem?
- How does the manifest differ on departure vs return?
- Is there a specific customs/border situation you want to highlight?
- Are we including eAPIS filing in-scope for V1?

### Cuba / OFAC
For the Havana stop — do you want the system to flag the OFAC permit requirement, or do you have specific knowledge of how this works for contract ops into Cuba?

---

Once I have these specifics, I can build:
1. The backend data model (aircraft profiles, crew, manifests, customs rules)
2. The route planner integration with the 6-stop route
3. The V1 release form page pre-loaded with this mission as example data
