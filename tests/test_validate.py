"""Tests for the safe-dependabot policy validator."""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import Any

MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "validate.py"


def load_validator() -> ModuleType:
    """Load the validator module directly from source."""

    spec = spec_from_file_location("safe_dependabot_validate", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load validator module.")

    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = load_validator()


def safe_config() -> dict[str, Any]:
    """Return a valid conservative Dependabot configuration."""

    return {
        "version": 2,
        "updates": [
            {
                "package-ecosystem": "pip",
                "directory": "/",
                "schedule": {"interval": "weekly"},
                "open-pull-requests-limit": 5,
                "allow": [
                    {
                        "dependency-name": "*",
                        "update-types": [
                            "version-update:semver-minor",
                            "version-update:semver-patch",
                        ],
                    }
                ],
            },
            {
                "package-ecosystem": "github-actions",
                "directory": "/",
                "schedule": {"interval": "weekly"},
                "open-pull-requests-limit": 5,
                "allow": [
                    {
                        "dependency-name": "*",
                        "update-types": [
                            "version-update:semver-minor",
                            "version-update:semver-patch",
                        ],
                    }
                ],
            },
        ],
    }


def test_unknown_package_ecosystem_fails_structure_validation() -> None:
    """Typos in package-ecosystem should fail before policy evaluation."""

    config = safe_config()
    config["updates"][0]["package-ecosystem"] = "pyhton"

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert any("unsupported package-ecosystem 'pyhton'" in error for error in errors)


def test_directory_and_directories_are_mutually_exclusive() -> None:
    """An update block should choose exactly one location form."""

    config = safe_config()
    config["updates"][0]["directories"] = ["/", "/examples"]

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert any("either directory or directories, not both" in error for error in errors)


def test_directory_must_be_non_empty_string() -> None:
    """A malformed single directory should fail structural validation."""

    config = safe_config()
    config["updates"][0]["directory"] = ""

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert any("directory must be a non-empty string" in error for error in errors)


def test_directories_must_be_non_empty_string_list() -> None:
    """Every directories entry should be a non-empty string."""

    config = safe_config()
    config["updates"][0].pop("directory")
    config["updates"][0]["directories"] = ["/apps/api", ""]

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert any("directories[2] must be a non-empty string" in error for error in errors)


def test_directory_does_not_accept_globs() -> None:
    """Globbing belongs to directories, not directory."""

    config = safe_config()
    config["updates"][0]["directory"] = "/apps/*"

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert any("directory does not support globbing" in error for error in errors)


def test_github_actions_requires_root_directory() -> None:
    """GitHub Actions Dependabot updates are configured from repository root."""

    config = safe_config()
    config["updates"][1]["directory"] = "/.github/workflows"

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert any(
        "(github-actions) must use / as its manifest directory" in error
        for error in errors
    )


def test_invalid_dependency_group_identifier_fails() -> None:
    """Ordinary dependency groups should follow GitHub's identifier rules."""

    config = safe_config()
    config["updates"][0]["groups"] = {
        "123-invalid": {"patterns": ["*"]},
    }

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert any("has an invalid identifier" in error for error in errors)


def test_dependency_groups_must_be_mapping() -> None:
    """The groups option should reject unsupported container types."""

    config = safe_config()
    config["updates"][0]["groups"] = ["everything"]

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert any("groups must be a mapping" in error for error in errors)


def test_group_update_types_validate_supported_values() -> None:
    """Group update-types should use Dependabot's major/minor/patch values."""

    config = safe_config()
    config["updates"][0]["groups"] = {
        "safe-updates": {
            "patterns": ["*"],
            "update-types": ["semver-minor"],
        }
    }

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert any("containing only major, minor, or patch" in error for error in errors)


def test_safe_configuration_passes() -> None:
    """A conservative configuration should pass without warnings."""

    errors, warnings, count = validator.validate(
        safe_config(),
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert errors == []
    assert warnings == []
    assert count == 2


def test_major_updates_are_rejected_without_version_guard() -> None:
    """Missing semver-major version guards should fail policy validation."""

    config = safe_config()
    config["updates"][0]["allow"] = []

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert any("semver-major" in error for error in errors)


def test_security_safe_allow_guard_passes_without_warning() -> None:
    """Minor/patch allow rules should guard majors without touching security updates."""

    errors, warnings, _ = validator.validate(
        safe_config(),
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert errors == []
    assert not any("security remediation" in warning for warning in warnings)


def test_legacy_major_ignore_is_accepted_with_security_warning() -> None:
    """Legacy wildcard major ignores remain compatible but should warn."""

    config = safe_config()
    config["updates"][0].pop("allow")
    config["updates"][0]["ignore"] = [
        {
            "dependency-name": "*",
            "update-types": ["version-update:semver-major"],
        }
    ]

    errors, warnings, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert errors == []
    assert any("security remediation" in warning for warning in warnings)


def test_valid_multi_ecosystem_group_passes() -> None:
    """Grouped update entries should inherit cadence from a valid top-level group."""

    config = safe_config()
    config["multi-ecosystem-groups"] = {
        "runtime": {
            "schedule": {"interval": "weekly"},
        }
    }
    config["updates"][0].pop("schedule")
    config["updates"][0].pop("open-pull-requests-limit")
    config["updates"][0]["multi-ecosystem-group"] = "runtime"
    config["updates"][0]["patterns"] = ["*"]

    errors, warnings, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert errors == []
    assert not any(
        "updates[1] (pip) does not set open-pull-requests-limit" in warning
        for warning in warnings
    )


def test_multi_ecosystem_group_reference_must_exist() -> None:
    """Grouped update entries must reference a defined top-level group."""

    config = safe_config()
    config["updates"][0].pop("schedule")
    config["updates"][0]["multi-ecosystem-group"] = "missing"
    config["updates"][0]["patterns"] = ["*"]

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert any("undefined multi-ecosystem-group 'missing'" in error for error in errors)


def test_multi_ecosystem_group_requires_schedule() -> None:
    """Top-level groups must define their own schedule."""

    config = safe_config()
    config["multi-ecosystem-groups"] = {"runtime": {}}
    config["updates"][0].pop("schedule")
    config["updates"][0]["multi-ecosystem-group"] = "runtime"
    config["updates"][0]["patterns"] = ["*"]

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert any(
        "multi-ecosystem-groups.runtime must define a schedule" in error
        for error in errors
    )


def test_weekly_schedule_accepts_day_time_and_timezone() -> None:
    """A fully specified weekly schedule should pass validation."""

    config = safe_config()
    config["updates"][0]["schedule"] = {
        "interval": "weekly",
        "day": "tuesday",
        "time": "02:00",
        "timezone": "Europe/Lisbon",
    }

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert errors == []


def test_cron_schedule_requires_cronjob() -> None:
    """Cron intervals must provide a cronjob expression."""

    config = safe_config()
    config["updates"][0]["schedule"] = {"interval": "cron"}

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert any(
        "interval 'cron' requires a non-empty cronjob" in error
        for error in errors
    )


def test_valid_cron_schedule_passes() -> None:
    """A cron interval with an expression should pass."""

    config = safe_config()
    config["updates"][0]["schedule"] = {
        "interval": "cron",
        "cronjob": "0 9 * * *",
    }

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert errors == []


def test_cronjob_is_rejected_for_non_cron_interval() -> None:
    """A cronjob field should not silently apply to weekly schedules."""

    config = safe_config()
    config["updates"][0]["schedule"] = {
        "interval": "weekly",
        "cronjob": "0 9 * * *",
    }

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert any(
        "cronjob is only valid with interval 'cron'" in error
        for error in errors
    )


def test_day_is_rejected_for_non_weekly_interval() -> None:
    """The day field is only meaningful for weekly schedules."""

    config = safe_config()
    config["updates"][0]["schedule"] = {
        "interval": "daily",
        "day": "monday",
    }

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert any(
        "day is only valid with interval 'weekly'" in error
        for error in errors
    )


def test_schedule_time_uses_24_hour_hh_mm() -> None:
    """Invalid schedule clock values should fail."""

    config = safe_config()
    config["updates"][0]["schedule"] = {
        "interval": "weekly",
        "time": "24:00",
    }

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert any("24-hour HH:MM format" in error for error in errors)


def test_schedule_timezone_must_be_known_iana_zone() -> None:
    """Unknown timezone identifiers should fail."""

    config = safe_config()
    config["updates"][0]["schedule"] = {
        "interval": "weekly",
        "time": "09:00",
        "timezone": "Mars/Olympus",
    }

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert any("is not a known IANA timezone" in error for error in errors)


def test_schedule_timezone_requires_time() -> None:
    """Timezone without a time value is not a meaningful schedule."""

    config = safe_config()
    config["updates"][0]["schedule"] = {
        "interval": "weekly",
        "timezone": "UTC",
    }

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert any("timezone requires schedule time" in error for error in errors)


def test_multi_ecosystem_group_uses_same_cron_validation() -> None:
    """Top-level multi-ecosystem group schedules should share validation."""

    config = safe_config()
    config["multi-ecosystem-groups"] = {
        "runtime": {"schedule": {"interval": "cron"}}
    }
    config["updates"][0].pop("schedule")
    config["updates"][0]["multi-ecosystem-group"] = "runtime"
    config["updates"][0]["patterns"] = ["*"]

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert any(
        "multi-ecosystem-groups.runtime schedule interval 'cron' "
        "requires a non-empty cronjob" in error
        for error in errors
    )


def test_multi_ecosystem_group_schedule_interval_is_validated() -> None:
    """Top-level group schedules should use supported intervals."""

    config = safe_config()
    config["multi-ecosystem-groups"] = {
        "runtime": {"schedule": {"interval": "fortnightly"}}
    }
    config["updates"][0].pop("schedule")
    config["updates"][0]["multi-ecosystem-group"] = "runtime"
    config["updates"][0]["patterns"] = ["*"]

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert any(
        "unsupported schedule interval 'fortnightly'" in error
        for error in errors
    )


def test_multi_ecosystem_group_member_requires_patterns() -> None:
    """Every grouped ecosystem entry must define dependency patterns."""

    config = safe_config()
    config["multi-ecosystem-groups"] = {
        "runtime": {"schedule": {"interval": "weekly"}}
    }
    config["updates"][0].pop("schedule")
    config["updates"][0]["multi-ecosystem-group"] = "runtime"

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert any("must define a non-empty patterns list" in error for error in errors)


def test_omitted_pull_request_limit_uses_github_default() -> None:
    """Omitted standalone limits should model GitHub's default of five."""

    config = safe_config()
    config["updates"][0].pop("open-pull-requests-limit")

    errors, warnings, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert errors == []
    assert any("GitHub's default of 5 applies" in warning for warning in warnings)


def test_omitted_pull_request_limit_can_exceed_policy_maximum() -> None:
    """A stricter policy must reject the effective GitHub default."""

    config = safe_config()
    config["updates"][0].pop("open-pull-requests-limit")

    errors, _, _ = validator.validate(
        config,
        max_open_prs=3,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert any(
        "GitHub's default of 5 exceeds the policy maximum of 3" in error
        for error in errors
    )


def test_zero_pull_request_limit_disables_version_updates() -> None:
    """Security-only blocks should not need a routine major-version guard."""

    config = safe_config()
    config["updates"][0]["open-pull-requests-limit"] = 0
    config["updates"][0].pop("allow")

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert errors == []


def test_zero_limit_still_warns_about_legacy_security_ignore() -> None:
    """A legacy ignore remains risky even when version updates are disabled."""

    config = safe_config()
    config["updates"][0]["open-pull-requests-limit"] = 0
    config["updates"][0].pop("allow")
    config["updates"][0]["ignore"] = [
        {
            "dependency-name": "*",
            "update-types": ["version-update:semver-major"],
        }
    ]

    errors, warnings, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert errors == []
    assert any("security remediation" in warning for warning in warnings)


def test_negative_pull_request_limit_is_rejected() -> None:
    """Negative limits are not valid Dependabot behavior."""

    config = safe_config()
    config["updates"][0]["open-pull-requests-limit"] = -1

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert any("must be zero or greater" in error for error in errors)


def test_grouped_update_can_omit_standalone_pull_request_limit() -> None:
    """Grouped members should not inherit the standalone default-five warning."""

    config = safe_config()
    config["multi-ecosystem-groups"] = {
        "runtime": {"schedule": {"interval": "weekly"}}
    }
    config["updates"][0].pop("schedule")
    config["updates"][0].pop("open-pull-requests-limit")
    config["updates"][0]["multi-ecosystem-group"] = "runtime"
    config["updates"][0]["patterns"] = ["*"]
    config["updates"][1]["open-pull-requests-limit"] = 3

    errors, warnings, _ = validator.validate(
        config,
        max_open_prs=3,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert errors == []
    assert not any("GitHub's default of 5" in warning for warning in warnings)


def test_pull_request_limit_is_enforced() -> None:
    """Update blocks above the configured PR limit should fail."""

    config = safe_config()
    config["updates"][0]["open-pull-requests-limit"] = 10

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert any("policy maximum is 5" in error for error in errors)


def test_broad_groups_warn_by_default() -> None:
    """Groups matching all dependencies should warn by default."""

    config = safe_config()
    config["updates"][0]["groups"] = {
        "everything": {"patterns": ["*"]},
    }

    errors, warnings, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert errors == []
    assert any("matches all dependency names" in warning for warning in warnings)


def test_wildcard_group_with_exclusions_is_not_broad() -> None:
    """Exclude patterns materially narrow a wildcard group."""

    config = safe_config()
    config["updates"][0]["groups"] = {
        "safe": {
            "patterns": ["*"],
            "exclude-patterns": ["django"],
        }
    }

    errors, warnings, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert errors == []
    assert not any("matches all dependency names" in warning for warning in warnings)


def test_wildcard_group_with_dependency_type_is_not_broad() -> None:
    """Development-only wildcard groups should not be called fully broad."""

    config = safe_config()
    config["updates"][0]["groups"] = {
        "dev": {
            "patterns": ["*"],
            "dependency-type": "development",
        }
    }

    errors, warnings, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert errors == []
    assert not any("matches all dependency names" in warning for warning in warnings)


def test_wildcard_group_with_update_types_is_not_broad() -> None:
    """Patch/minor-only wildcard groups are meaningfully constrained."""

    config = safe_config()
    config["updates"][0]["groups"] = {
        "safe": {
            "patterns": ["*"],
            "update-types": ["minor", "patch"],
        }
    }

    errors, warnings, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert errors == []
    assert not any("matches all dependency names" in warning for warning in warnings)


def test_wildcard_security_update_group_is_not_broad() -> None:
    """Security-only wildcard groups should not trigger the broad warning."""

    config = safe_config()
    config["updates"][0]["groups"] = {
        "security": {
            "patterns": ["*"],
            "applies-to": "security-updates",
        }
    }

    errors, warnings, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert errors == []
    assert not any("matches all dependency names" in warning for warning in warnings)


def test_explicit_version_scope_remains_broad_without_other_constraints() -> None:
    """Explicit version-updates is equivalent to the default broad scope."""

    config = safe_config()
    config["updates"][0]["groups"] = {
        "everything": {
            "patterns": ["*"],
            "applies-to": "version-updates",
        }
    }

    errors, warnings, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert errors == []
    assert any("matches all dependency names" in warning for warning in warnings)


def test_all_semver_update_types_remain_broad() -> None:
    """Listing every SemVer level should not disguise an unconstrained group."""

    config = safe_config()
    config["updates"][0]["groups"] = {
        "everything": {
            "patterns": ["*"],
            "update-types": ["major", "minor", "patch"],
        }
    }

    errors, warnings, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert errors == []
    assert any("matches all dependency names" in warning for warning in warnings)


def test_broad_groups_can_be_made_fatal() -> None:
    """Users may promote broad grouping warnings to policy errors."""

    config = safe_config()
    config["updates"][0]["groups"] = {
        "everything": {"patterns": ["*"]},
    }

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=True,
    )

    assert any("matches all dependency names" in error for error in errors)


def test_github_actions_block_can_be_required() -> None:
    """The policy should detect repositories missing action updates."""

    config = safe_config()
    config["updates"] = [config["updates"][0]]

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert "A github-actions update block is required by policy." in errors


def test_every_supported_ecosystem_has_a_detection_fixture(tmp_path: Path) -> None:
    """The detector should have at least one reliable signal per supported ecosystem."""

    fixtures: dict[str, list[tuple[str, str]]] = {
        "bazel": [("bazel/MODULE.bazel", "")],
        "bun": [
            ("bun/package.json", '{"name":"bun-demo"}'),
            ("bun/bun.lock", ""),
        ],
        "bundler": [("ruby/Gemfile", 'gem "rake"')],
        "cargo": [("rust/Cargo.toml", "[package]\nname='demo'\nversion='0.1.0'\n")],
        "composer": [("php/composer.json", "{}")],
        "conda": [("conda/environment.yml", "dependencies:\n  - python\n")],
        "deno": [("deno/deno.json", "{}")],
        "devcontainers": [(".devcontainer/devcontainer.json", "{}")],
        "docker": [("container/Dockerfile", "FROM python:3.12\n")],
        "docker-compose": [("compose/docker-compose.yml", "services: {}\n")],
        "dotnet-sdk": [("dotnet/global.json", "{}")],
        "elm": [("elm/elm.json", "{}")],
        "gitsubmodule": [(".gitmodules", "")],
        "github-actions": [(".github/workflows/ci.yml", "name: CI\n")],
        "gomod": [("go/go.mod", "module example.com/demo\n")],
        "gradle": [("gradle-project/gradle/libs.versions.toml", "[versions]\n")],
        "helm": [("helm/Chart.yaml", "apiVersion: v2\nname: demo\n")],
        "julia": [("julia/Manifest.toml", "")],
        "maven": [("maven/pom.xml", "<project />\n")],
        "mix": [("elixir/mix.exs", "")],
        "nix": [
            ("nix/flake.nix", "{}\n"),
            ("nix/flake.lock", "{}\n"),
        ],
        "npm": [("node/package.json", '{"name":"node-demo"}')],
        "nuget": [("nuget/app.csproj", "<Project />\n")],
        "opentofu": [("tofu/main.tofu", 'terraform {}\n')],
        "pip": [("python/requirements.txt", "pyyaml==6.0.2\n")],
        "pre-commit": [("hooks/.pre-commit-config.yaml", "repos: []\n")],
        "pub": [("dart/pubspec.yaml", "name: demo\n")],
        "rust-toolchain": [
            (
                "toolchain/rust-toolchain.toml",
                '[toolchain]\nchannel = "1.90"\n',
            )
        ],
        "sbt": [("scala/build.sbt", 'scalaVersion := "3.7.0"\n')],
        "swift": [("swift/Package.swift", "// swift-tools-version: 6.0\n")],
        "terraform": [("terraform/main.tf", 'terraform {}\n')],
        "uv": [
            ("uv/pyproject.toml", "[project]\nname='demo'\n"),
            ("uv/uv.lock", "version = 1\n"),
        ],
        "vcpkg": [("cpp/vcpkg.json", "{}")],
    }

    assert set(fixtures) == set(validator.SUPPORTED_ECOSYSTEMS)

    for files in fixtures.values():
        for relative_path, content in files:
            path = tmp_path / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    detected = validator.detect_ecosystems(tmp_path)

    assert set(detected) == set(validator.SUPPORTED_ECOSYSTEMS)


def test_github_actions_workflow_maps_to_repository_root() -> None:
    """GitHub Actions workflows are configured with directory /."""

    assert (
        validator.manifest_directory(
            ".github/workflows/ci.yml",
            "github-actions",
        )
        == "/"
    )


def test_gradle_version_catalog_maps_to_project_root() -> None:
    """A Gradle catalog under gradle/ belongs to the containing project."""

    assert (
        validator.manifest_directory(
            "services/api/gradle/libs.versions.toml",
            "gradle",
        )
        == "/services/api"
    )


def test_devcontainer_maps_to_containing_project_root() -> None:
    """A .devcontainer manifest belongs to its containing project."""

    assert (
        validator.manifest_directory(
            "services/api/.devcontainer/devcontainer.json",
            "devcontainers",
        )
        == "/services/api"
    )


def test_terraform_files_are_detected_without_lockfile(tmp_path: Path) -> None:
    """Terraform should not require a committed lockfile for detection."""

    path = tmp_path / "infra" / "main.tf"
    path.parent.mkdir(parents=True)
    path.write_text('terraform {}\n', encoding="utf-8")

    detected = validator.detect_ecosystems(tmp_path)

    assert detected == {"terraform": ["infra/main.tf"]}


def test_opentofu_signal_claims_shared_hcl_lockfile(tmp_path: Path) -> None:
    """An OpenTofu-specific manifest should disambiguate the shared lockfile."""

    directory = tmp_path / "infra"
    directory.mkdir()
    (directory / "main.tofu").write_text('terraform {}\n', encoding="utf-8")
    (directory / ".terraform.lock.hcl").write_text("", encoding="utf-8")

    detected = validator.detect_ecosystems(tmp_path)

    assert set(detected) == {"opentofu"}
    assert sorted(detected["opentofu"]) == [
        "infra/.terraform.lock.hcl",
        "infra/main.tofu",
    ]


def test_kubernetes_image_manifest_detects_docker(tmp_path: Path) -> None:
    """Docker ecosystem should detect supported Kubernetes image references."""

    manifest = tmp_path / "k8s" / "deployment.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        "apiVersion: apps/v1\n"
        "kind: Deployment\n"
        "spec:\n"
        "  template:\n"
        "    spec:\n"
        "      containers:\n"
        "        - image: nginx:1.29\n",
        encoding="utf-8",
    )

    detected = validator.detect_ecosystems(tmp_path)

    assert detected == {"docker": ["k8s/deployment.yaml"]}


def test_detects_multiple_ecosystems(tmp_path: Path) -> None:
    """Repository manifests should map to the matching Dependabot ecosystems."""

    (tmp_path / "Cargo.toml").write_text(
        "[package]\nname='demo'\nversion='0.1.0'\n",
        encoding="utf-8",
    )
    (tmp_path / "package.json").write_text('{"name":"demo"}', encoding="utf-8")
    (tmp_path / "go.mod").write_text("module example.com/demo\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='demo'\n",
        encoding="utf-8",
    )

    detected = validator.detect_ecosystems(tmp_path)

    assert set(detected) == {"cargo", "gomod", "npm", "pip"}


def test_uv_lock_selects_uv_ecosystem(tmp_path: Path) -> None:
    """A pyproject with uv.lock should be treated as a uv project."""

    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='demo'\n",
        encoding="utf-8",
    )
    (tmp_path / "uv.lock").write_text("version = 1\n", encoding="utf-8")

    detected = validator.detect_ecosystems(tmp_path)

    assert set(detected) == {"uv"}


def test_uv_lock_owns_exported_requirements_file(tmp_path: Path) -> None:
    """A requirements export beside uv.lock should not create a pip ecosystem."""

    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='demo'\n",
        encoding="utf-8",
    )
    (tmp_path / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text(
        "# Generated from uv.lock. Do not edit.\nexample==1.0\n",
        encoding="utf-8",
    )

    detected = validator.detect_ecosystems(tmp_path)

    assert set(detected) == {"uv"}
    assert sorted(detected["uv"]) == [
        "pyproject.toml",
        "requirements.txt",
        "uv.lock",
    ]




def test_uncovered_manifest_directory_fails_validation() -> None:
    """Every detected manifest directory must have matching coverage."""

    config = safe_config()
    config["updates"][0]["directory"] = "/apps/api"

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
        detected_ecosystems={
            "pip": [
                "apps/api/pyproject.toml",
                "apps/web/pyproject.toml",
            ]
        },
    )

    assert any(
        "/apps/web" in error and "directory/directories" in error
        for error in errors
    )


def test_directories_glob_covers_monorepo_manifests() -> None:
    """The directories key should support anchored wildcard coverage."""

    config = safe_config()
    config["updates"][0].pop("directory")
    config["updates"][0]["directories"] = ["/apps/*"]

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
        detected_ecosystems={
            "pip": [
                "apps/api/pyproject.toml",
                "apps/web/pyproject.toml",
            ]
        },
    )

    assert errors == []


def test_recursive_directories_glob_covers_root_and_nested_manifests() -> None:
    """GitHub's **/* directory glob should cover current and nested directories."""

    config = safe_config()
    config["updates"][0].pop("directory")
    config["updates"][0]["directories"] = ["**/*"]

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
        detected_ecosystems={
            "pip": [
                "pyproject.toml",
                "apps/api/pyproject.toml",
                "apps/api/internal/requirements.txt",
            ]
        },
    )

    assert errors == []


def test_overlapping_blocks_for_same_target_branch_fail() -> None:
    """Two blocks must not cover the same manifest directory on one target branch."""

    config = safe_config()
    config["updates"][0]["directory"] = "/apps/api"
    config["updates"].insert(
        1,
        {
            "package-ecosystem": "pip",
            "directories": ["/apps/*"],
            "schedule": {"interval": "weekly"},
            "open-pull-requests-limit": 5,
            "allow": [
                {
                    "dependency-name": "*",
                    "update-types": [
                        "version-update:semver-minor",
                        "version-update:semver-patch",
                    ],
                }
            ],
        },
    )

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
        detected_ecosystems={"pip": ["apps/api/pyproject.toml"]},
        current_branch="main",
        default_branch="main",
    )

    assert any(
        "overlapping pip coverage" in error
        and "updates[1]" in error
        and "updates[2]" in error
        for error in errors
    )


def test_target_branch_block_does_not_cover_default_branch_checkout() -> None:
    """Coverage for another target branch must not satisfy the current checkout."""

    config = safe_config()
    config["updates"][0]["directory"] = "/apps/api"
    config["updates"][0]["target-branch"] = "develop"

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
        detected_ecosystems={"pip": ["apps/api/pyproject.toml"]},
        current_branch="main",
        default_branch="main",
    )

    assert any("branch 'main'" in error and "/apps/api" in error for error in errors)


def test_target_branch_block_covers_matching_checkout() -> None:
    """Explicit target-branch coverage should apply on that branch checkout."""

    config = safe_config()
    config["updates"][0]["directory"] = "/apps/api"
    config["updates"][0]["target-branch"] = "develop"

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
        detected_ecosystems={"pip": ["apps/api/pyproject.toml"]},
        current_branch="develop",
        default_branch="main",
    )

    assert errors == []


def test_excluded_manifest_does_not_count_as_covered() -> None:
    """An excluded detected manifest should not satisfy directory coverage."""

    config = safe_config()
    config["updates"][0]["exclude-paths"] = ["pyproject.toml"]

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
        detected_ecosystems={"pip": ["pyproject.toml"]},
    )

    assert any("no matching Dependabot" in error for error in errors)


def test_missing_detected_ecosystem_fails_validation() -> None:
    """Detected manifests must have corresponding Dependabot coverage."""

    config = safe_config()

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
        detected_ecosystems={"cargo": ["Cargo.toml"], "pip": ["pyproject.toml"]},
    )

    assert any("Detected cargo manifest" in error for error in errors)


def test_detected_ecosystems_pass_when_configured() -> None:
    """Detected manifests should pass when every ecosystem is configured."""

    config = safe_config()
    config["updates"].append(
        {
            "package-ecosystem": "cargo",
            "directory": "/",
            "schedule": {"interval": "weekly"},
            "open-pull-requests-limit": 5,
            "ignore": [
                {
                    "dependency-name": "*",
                    "update-types": ["version-update:semver-major"],
                }
            ],
        }
    )

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
        detected_ecosystems={"cargo": ["Cargo.toml"], "pip": ["pyproject.toml"]},
    )

    assert errors == []
