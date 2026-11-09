"""Verify independently hosted native bytes using ORIGINAL CatBoost v3 verified_view.

No PitchAPI calls. Host metadata is read from GitHub API, never a manifest
assertion. No provider credentials, private RSA key, fit or model promotion.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import zipfile

from src.kb3_catboost_research_v3 import GithubArchives, verified_view, vector, REPO
from src.kb3_p1_shared_asof_features_v2 import when, need
from src.kb3_step16_m0_720_calibration import _gh_json, _gh_artifact_zip

SCHEMA = "kb3-v3-host-attested-original-builder-87-forward-v1"


def validate(artifact_id, token):
    need(str(artifact_id).isdigit() and bool(token), "GITHUB_ARTIFACT_TOKEN_REQUIRED")
    url = f"https://api.github.com/repos/{REPO}/actions/artifacts/{artifact_id}"
    meta = _gh_json(url, token)
    need(str(meta.get("id")) == str(artifact_id) and not meta.get("expired"),
         "SOURCE_ARTIFACT_NOT_HOSTED")
    need(meta.get("name") == "KB3_V3_NATIVE_87_FORWARD_SOURCE_UNENCRYPTED_PRIVATE",
         "WRONG_SOURCE_ARTIFACT_NAME")
    need(meta.get("archive_download_url") == url + "/zip", "UNTRUSTED_SOURCE_URL")
    raw = _gh_artifact_zip(url + "/zip", token)
    need(meta.get("digest") == "sha256:" + hashlib.sha256(raw).hexdigest(),
         "HOSTED_ZIP_HASH_MISMATCH")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names = z.namelist()
        need(len(names) == len(set(names)), "DUPLICATE_ZIP_MEMBER")
        def get(name):
            need(name in names, "MISSING_NATIVE_MEMBER")
            info = z.getinfo(name)
            need(0 < info.file_size <= 16 * 1024 * 1024,
                 "NATIVE_MEMBER_TOO_LARGE")
            return z.read(name)
        manifest = json.loads(get("bridge_manifest.json"))
        need(manifest["schema"] == "kb3-v3-native-github-forward-bridge-v1",
             "WRONG_NATIVE_BRIDGE_SCHEMA")
        need(manifest["source_count"] == 6 and
             manifest["target_count"] == len(manifest["targets"]),
             "NATIVE_BRIDGE_COUNTS_DRIFT")
        host_created = when(meta["created_at"])
        cutoff = when(manifest["cutoff_utc"])
        # Strict: host must be independently known BEFORE feature cutoff.
        need(host_created <= cutoff, "HOSTED_AFTER_EXACT_FEATURE_CUTOFF")
        source_index = {}
        for src in manifest["source_index"]:
            member, sha = src["member"], src["sha256"]
            need(hashlib.sha256(get(member)).hexdigest() == sha,
                 "NATIVE_SOURCE_MEMBER_HASH_DRIFT")
            source_index[member] = dict(artifact_id=str(artifact_id),
                                        member=member, sha256=sha)
        need(len(source_index) == 6, "DUPLICATE_SOURCE_MEMBERS")
        store = GithubArchives(token)
        counts = Counter()
        for target in manifest["targets"]:
            need(target["feature_count"] == 87 and
                 target["cutoff_utc"] == manifest["cutoff_utc"],
                 "FEATURE_CUTOFF_OR_COUNT_DRIFT")
            member = target["input_member"]
            input_bytes = get(member)
            need(hashlib.sha256(input_bytes).hexdigest() == target["input_sha256"],
                 "INPUT_MEMBER_HASH_DRIFT")
            inp = json.loads(input_bytes)
            need(inp["target"]["league"] == target["league"] and
                 str(inp["target"]["fixture_id"]) == str(target["fixture_id"]) and
                 inp["target"]["kickoff_utc"] == target["kickoff_utc"],
                 "TARGET_IDENTITY_DRIFT")
            needed = {m: source_index[m] for m in target["source_members"]}
            sha_index = {r["sha256"]: r for r in needed.values()}
            need(len(sha_index) == len(needed), "SOURCE_SHA_DUPLICATE")
            sample = dict(input=inp,
                          input_archive=dict(artifact_id=str(artifact_id),
                                             member=member,
                                             sha256=target["input_sha256"]),
                          source_archives=sha_index)
            # Reconstruct 87 values from independently attested raw native bytes
            # with original verified_view, never from cached M0 or surrogate.
            view = verified_view(sample, store, purpose="FORWARD")
            need(len(vector(view)) == 87, "V3_VECTOR_NOT_87")
            counts[target["league"]] += 1
    return dict(schema=SCHEMA, artifact_id=int(artifact_id),
                github_created_at_utc=meta["created_at"],
                cutoff_utc=manifest["cutoff_utc"],
                source_sha256_and_github_zip_verified=True,
                hosted_before_exact_feature_cutoff=True,
                native_source_members_verified=6,
                original_builder_v2_used=True,
                original_v3_verified_view_used=True,
                original_87_vector_verified=sum(counts.values()),
                country_counts=dict(sorted(counts.items())),
                first_provider_publication_certified=False,
                historical_pit_certified=False,
                eligible_for_future_forward_research=True,
                eligible_for_training=False,
                production_approved=False,
                model_fit_performed=False)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--artifact-id", required=True, type=int)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    report = validate(a.artifact_id, os.environ.get("GH_TOKEN", ""))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("x") as f:
        json.dump(report, f, sort_keys=True, indent=2)
        f.write("\n")
    print("V3_REAL_HOST_ATTESTED_ORIGINAL_BUILDER",
          report["original_87_vector_verified"],
          "LEAGUES", report["country_counts"],
          "FIT", False, "PRODUCTION", False)


if __name__ == "__main__":
    main()
