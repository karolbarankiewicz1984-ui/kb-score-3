"""Bridge real PitchAPI league.matches response bytes to ORIGINAL v3 verified_view.

Runs inside the EXISTING three-league collector with its already captured
network receipts: zero additional provider requests. Output is plaintext
native source in a PRIVATE short-lived GitHub Actions artifact, never git.
No model fit, no TEST, no retrospective PIT certification.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

from src.kb3_p1_shared_asof_features_v2 import build_shared_features
from src.kb3_catboost_research_v3 import vector

LEAGUES = {"ESP", "ITA", "GER"}
SCHEMA = "kb3-v3-native-github-forward-bridge-v1"
BUFFER = timedelta(hours=2)
LEAD = timedelta(minutes=90)
RESULT_LAG = timedelta(hours=3)


class BridgeError(ValueError):
    pass


def clock(s):
    if not isinstance(s, str) or not s.endswith("Z"):
        raise BridgeError("NATIVE_UTC_REQUIRED")
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def stamp(dt):
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def raw_json(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def season_start(season):
    return int(season.split("/")[0])


def convert(m, league, season, *, target=False):
    result = dict(league=league, fixture_id=str(m["id"]),
                  home_team_id=str(m["home_team"]["id"]),
                  away_team_id=str(m["away_team"]["id"]),
                  kickoff_utc=m["time_utc"], season_start_year=season_start(season))
    if not target:
        result.update(status="FINISHED", goals_home_90=m["score_home"],
                      goals_away_90=m["score_away"])
    return result


def produce(receipts, destination, *, created_now=None):
    """Write raw byte members and deterministic original-builder input members.

    The exact Github-hosted artifact id is intentionally NOT forged here.
    The next workflow resolves it from GitHub API and checks host creation
    <= frozen cutoff, then calls verified_view on the original bytes.
    """
    from scripts.step14_three_league_pitchapi_actual_audit import CURRENT, PREVIOUS
    now = created_now or datetime.now(timezone.utc)
    if now.utcoffset() != timedelta(0):
        raise BridgeError("UTC_REQUIRED")
    cutoff = now + BUFFER
    target_limit = now + timedelta(hours=96)
    out = Path(destination)
    if out.exists():
        raise BridgeError("IMMUTABLE_NATIVE_BRIDGE_EXISTS")
    selected = {}
    for r in receipts:
        resource = r.get("resource", "")
        if not resource.startswith("pitchapi:pilot_daily:"):
            continue
        _, _, country, season = resource.split(":", 3)
        if country not in LEAGUES or season not in (CURRENT, PREVIOUS):
            raise BridgeError("UNEXPECTED_NATIVE_RESOURCE")
        if (country, season) in selected:
            raise BridgeError("DUPLICATE_NATIVE_LEAGUE_SNAPSHOT")
        if r.get("origin") != "NETWORK_OBSERVED":
            raise BridgeError("SYNTHETIC_SOURCE_NOT_ALLOWED")
        if clock(r["completed_at_utc"]) > now:
            raise BridgeError("SOURCE_COMPLETED_AFTER_SNAPSHOT")
        payload = r["payload"]
        if not isinstance(payload, dict) or not isinstance(payload.get("matches"), list):
            raise BridgeError("NATIVE_MATCHES_REQUIRED")
        selected[(country, season)] = r
    if set(selected) != {(c, s) for c in LEAGUES for s in (CURRENT, PREVIOUS)}:
        raise BridgeError("MISSING_REAL_NATIVE_SIX_SNAPSHOTS")

    # Fail closed: no partial directory after any malformed provider record.
    import shutil
    out.mkdir(parents=True, exist_ok=False)
    try:
        sources = {}
        for (country, season), receipt in sorted(selected.items()):
            payload = receipt["payload"]
            member = "source/" + country + "_" + season.replace("/", "_") + ".json"
            blob = raw_json(payload)
            (out / member).parent.mkdir(parents=True, exist_ok=True)
            (out / member).write_bytes(blob)
            sources[(country, season)] = dict(
                member=member, sha256=sha(blob),
                observed_completed_at_utc=receipt["completed_at_utc"],
                payload=payload,
            )
        produced = []
        for country in sorted(LEAGUES):
            current = sources[(country, CURRENT)]
            current_matches = current["payload"]["matches"]
            old = sources[(country, PREVIOUS)]
            all_matches = [(m, CURRENT, current) for m in current_matches] + [
                (m, PREVIOUS, old) for m in old["payload"]["matches"]]
            future = sorted((m for m in current_matches
                             if m.get("status") in ("upcoming", "not_started", "scheduled")
                             and cutoff + LEAD <= clock(m["time_utc"]) <= target_limit
                             and m.get("score_home") is None and m.get("score_away") is None),
                            key=lambda m: (m["time_utc"], str(m["id"])))[:10]
            for m in future:
                ko = clock(m["time_utc"])
                if ko < cutoff + LEAD:
                    raise BridgeError("TARGET_TOO_CLOSE")
                predecessors = []
                seen = set()
                for p, season, src in all_matches:
                    if (p.get("status") != "finished"
                            or clock(p["time_utc"]) + RESULT_LAG > clock(src["observed_completed_at_utc"])
                            or clock(p["time_utc"]) >= cutoff):
                        continue
                    if str(p["id"]) in seen:
                        raise BridgeError("DUPLICATE_PREDECESSOR_FIXTURE")
                    seen.add(str(p["id"]))
                    if (type(p.get("score_home")) is not int
                            or type(p.get("score_away")) is not int):
                        continue
                    row = convert(p, country, season)
                    row["result_receipt"] = dict(
                        source_class="NETWORK_OBSERVED",
                        observed_completed_at_utc=src["observed_completed_at_utc"],
                        captured_at_utc=src["observed_completed_at_utc"],
                        source_sha256=src["sha256"],
                    )
                    predecessors.append(row)
                target = convert(m, country, CURRENT, target=True)
                receipt = dict(source_class="NETWORK_OBSERVED",
                               observed_completed_at_utc=current["observed_completed_at_utc"],
                               captured_at_utc=current["observed_completed_at_utc"],
                               source_sha256=current["sha256"])
                inp = dict(target=target, cutoff_utc=stamp(cutoff),
                           target_receipt=receipt, predecessor_rows=predecessors)
                # This is the original v2 builder, not a surrogate or imported vector.
                view = build_shared_features(purpose="FORWARD", **inp)
                if len(vector(view)) != 87:
                    raise BridgeError("ORIGINAL_V3_VECTOR_NOT_87")
                member = "input/" + country + "_" + sha(str(m["id"]).encode())[:16] + ".json"
                blob = raw_json(inp)
                (out / member).parent.mkdir(parents=True, exist_ok=True)
                (out / member).write_bytes(blob)
                produced.append(dict(league=country, fixture_id=str(m["id"]),
                                     kickoff_utc=m["time_utc"], cutoff_utc=stamp(cutoff),
                                     input_member=member, input_sha256=sha(blob),
                                     source_members=sorted({src["member"] for src in
                                         (current, old)}),
                                     feature_count=87,
                                     independent_archive_verified=False,
                                     training_allowed=False))
        # Zero targets is valid; must not invent a forecast.
        manifest = dict(schema=SCHEMA, generated_at_utc=stamp(now),
                        cutoff_utc=stamp(cutoff),
                        source_count=len(sources), target_count=len(produced),
                        targets=produced,
                        source_index=[dict(country=c, season=s, member=x["member"],
                                           sha256=x["sha256"])
                                      for (c, s), x in sorted(sources.items())],
                        host_artifact_created_before_cutoff_verified=False,
                        source_provider_first_publication_certified=False,
                        original_builder_v2_used=True,
                        original_vector_v3_87_used=True,
                        production_approved=False, training_allowed=False)
        (out / "bridge_manifest.json").write_bytes(raw_json(manifest))
        return manifest
    except BaseException:
        shutil.rmtree(out, ignore_errors=True)
        raise
