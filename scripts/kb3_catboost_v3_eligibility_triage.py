"""Read-only decision matrix for v3 historical eligibility; never turns late data into PIT."""
import json
from pathlib import Path

def assess(inventory):
    counts=inventory["table_counts"]
    obs=counts["observations"]
    late=inventory["observations_recorded_after_target_kickoff"]
    first=inventory["observations_with_provider_first_published"]
    listings=counts["finished_fixture_index"]
    late_list=inventory["fixture_listing_recorded_after_target_kickoff"]
    if not (0<=late<=obs and 0<=first<=obs and 0<=late_list<=listings):
        raise ValueError("INVALID_INVENTORY_COUNTS")
    if inventory["integrity"]!="ok" or not inventory["source_unchanged"]:
        raise ValueError("UNTRUSTED_SQLITE_INVENTORY")
    return {
        "schema":"kb3-v3-eligibility-triage-v1",
        "historical_observations":obs,
        "historical_target_late_observations":late,
        "target_late_fraction":late/obs if obs else None,
        "historical_listings":listings,
        "target_late_listings":late_list,
        "provider_first_publication_evidence_rows":first,
        "formally_admitted_v3_train_rows":0,
        "reconstructed_history_use":"DESCRIPTIVE_RESEARCH_ONLY",
        "critical_distinction":"A predecessor observation after its OWN kickoff can be available before a LATER target cutoff; this inventory does not establish that availability for any particular later target.",
        "next_evidence_needed":[
            "target-specific cutoff and immutable archived source input bytes",
            "each predecessor observed/captured timestamp <= target cutoff",
            "GitHub host-created archive timestamp <= target cutoff",
            "source-to-fixture identity and checksum verification",
            "chronological split and independent outcome receipt"],
        "research_experiment_permitted":"OFFLINE_DIAGNOSTICS_WITH_UNCERTIFIED_LABELS_ONLY",
        "real_v3_training_permitted":False,
        "production_approved":False,
        "no_retrospective_forecasts":True
    }

if __name__=="__main__":
    path=Path("reports/KB3_CATBOOST_V3_SOURCE_INVENTORY_2026-11-09.json")
    print(json.dumps(assess(json.loads(path.read_text())),indent=2,ensure_ascii=False))
