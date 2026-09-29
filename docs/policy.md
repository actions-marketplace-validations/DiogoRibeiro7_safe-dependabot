# Policy rules

Safe Dependabot separates routine dependency maintenance from deliberate breaking upgrades.

## Major-version updates

When `require-major-ignore` is enabled, the preferred policy is to allow routine minor and patch version updates explicitly:

```yaml
allow:
  - dependency-name: "*"
    update-types:
      - version-update:semver-minor
      - version-update:semver-patch
```

GitHub documents that `allow.update-types` affects version updates only, not security updates. This blocks routine major version-update pull requests while still allowing Dependabot to create a security update when remediation requires a major version.

Legacy wildcard `ignore` rules for `version-update:semver-major` remain accepted in v1 for compatibility, but Safe Dependabot emits a warning because GitHub applies `ignore` filtering to security updates as well.

The intention is not to avoid major upgrades permanently. It is to make routine major upgrades explicit engineering work with migration notes, dedicated tests, and focused review without weakening vulnerability remediation.

!!! warning "Pre-1.0 dependencies"
    Semantic versioning allows breaking changes in minor releases before version 1.0. A `0.4 -> 0.5` update can therefore still be breaking even when it is not classified as semver-major.

## Pull-request limits

Dependabot can generate substantial PR churn in repositories with many dependency groups. GitHub's default for standalone version-update blocks is five open pull requests when `open-pull-requests-limit` is omitted.

Safe Dependabot validates the **effective** limit. With the default `max-open-prs: 5`, an omitted standalone limit is accepted with a warning because GitHub's effective value is five. If a repository lowers the policy maximum, omission can become an error:

```yaml
- uses: DiogoRibeiro7/safe-dependabot@v1
  with:
    max-open-prs: 3
```

In that case, standalone update blocks must explicitly set `open-pull-requests-limit` to three or less.

Setting `open-pull-requests-limit: 0` disables version updates for that package ecosystem while leaving security updates enabled. Safe Dependabot therefore does not require a routine major-version guard on a security-only block.

Multi-ecosystem groups are treated separately: GitHub consolidates a group into a single cross-ecosystem pull request, so grouped member entries are not assigned the standalone default-five warning merely because they omit `open-pull-requests-limit`.

## Broad groups

A completely unconstrained wildcard group can make a failed CI run harder to diagnose because many unrelated dependency changes arrive together:

```yaml
groups:
  everything:
    patterns:
      - "*"
```

Safe Dependabot only treats that group as broad when the wildcard is not meaningfully narrowed. The warning is suppressed when the group uses:

- non-empty `exclude-patterns`;
- a specific `dependency-type`;
- a proper subset of SemVer `update-types`;
- `applies-to: security-updates`.

An explicit `applies-to: version-updates` does not narrow the group because version updates are Dependabot's default group scope. Likewise, listing all three SemVer levels (`major`, `minor`, and `patch`) remains effectively unconstrained.

By default an unconstrained wildcard generates a warning. To fail the policy check instead:

```yaml
- uses: DiogoRibeiro7/safe-dependabot@v1
  with:
    fail-on-broad-groups: true
```

## GitHub Actions coverage

With `require-github-actions: true`, Safe Dependabot requires a `github-actions` update block. Workflow dependencies age like application dependencies and should be maintained deliberately.

## Security updates

Safe Dependabot validates configuration. It does not approve, merge, or suppress security updates, and it does not replace Dependabot alerts or dependency review.


## Schedule semantics

Safe Dependabot validates the combinations of schedule fields that materially affect Dependabot behavior. In particular, cron schedules must provide `cronjob`, weekly `day` values are checked explicitly, clock times use 24-hour `HH:MM`, and timezone identifiers are validated against the IANA timezone database.

The same validation is used for standalone update schedules and top-level multi-ecosystem group schedules.
