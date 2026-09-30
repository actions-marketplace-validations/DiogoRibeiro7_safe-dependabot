# Changelog

All notable changes to Safe Dependabot will be documented in this file.

The project follows semantic versioning.

## Unreleased

## 1.1.1 - 2026-09-30

### Fixed

- Treat GitHub release tag checkouts as unscoped repository snapshots instead of interpreting the tag name as a Dependabot target branch.
- Allow release self-validation to match normal default-branch Dependabot update blocks when running from tags such as `v1.1.0`.

## 1.1.0 - 2026-09-30

### Added

- Directory-level ecosystem coverage validation for monorepos, including `directories` glob handling, target-branch scoping, and overlapping coverage detection.
- First-class validation for Dependabot multi-ecosystem groups.
- Structural validation for supported package ecosystems, location fields, and dependency-group configuration.
- Complete ecosystem detection coverage for the current supported Dependabot ecosystem set.
- Targeted detector controls for ignored path globs, explicit ecosystem overrides, and optional scanning of normally ignored directories.
- Optional `pre-one-risk` policy with `off`, `warn`, and `fail` modes for exact or resolved direct dependencies on pre-1.0 versions.

### Changed

- Recommended major-version policy now prefers security-safe `allow.update-types` guards over wildcard major-version `ignore` rules.
- Pull-request-limit validation now models GitHub's effective default and treats `open-pull-requests-limit: 0` as version updates disabled.
- Broad dependency-group warnings now account for exclusions, dependency type, update type, and security-update scope.
- Schedule validation now checks weekly day values, 24-hour time format, IANA timezones, and cron requirements.

### Fixed

- Prevent wildcard major-version policy from unintentionally suppressing security remediations.
- Avoid false ecosystem coverage passes when only one manifest directory is configured.
- Stop treating legacy `bun.lockb` as supported Bun coverage.
- Detect Terraform projects without requiring a committed lockfile and disambiguate OpenTofu when explicit signals are present.
- Correct Docker Compose and Kubernetes image manifest detection.

## 1.0.1 - 2026-09-27

### Fixed

- Treat exported `requirements*.txt` files beside `uv.lock` as part of the uv-managed project, avoiding false pip ecosystem failures.

## 1.0.0 - 2026-09-26

### Added

- Conservative Dependabot policy validation.
- Ecosystem-aware manifest detection.
- GitHub Actions, Python, Rust, Node, Go, Ruby, PHP, Java, .NET, Terraform and additional ecosystem coverage.
- Configurable policy inputs and action outputs.
- MkDocs documentation with GitHub Pages deployment.
- Self-validation against the repository's own Dependabot configuration.
- Repository governance files and contribution templates.
- Automated semantic release workflow with a moving stable major tag.

### Changed

- Repository documentation and action metadata describe ecosystem detection consistently.
