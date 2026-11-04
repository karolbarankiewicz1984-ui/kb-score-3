-- R1 Codex schema only: adds attestations; never modifies existing forecasts.
CREATE TABLE IF NOT EXISTS m0_shadow_publication_proofs (
 forecast_id TEXT PRIMARY KEY REFERENCES m0_shadow_1x2_forecasts(forecast_id),
 forecast_sha256 TEXT NOT NULL,
 github_artifact_id TEXT NOT NULL,
 github_run_id TEXT NOT NULL,
 github_published_at_utc TEXT NOT NULL,
 archive_sha256 TEXT NOT NULL,
 audited_at_utc TEXT NOT NULL,
 proof_sha256 TEXT NOT NULL UNIQUE
);
CREATE TRIGGER IF NOT EXISTS m0_publication_no_update BEFORE UPDATE ON m0_shadow_publication_proofs
 BEGIN SELECT RAISE(ABORT,'M0_PUBLICATION_PROOF_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS m0_publication_no_delete BEFORE DELETE ON m0_shadow_publication_proofs
 BEGIN SELECT RAISE(ABORT,'M0_PUBLICATION_PROOF_IMMUTABLE'); END;
CREATE TABLE IF NOT EXISTS m0_shadow_calibration_proof_members (
 candidate_id TEXT NOT NULL REFERENCES m0_shadow_calibration_candidates(candidate_id),
 forecast_id TEXT NOT NULL REFERENCES m0_shadow_publication_proofs(forecast_id),
 sample_role TEXT NOT NULL CHECK(sample_role IN ('FIT','HOLDOUT')),
 PRIMARY KEY(candidate_id,forecast_id)
);
CREATE TRIGGER IF NOT EXISTS m0_cal_proof_no_update BEFORE UPDATE ON m0_shadow_calibration_proof_members
 BEGIN SELECT RAISE(ABORT,'M0_CALIBRATION_PROOF_MEMBERS_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS m0_cal_proof_no_delete BEFORE DELETE ON m0_shadow_calibration_proof_members
 BEGIN SELECT RAISE(ABORT,'M0_CALIBRATION_PROOF_MEMBERS_IMMUTABLE'); END;
