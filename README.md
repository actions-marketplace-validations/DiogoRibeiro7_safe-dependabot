# safe-dependabot

A GitHub Action that validates `.github/dependabot.yml` against a conservative dependency-update policy.

Full documentation: https://diogoribeiro7.github.io/safe-dependabot/

The default policy is intentionally simple:

- require Dependabot configuration version 2 and validate core configuration structure;
- require a GitHub Actions update block;
- require routine semantic-versioning major version updates to be blocked without suppressing security remediation;
- allow at most five open Dependabot pull requests per update block;
- detect dependency manifests and require matching Dependabot ecosystem **and manifest-directory** coverage;
- warn when a dependency group matches every dependency, because broad groups can make CI failures harder to isolate;
- validate multi-ecosystem group references, group schedules, and required member patterns.

## Usage

```yaml
name: Dependabot policy

on:
  pull_request:
    paths:
      - ".github/dependabot.yml"
  push:
    branches:
      - main
    paths:
      - ".github/dependabot.yml"

permissions:
  contents: read

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: DiogoRibeiro7/safe-dependabot@v1
```

## Configuration

```yaml
- uses: DiogoRibeiro7/safe-dependabot@v1
  with:
    max-open-prs: 5
    require-major-ignore: true
    require-github-actions: true
    fail-on-broad-groups: false
    detect-ecosystems: true
```

| Input | Default | Purpose |
| --- | --- | --- |
| `config-path` | `.github/dependabot.yml` | Dependabot configuration to validate |
| `max-open-prs` | `5` | Maximum effective open version-update PR limit for standalone blocks |
| `require-major-ignore` | `true` | Require a guard against routine SemVer-major version updates; security-safe `allow.update-types` is preferred and legacy wildcard `ignore` rules warn |
| `require-github-actions` | `true` | Require Dependabot coverage for GitHub Actions |
| `fail-on-broad-groups` | `false` | Turn wildcard dependency-group warnings into failures |
| `detect-ecosystems` | `true` | Detect repository manifests and require matching ecosystem and directory/directories coverage |

The action exposes `update-blocks`, the number of Dependabot update blocks that were validated, and `detected-ecosystems`, a comma-separated list of ecosystems found from repository manifests.

## Ecosystem detection

Safe Dependabot detects the full current set of supported Dependabot ecosystem IDs and checks that each detected manifest location is covered. Examples include:

| Manifest | Dependabot ecosystem |
| --- | --- |
| `pyproject.toml`, `requirements*.txt`, `poetry.lock` | `pip` |
| `pyproject.toml` + `uv.lock` | `uv` |
| `Cargo.toml` | `cargo` |
| `package.json` | `npm` |
| `package.json` + Bun lockfile | `bun` |
| `go.mod` | `gomod` |
| `Gemfile`, `*.gemspec` | `bundler` |
| `composer.json` | `composer` |
| `pom.xml` | `maven` |
| Gradle build files | `gradle` |
| `mix.exs` | `mix` |
| `pubspec.yaml` | `pub` |
| `Package.swift` | `swift` |
| .NET project files | `nuget` |
| `global.json` | `dotnet-sdk` |
| `.terraform.lock.hcl` | `terraform` |
| `.pre-commit-config.yaml` | `pre-commit` |
| `environment.yml` | `conda` |
| `devcontainer.json` | `devcontainers` |
| Dockerfile/Containerfile | `docker` |
| `docker-compose.yml`, `compose.yaml` | `docker-compose` |
| `Chart.yaml` | `helm` |
| `.gitmodules` | `gitsubmodule` |
| `flake.nix` + `flake.lock` | `nix` |
| `*.tofu`, `terragrunt.hcl` | `opentofu` |
| `rust-toolchain.toml` | `rust-toolchain` |
| `build.sbt` | `sbt` |

Generated dependency directories such as `node_modules`, `vendor`, `target`, virtual environments, and build output are ignored.

For monorepos, coverage is checked per manifest directory rather than only per ecosystem. The validator understands exact `directory` entries, glob-capable `directories`, explicit `target-branch` scoping, and reports overlapping blocks for the same ecosystem/target branch when they cover the same detected manifest location.

## Recommended Dependabot baseline

```yaml
version: 2

updates:
  - package-ecosystem: pip
    directory: /
    schedule:
      interval: weekly
    open-pull-requests-limit: 5
    allow:
      - dependency-name: "*"
        update-types:
          - version-update:semver-minor
          - version-update:semver-patch

  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
    open-pull-requests-limit: 5
    allow:
      - dependency-name: "*"
        update-types:
          - version-update:semver-minor
          - version-update:semver-patch
```

GitHub documents that `allow.update-types` affects version updates only, so the recommended minor/patch allow rule does not suppress security updates. Legacy wildcard major `ignore` rules remain accepted for v1 compatibility but produce a warning because `ignore` can also filter security updates. This action validates configuration; it does not merge, approve, or modify dependency pull requests.

## Local development

Requires Python 3.12 or newer.

```bash
python -m pip install -e ".[dev]"
ruff check .
mypy
pytest
```

## License

MIT.
