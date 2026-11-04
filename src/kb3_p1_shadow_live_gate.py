"""Explicit OFF-by-default opt-in for research-only forward CatBoost shadow.

Validates a single reviewed artifact's exact manifest and CatBoost binary
before any live provider API calls. Cannot approve historical PIT or production.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from src.kb3_step16_m0_720_eight_forward import ROOT
from src.kb3_p1_prospective_shadow_six_v1 import ShadowSix, ShadowSafetyError

PIN_FILE=ROOT/"config/kb3_shadow_six_pinned_research_model.json"
ENV_NAME="KB3_SHADOW_SIX_ENABLED"
MODEL_DIR_ENV="KB3_SHADOW_SIX_MODEL_DIR"
PIN_SCHEMA="kb3-shadow-six-research-model-pin-v1"


def opt_in_enabled(environ=None):
    environ=os.environ if environ is None else environ
    value=environ.get(ENV_NAME,"").lower().strip()
    if value in ("","false","0"):
        return False
    if value in ("true","1"):
        return True
    raise ShadowSafetyError("SHADOW_SWITCH_INVALID_MUST_BE_EXPLICIT_BOOLEAN")


def pinned_model_details(pin_path=PIN_FILE):
    pin=json.loads(Path(pin_path).read_text())
    if not (
        pin.get("schema")==PIN_SCHEMA
        and pin.get("artifact_id")==13366883765
        and pin.get("artifact_run_id")==41922809252
        and pin.get("artifact_name")==
            "KB3_CATBOOST_SIX_FORWARD_COMPATIBLE_RESEARCH_NOT_LIVE"
        and pin.get("model_version")=="KB3_CATBOOST_SHADOW_LAST5_GOALS_6_RESEARCH_V1"
        and pin.get("model_sha256")==
            "58c5a7fc35afe942893a25b96233689d1f7814ec8a93ed689a7b46f553dbbbc5"
        and pin.get("manifest_sha256")==
            "9a1b2ce07d11aa369066de712469470f862836a5ba5d3e817402589e65fc8eca"
        and pin.get("production_approved") is False
        and pin.get("enabled_by_default") is False
        and pin.get("historical_native_pit_certified") is False
        and pin.get("no_new_provider_calls") is True
        and pin.get("durable_repo_relative_dir")==
            "assets/research/kb3_shadow_six_v1"
        and pin.get("durable_mirror_workflow_run_id")==41929594196
        and pin.get("durable_source_verified_model_sha256")==
            pin.get("model_sha256")
    ):
        raise ShadowSafetyError("SHADOW_PIN_IMMUTABLE_POLICY_DRIFT")
    return pin


def load_opted_shadow(*,clock=None,environ=None,pin_path=PIN_FILE):
    """Return None unless explicitly enabled. If enabled, fail closed on bytes."""
    if not opt_in_enabled(environ):
        return None
    environ=os.environ if environ is None else environ
    pin=pinned_model_details(pin_path)
    folder=environ.get(MODEL_DIR_ENV)
    if not folder:
        raise ShadowSafetyError("SHADOW_SELECTED_MODEL_DIRECTORY_NOT_CONFIGURED")
    root=Path(folder)
    binary=root/pin["model_filename"]
    manifest_path=root/pin["manifest_filename"]
    if not (binary.is_file() and manifest_path.is_file()):
        raise ShadowSafetyError("SHADOW_SELECTED_ARTIFACT_MISSING")
    if hashlib.sha256(binary.read_bytes()).hexdigest()!=pin["model_sha256"]:
        raise ShadowSafetyError("SHADOW_RESEARCH_BINARY_PIN_MISMATCH")
    manifest=json.loads(manifest_path.read_text())
    if (manifest.get("manifest_sha256")!=pin["manifest_sha256"]
            or manifest.get("model_binary_sha256")!=pin["model_sha256"]):
        raise ShadowSafetyError("SHADOW_MANIFEST_PIN_MISMATCH")
    instance=ShadowSix(manifest_file=manifest_path,model_file=binary,
                       clock=clock)
    if instance.model_sha!=pin["model_sha256"]:
        raise ShadowSafetyError("SHADOW_LOADED_MODEL_SHA_DRIFT")
    return instance
