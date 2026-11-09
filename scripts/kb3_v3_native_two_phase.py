"""Isolated two-phase real native-source archive for KB3 CatBoost shared-asof V3.

Phase 1: 7 existing PitchAPI API calls (catalog + 2 seasons x 3 leagues).
         Archive original SDK-native JSON responses AND normalized pre-cutoff
         inputs as one immutable GitHub Actions artifact. No model writes.
Phase 2: verify GitHub API host-created time + hosted ZIP hash, each native
         member hash/identity, and re-build original shared-asof 87 features.
         A result after its original cutoff is never rewritten as historical PIT.

This module DOES NOT fit a CatBoost or promote M0/Champion/TEST. It archives
research-only candidates even after valid native observation verification.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from pathlib import Path
import argparse
import hashlib
import io
import json
import os
import re
import shutil
import time
import zipfile

from src.kb3_features import utc_dt, utc_str, digest
from src.kb3_p1_shared_asof_features_v2 import when, need
from src.kb3_catboost_research_v3 import verified_view, vector, contract
CURRENT = "2026/2027"
PREVIOUS = "2025/2026"

SCHEMA = "kb3-v3-raw-native-two-phase-v1"
LEAGUES = ("ESP", "ITA", "GER")
FIXTURE_LAG = timedelta(hours=3)
MIN_LEAD = timedelta(minutes=90)
MAX_CALLS = 7
CUTOFF_BUFFER = timedelta(minutes=6)
MAX_TARGETS_PER_LEAGUE = 3
MAX_HORIZON = timedelta(days=4)
UTC = timezone.utc


def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf8")


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def receipt(payload, completed_at):
    return dict(source_class="NETWORK_OBSERVED",
                observed_completed_at_utc=completed_at,
                captured_at_utc=completed_at,
                source_sha256=sha(canonical(payload)))


def native_identity(row):
    need(isinstance(row, dict), "NATIVE_ROW_REQUIRED")
    need(type(row.get("id")) is str and bool(row["id"]), "NATIVE_MATCH_ID_REQUIRED")
    need(isinstance(row.get("home_team"), dict) and
         isinstance(row.get("away_team"), dict), "NATIVE_TEAMS_REQUIRED")
    home = row["home_team"].get("id")
    away = row["away_team"].get("id")
    need(type(home) is str and type(away) is str and home != away and
         bool(home) and bool(away), "NATIVE_TEAM_IDS_REQUIRED")
    ko = when(row.get("time_utc"))
    return home, away, ko


def build_bundle(source_payloads, *, captured_at, cutoff_at, outdir):
    """Pure deterministic writer. Source clocks are measured, NEVER invented.

    source_payloads maps (league, start_year) to
    {'payload': native {matches:[...]}, 'completed_at_utc': canonical UTC}.
    Test fixtures may supply synthetic times; only the live collector marks
    actual network traffic. Tests are NEVER submitted as actual host proof.
    """
    captured = when(captured_at)
    cutoff = when(cutoff_at)
    need(captured <= cutoff - timedelta(minutes=1), "CUTOFF_TOO_SOON")
    need(set(source_payloads) == {(l, y) for l in LEAGUES for y in (2025, 2026)},
         "SIX_NATIVE_LEAGUE_SEASON_SOURCES_REQUIRED")
    out = Path(outdir)
    need(not out.exists(), "IMMUTABLE_BUNDLE_EXISTS")
    files = {}
    material = {}
    for league in LEAGUES:
        for year in (2025, 2026):
            record = source_payloads[(league, year)]
            payload = record["payload"]
            completed_at = when(record["completed_at_utc"])
            need(completed_at <= captured <= cutoff, "SOURCE_AFTER_CAPTURE_OR_CUTOFF")
            need(isinstance(payload, dict) and
                 isinstance(payload.get("matches"), list), "NATIVE_MATCHES_REQUIRED")
            member = "sources/" + league + "_" + str(year) + ".json"
            files[member] = canonical(payload)
            match_ids = set()
            for row in payload["matches"]:
                native_identity(row)
                need(row["id"] not in match_ids, "DUPLICATE_NATIVE_MATCH_ID")
                match_ids.add(row["id"])
            material[(league, year)] = {
                "matches": payload["matches"],
                "receipt": receipt(payload, record["completed_at_utc"]),
                "member": member,
                "sha256": sha(files[member]),
            }

    index = {
        "schema": SCHEMA, "cutoff_utc": cutoff_at,
        "network_capture_completed_at_utc": captured_at,
        "provider_first_publication_certified": False,
        "research_only": True, "production_approved": False,
        "provider_calls_hard_cap": MAX_CALLS,
        "sources": [{"league": k[0], "season_start_year": k[1],
                     "member": v["member"], "sha256": v["sha256"]}
                    for k, v in sorted(material.items())],
        "inputs": [],
    }
    for league in LEAGUES:
        old = material[(league, 2025)]
        curr = material[(league, 2026)]
        prior = []
        for year, source in ((2025, old), (2026, curr)):
            for m in source["matches"]:
                home, away, ko = native_identity(m)
                if (m.get("status") != "finished" or
                    ko + FIXTURE_LAG > when(source["receipt"]["observed_completed_at_utc"]) or
                    ko + FIXTURE_LAG > cutoff):
                    continue
                gh, ga = m.get("score_home"), m.get("score_away")
                need(type(gh) is int and type(ga) is int and
                     0 <= gh <= 30 and 0 <= ga <= 30, "FINISHED_SCORE_INVALID")
                prior.append({
                    "league": league, "fixture_id": m["id"],
                    "home_team_id": home, "away_team_id": away,
                    "kickoff_utc": m["time_utc"], "season_start_year": year,
                    "status": "FINISHED",
                    "goals_home_90": gh, "goals_away_90": ga,
                    "result_receipt": dict(source["receipt"]),
                })
        prior.sort(key=lambda x: (x["kickoff_utc"], x["fixture_id"]))
        need(len({x["fixture_id"] for x in prior}) == len(prior),
             "CROSS_SEASON_DUPLICATE_RESULT_ID")
        future = []
        for m in curr["matches"]:
            home, away, ko = native_identity(m)
            if m.get("status") not in ("upcoming", "scheduled", "not_started"):
                continue
            if ko < cutoff + MIN_LEAD or ko > cutoff + MAX_HORIZON:
                continue
            need(m.get("score_home") is None and
                 m.get("score_away") is None, "TARGET_LABEL_ALREADY_AVAILABLE")
            future.append(m)
        future.sort(key=lambda x: (x["time_utc"], x["id"]))
        for m in future[:MAX_TARGETS_PER_LEAGUE]:
            home, away, ko = native_identity(m)
            inp = {
                "target": {
                    "league": league, "fixture_id": m["id"],
                    "home_team_id": home, "away_team_id": away,
                    "kickoff_utc": m["time_utc"],
                    "season_start_year": 2026,
                },
                "cutoff_utc": cutoff_at,
                "target_receipt": dict(curr["receipt"]),
                "predecessor_rows": [x for x in prior
                                     if x["fixture_id"] != m["id"]],
            }
            identifier = sha((league + ":" + m["id"]).encode())[:24]
            member = "inputs/" + identifier + ".json"
            files[member] = canonical(inp)
            index["inputs"].append({
                "league": league,
                "fixture_id": m["id"],
                "kickoff_utc": m["time_utc"],
                "member": member,
                "sha256": sha(files[member]),
            })
    need(bool(index["inputs"]), "NO_FUTURE_TARGETS_AT_PLANNED_CUTOFF")
    files["index.json"] = canonical(index)
    out.mkdir(parents=True, exist_ok=False)
    try:
        for member, blob in sorted(files.items()):
            target = out / member
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as fd:
                fd.write(blob)
    except BaseException:
        shutil.rmtree(out, ignore_errors=True)
        raise
    return {
        "schema": SCHEMA, "cutoff_utc": cutoff_at,
        "inputs_written": len(index["inputs"]), "sources_written": 6,
        "calls": MAX_CALLS, "research_only": True,
        "model_fit": False, "production_approved": False,
    }


def collect(outdir, key, *, client_factory=None, clock=None):
    from scripts.step14_three_league_pitchapi_actual_audit import select_three
    from scripts.pitchapi_step06_audit import to_plain
    need(type(key) is str and bool(key.strip()), "EXISTING_PITCHAPI_KEY_REQUIRED")
    if client_factory is None:
        from pitchapi import PitchAPI
        client_factory = PitchAPI
    clock = clock or (lambda: datetime.now(UTC))
    client = client_factory(api_key=key)
    before = clock()
    need(before.utcoffset() == timedelta(0), "REAL_CAPTURE_UTC_REQUIRED")
    calls = 0

    def call(method, *args, **kwargs):
        nonlocal calls
        need(calls < MAX_CALLS, "MAX_7_PITCHAPI_CALLS")
        calls += 1
        started = clock()
        response = to_plain(method(*args, **kwargs))
        completed = clock()
        need(completed >= started and
             (completed - started) <= timedelta(minutes=3), "UNTRUSTED_CAPTURE_INTERVAL")
        need(isinstance(response, dict), "NATIVE_RESPONSE_NOT_DICT")
        return response, utc_str(completed)

    catalogue, _ = call(client.leagues.list)
    selected = select_three(catalogue)
    data = {}
    for title, league, expected, league_id in selected:
        for year, season in ((2025, PREVIOUS), (2026, CURRENT)):
            raw, timestamp = call(client.leagues.matches, league_id, season=season,
                                  **({"status": "all"} if year == 2026 else {}))
            need(isinstance(raw.get("matches"), list) and
                 len(raw["matches"]) == expected, "NATIVE_FIXTURE_COUNT_INVALID:" + league)
            data[(league, year)] = {"payload": raw, "completed_at_utc": timestamp}
    need(calls == MAX_CALLS, "PROVIDER_CALL_COUNT_DRIFT")
    captured = utc_str(clock())
    cutoff = utc_str(utc_dt(captured) + CUTOFF_BUFFER)
    result = build_bundle(data, captured_at=captured,
                          cutoff_at=cutoff, outdir=outdir)
    result["calls"] = calls
    return result


class HostedOneArtifact:
    """Read adapter for the original V3 verified_view with GitHub host evidence.

    Caller MUST supply artifact metadata obtained from GitHub REST API, not
    from archived self-assertions. The whole ZIP digest is verified first.
    """
    def __init__(self, raw_zip, *, artifact_id, created_at, digest_sha256):
        need(type(artifact_id) is int and artifact_id > 0, "ARTIFACT_ID_REQUIRED")
        self.artifact_id = str(artifact_id)
        self.created = when(created_at)
        need(digest_sha256 == "sha256:" + sha(raw_zip),
             "HOSTED_ARCHIVE_SHA256_MISMATCH")
        self.z = zipfile.ZipFile(io.BytesIO(raw_zip))
        names = self.z.namelist()
        need(len(set(names)) == len(names), "DUPLICATE_ZIP_MEMBER")
        self.names = set(names)

    def read(self, ref):
        need(str(ref["artifact_id"]) == self.artifact_id,
             "FOREIGN_ARTIFACT_ID")
        member = ref["member"]
        need(type(member) is str and member in self.names and
             not member.startswith("/") and
             ".." not in member.split("/"), "UNSAFE_OR_MISSING_MEMBER")
        info = self.z.getinfo(member)
        need(0 < info.file_size <= 16 * 1024 * 1024, "MEMBER_TOO_LARGE")
        blob = self.z.read(member)
        need(sha(blob) == ref["sha256"], "NATIVE_MEMBER_SHA256_MISMATCH")
        return json.loads(blob), self.created


def verify_artifact(raw_zip, *, artifact_id, created_at, digest_sha256,
                    at_utc=None, require_after_cutoff=True):
    """Actual research candidate freeze; never manufactures PIT evidence."""
    a = HostedOneArtifact(raw_zip, artifact_id=artifact_id,
                          created_at=created_at, digest_sha256=digest_sha256)
    need("index.json" in a.names, "MISSING_ARCHIVED_INDEX")
    index = json.loads(a.z.read("index.json"))
    need(index.get("schema") == SCHEMA, "WRONG_INPUT_ARCHIVE_SCHEMA")
    need(index.get("research_only") is True and
         index.get("production_approved") is False, "GOVERNANCE_DRIFT")
    cutoff = when(index["cutoff_utc"])
    need(a.created <= cutoff, "HOST_ARCHIVE_AFTER_EXACT_CUTOFF")
    now = when(at_utc) if at_utc is not None else datetime.now(UTC)
    if require_after_cutoff:
        need(cutoff <= now <= cutoff + timedelta(minutes=45),
             "FREEZE_OUTSIDE_REAL_CUTOFF_WINDOW")
    need(now >= a.created, "FREEZE_BEFORE_HOST_CREATED")
    expected_sources = {}
    for item in index["sources"]:
        source_ref = {"artifact_id": a.artifact_id, "member": item["member"],
                      "sha256": item["sha256"]}
        doc, created = a.read(source_ref)
        need(isinstance(doc, dict) and isinstance(doc.get("matches"), list),
             "INVALID_NATIVE_SOURCE")
        expected_sources[item["sha256"]] = source_ref
    need(len(expected_sources) == 6, "SIX_UNIQUE_NATIVE_SOURCES_REQUIRED")
    rows = []
    for entry in index["inputs"]:
        cutoff_lead = when(entry["kickoff_utc"]) - cutoff
        if cutoff_lead < MIN_LEAD:
            raise ValueError("TARGET_NOT_PREMATCH_AT_CUTOFF")
        archive_ref = {"artifact_id": a.artifact_id, "member": entry["member"],
                       "sha256": entry["sha256"]}
        inp, _ = a.read(archive_ref)
        need(inp.get("cutoff_utc") == index["cutoff_utc"],
             "INDIVIDUAL_CUTOFF_DRIFT")
        sample = {"input": inp, "input_archive": archive_ref,
                  "source_archives": expected_sources}
        # The original v3 function checks EVERY included native result's
        # source bytes, capture/host clocks, team/match IDs and 90-min scores.
        view = verified_view(sample, a, "FORWARD")
        ordered = vector(view)
        need(len(ordered) == contract()["feature_count"] == 87,
             "V3_NOT_87_FEATURES")
        need(view["training_allowed"] is False, "TRAINING_FLAG_DRIFT")
        # A genuinely pre-kickoff freeze must finish before kickoff - 90m.
        if require_after_cutoff:
            need(now < when(entry["kickoff_utc"]) - MIN_LEAD,
                 "TOO_LATE_FOR_PREMATCH_FREEZE")
        rows.append({
            "league": entry["league"],
            "fixture_id": entry["fixture_id"],
            "kickoff_utc": entry["kickoff_utc"],
            "feature_cutoff_utc": inp["cutoff_utc"],
            "feature_sha256": view["canonical_features_sha256"],
            "feature_count": len(ordered),
            "values": ordered,
            "availability_class": view["availability_class"],
            "formal_training_allowed": False,
            "research_only": True,
        })
    need(bool(rows), "NO_VALID_NATIVE_V3_TARGETS")
    report = {
        "schema": "kb3-v3-frozen-native-input-verified-no-model-fit-v1",
        "source_artifact_id": artifact_id,
        "source_artifact_created_at_utc": created_at,
        "source_artifact_sha256": digest_sha256,
        "planned_cutoff_utc": index["cutoff_utc"],
        "validated_at_utc": utc_str(now),
        "independently_archived_before_exact_cutoff": True,
        "native_sources_verified": 6,
        "verified_v3_input_vectors": len(rows),
        "frozen_candidates": rows,
        "provider_original_first_publication_certified": False,
        "formal_v3_training_admitted": 0,
        "new_catboost_models_trained": 0,
        "production_approved": False,
        "m0_champion_test_untouched": True,
    }
    report["sha256"] = digest(report)
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=("capture", "verify"))
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--zip", type=Path)
    p.add_argument("--artifact-id", type=int)
    p.add_argument("--created-at")
    p.add_argument("--digest")
    p.add_argument("--wait-until-cutoff", action="store_true")
    args = p.parse_args()
    if args.command == "capture":
        result = collect(args.output, os.environ.get("PITCHAPI_API_KEY"))
        print(json.dumps(result, sort_keys=True))
        return
    need(args.zip and args.artifact_id and args.created_at and args.digest,
         "HOSTED_GITHUB_ARCHIVE_ARGS_REQUIRED")
    raw = args.zip.read_bytes()
    if args.wait_until_cutoff:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            index = json.loads(z.read("index.json"))
        cutoff = when(index["cutoff_utc"])
        seconds = (cutoff - datetime.now(UTC)).total_seconds()
        need(seconds <= 8 * 60, "UNEXPECTED_WAIT_BEFORE_CUTOFF")
        if seconds > 0:
            time.sleep(seconds)
    report = verify_artifact(raw, artifact_id=args.artifact_id,
                             created_at=args.created_at,
                             digest_sha256=args.digest)
    need(not args.output.exists(), "OUTPUT_ALREADY_EXISTS")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf8") as f:
        json.dump(report, f, sort_keys=True, ensure_ascii=False, indent=2)
        f.write("\n")
    print("VERIFIED_NATIVE_V3_CANDIDATES", report["verified_v3_input_vectors"],
          "FORMAL_FIT", report["new_catboost_models_trained"],
          "NO_PRODUCTION_CHANGES")


if __name__ == "__main__":
    main()
