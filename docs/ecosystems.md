# Ecosystem detection

Safe Dependabot scans the checked-out repository for dependency manifests and maps them to the ecosystem identifiers supported by Dependabot.

The supported ecosystem IDs come from the same `SUPPORTED_ECOSYSTEMS` source of truth used by structural validation, and the test suite requires at least one detection fixture for every supported ecosystem.

## Detected manifests

| Manifest or signal | Ecosystem |
| --- | --- |
| `MODULE.bazel`, `WORKSPACE`, `WORKSPACE.bazel` | `bazel` |
| `package.json` with text-based `bun.lock` | `bun` |
| `Gemfile`, `*.gemspec` | `bundler` |
| `Cargo.toml` | `cargo` |
| `composer.json` | `composer` |
| `environment.yml`, `environment.yaml` | `conda` |
| `deno.json`, `deno.jsonc`, `deno.lock` | `deno` |
| `devcontainer.json`, `.devcontainer.json` | `devcontainers` |
| Dockerfile/Containerfile names; Kubernetes YAML with image references | `docker` |
| Docker Compose filenames such as `docker-compose.yml`, `compose.yaml`, overrides | `docker-compose` |
| `global.json` | `dotnet-sdk` |
| `elm.json` | `elm` |
| `.gitmodules` | `gitsubmodule` |
| `.github/workflows/*.yml`, `.github/workflows/*.yaml`, root `action.yml`/`action.yaml` | `github-actions` |
| `go.mod` | `gomod` |
| Gradle build/settings files, `gradle.lockfile`, `gradle/libs.versions.toml` | `gradle` |
| `Chart.yaml` | `helm` |
| `Manifest.toml`; `Project.toml` beside a manifest | `julia` |
| `pom.xml` | `maven` |
| `mix.exs` | `mix` |
| paired `flake.nix` + `flake.lock` | `nix` |
| `package.json` without a Bun lockfile | `npm` |
| .NET project files and `packages.config` | `nuget` |
| `*.tofu`, `terragrunt.hcl`; shared HCL lockfiles beside an OpenTofu signal | `opentofu` |
| `pyproject.toml`, `requirements*.txt`, `poetry.lock`, `Pipfile` | `pip` |
| `.pre-commit-config.yaml`, `.pre-commit-config.yml` | `pre-commit` |
| `pubspec.yaml` | `pub` |
| `rust-toolchain`, `rust-toolchain.toml` | `rust-toolchain` |
| `build.sbt` | `sbt` |
| `Package.swift` | `swift` |
| `*.tf`, `.terraform.lock.hcl` without an OpenTofu-specific signal | `terraform` |
| `pyproject.toml` + `uv.lock` | `uv` |
| `vcpkg.json` | `vcpkg` |

## Ambiguous manifests

Terraform and OpenTofu intentionally share `.tf` files and `.terraform.lock.hcl`. A filesystem-only detector cannot always distinguish a pure OpenTofu project that uses only Terraform-compatible `.tf` syntax.

Safe Dependabot therefore uses deterministic signals:

- `*.tofu` or `terragrunt.hcl` identifies `opentofu`;
- a shared `.terraform.lock.hcl` in the same directory follows that OpenTofu signal;
- otherwise plain `*.tf` and the shared lockfile are classified as `terraform`.

This avoids requiring both ecosystems for one HCL project while documenting the remaining ambiguity.

The legacy binary `bun.lockb` is intentionally not a supported Bun signal. GitHub currently supports the text-based `bun.lock` format.

## Coverage directories

Some Dependabot ecosystems store managed files below the directory configured in `dependabot.yml`:

- GitHub Actions workflows under `.github/workflows/` are covered by `directory: /`.
- `gradle/libs.versions.toml` is covered from the containing Gradle project directory.
- `.devcontainer/devcontainer.json` is covered from the containing project directory.

Safe Dependabot normalizes these cases before directory-level coverage validation.

## Ignored directories

Generated or environment-specific directories are skipped during detection, including:

```text
.git
.venv
venv
node_modules
vendor
target
build
dist
site
.tox
.nox
```

This prevents vendored or generated dependency files from creating false policy failures.

## Monorepos

Detection is recursive. If a repository contains both `Cargo.toml` and `package.json`, Safe Dependabot expects both `cargo` and `npm` coverage in `.github/dependabot.yml`.

Coverage is validated at the **manifest-directory level**. A repository with `/apps/api/package.json` and `/apps/web/package.json` will therefore fail if Dependabot covers only `/apps/api`.

Use `directories` when one ecosystem appears in several locations:

```yaml
updates:
  - package-ecosystem: npm
    directories:
      - "/apps/*"
    schedule:
      interval: weekly
```

Safe Dependabot treats `directory` as one exact manifest location and supports globbing only for `directories`, matching GitHub's configuration semantics. It also scopes coverage by `target-branch` when the checked-out branch and repository default branch are available from the GitHub Actions event.

If multiple blocks for the same ecosystem and effective target branch cover the same detected manifest directory, validation fails because GitHub requires those locations to be unique and non-overlapping.


## Detector exclusions and overrides

Automatic detection can be customized without disabling it globally.

`detection-ignore-paths` accepts newline-separated repository-relative globs and removes matching files before classification. `detection-overrides` accepts newline-separated `glob=ecosystem` rules and replaces automatic classification for matching paths. The first matching override wins.

These controls are useful for generated fixtures, archived subprojects, exported manifests, or intentionally ambiguous layouts. Applied exclusions and overrides are reported in action outputs and printed in the workflow log.

Normally ignored generated/environment directory names can be scanned with `include-ignored-directories: true`. This affects names such as `build`, `dist`, `vendor`, `target`, and virtual environments. `.git` remains excluded even in inclusive mode.
