# Configuration

Safe Dependabot exposes a small set of inputs so repositories can tighten or relax the default policy without forking the action.

## Inputs

| Input | Default | Description |
| --- | --- | --- |
| `config-path` | `.github/dependabot.yml` | Path to the Dependabot configuration file. |
| `max-open-prs` | `5` | Maximum effective open version-update PR limit for standalone update blocks. |
| `require-major-ignore` | `true` | Require routine SemVer-major version updates to be restricted unless version updates are disabled with `open-pull-requests-limit: 0`. |
| `require-github-actions` | `true` | Require a `github-actions` update block. |
| `fail-on-broad-groups` | `false` | Treat groups matching every dependency as errors instead of warnings. |
| `detect-ecosystems` | `true` | Detect manifests and require matching Dependabot ecosystems. |
| `detection-ignore-paths` | empty | Newline-separated repository-relative globs excluded from detection. |
| `detection-overrides` | empty | Newline-separated `glob=ecosystem` rules overriding automatic classification. |
| `include-ignored-directories` | `false` | Scan normally ignored build/vendor/cache directory names; `.git` always remains excluded. |

## Outputs

| Output | Description |
| --- | --- |
| `update-blocks` | Number of Dependabot update blocks validated. |
| `detected-ecosystems` | Comma-separated ecosystems detected from repository manifests. |
| `detection-excluded-count` | Number of manifests excluded by detector path rules. |
| `detection-overridden-count` | Number of manifests reclassified by detector overrides. |
| `excluded-manifests` | Comma-separated excluded repository-relative paths. |
| `overridden-manifests` | Comma-separated applied `path=ecosystem` overrides. |

## Example

```yaml
- uses: DiogoRibeiro7/safe-dependabot@v1
  id: dependabot-policy
  with:
    max-open-prs: 3
    require-major-ignore: true
    require-github-actions: true
    fail-on-broad-groups: true
    detect-ecosystems: true

- name: Show detected ecosystems
  run: echo "${{ steps.dependabot-policy.outputs.detected-ecosystems }}"
```

## Targeted ecosystem detection controls

Prefer targeted controls over disabling ecosystem detection for the whole repository.

Ignore generated fixtures or archived manifests with repository-relative globs:

```yaml
- uses: DiogoRibeiro7/safe-dependabot@v1
  with:
    detection-ignore-paths: |
      fixtures/**
      archived/**/package.json
```

Override ambiguous or intentionally non-standard manifests:

```yaml
- uses: DiogoRibeiro7/safe-dependabot@v1
  with:
    detection-overrides: |
      infra/**/*.tf=opentofu
      legacy/package.json=npm
```

The first matching override wins. Override ecosystem values are validated against the same supported-ecosystem set as `package-ecosystem`.

By default, generated/environment directory names such as `build`, `dist`, `vendor`, `target`, and virtual environments are pruned. Re-enable scanning of those names when they contain legitimate projects:

```yaml
- uses: DiogoRibeiro7/safe-dependabot@v1
  with:
    include-ignored-directories: true
```

The repository metadata directory `.git` is always excluded.

The action reports how many manifests were excluded or overridden and emits the adjusted paths through outputs.

## Disabling ecosystem detection

If targeted controls are not sufficient, automatic detection can still be disabled:

```yaml
- uses: DiogoRibeiro7/safe-dependabot@v1
  with:
    detect-ecosystems: false
```

The rest of the Dependabot policy validation still runs.


## Multi-ecosystem groups

Safe Dependabot validates GitHub's multi-ecosystem group structure.

A valid group defines its schedule at the top level, while each participating update entry references the group and provides dependency `patterns`:

```yaml
version: 2

multi-ecosystem-groups:
  runtime:
    schedule:
      interval: weekly

updates:
  - package-ecosystem: docker
    directory: /
    multi-ecosystem-group: runtime
    patterns: ["*"]

  - package-ecosystem: npm
    directory: /
    multi-ecosystem-group: runtime
    patterns: ["*"]
```

Safe Dependabot checks that:

- each referenced group exists;
- each top-level group is a mapping with a valid schedule;
- each grouped update entry defines a non-empty `patterns` list;
- grouped entries are not incorrectly required to duplicate the group schedule;
- grouped entries do not receive a standalone missing-`open-pull-requests-limit` warning.

Other per-ecosystem policy rules still apply to grouped update entries.


## Structural validation

Before policy rules run, Safe Dependabot performs lightweight structural checks so obvious configuration errors fail in CI rather than later inside Dependabot.

The validator checks:

- `package-ecosystem` against GitHub's currently supported YAML values;
- exactly one of `directory` or `directories`;
- non-empty string locations and non-empty `directories` lists;
- globbing only through `directories`, not `directory`;
- `github-actions` coverage from the repository root (`/`);
- ordinary dependency-group identifiers and common group option types.

Supported package ecosystem values currently include:

```text
bazel, bun, bundler, cargo, composer, conda, deno, devcontainers,
docker, docker-compose, dotnet-sdk, elm, gitsubmodule, github-actions,
gomod, gradle, helm, julia, maven, mix, nix, npm, nuget, opentofu,
pip, pre-commit, pub, rust-toolchain, sbt, swift, terraform, uv, vcpkg
```

This is intentionally a lightweight schema layer rather than a replacement for Dependabot Core's complete configuration parser.


## Schedule validation

Safe Dependabot validates schedule semantics for both ordinary update blocks and multi-ecosystem groups.

Supported intervals are `daily`, `weekly`, `monthly`, `quarterly`, `semiannually`, `yearly`, and `cron`.

Additional checks include:

- `day` must be a lowercase weekday and is only valid with `weekly`;
- `time` must use 24-hour `HH:MM` format;
- `timezone` must be a known IANA timezone and requires `time`;
- `cron` requires a non-empty `cronjob`;
- `cronjob` is rejected for non-`cron` intervals.

Example:

```yaml
schedule:
  interval: weekly
  day: tuesday
  time: "02:00"
  timezone: Europe/Lisbon
```

Cron example:

```yaml
schedule:
  interval: cron
  cronjob: "0 9 * * *"
```
