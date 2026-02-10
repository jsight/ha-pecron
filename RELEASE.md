# Release Process

This document describes how to create and publish a new release.

## Prerequisites

- All changes merged to `main` branch
- All CI checks passing
- CHANGELOG.md updated with release notes
- Version bumped in `custom_components/pecron/manifest.json`

## Release Steps

### 1. Update Version

Update the version in `custom_components/pecron/manifest.json`:

```json
{
  "version": "0.2.0"
}
```

### 2. Update Changelog

Add a new section to `CHANGELOG.md` at the top (under "## Unreleased" if present):

```markdown
## [0.2.0] - 2026-02-10

### Added
- New feature description
- Another feature

### Fixed
- Bug fix description

### Changed
- Change description
```

Follow [Keep a Changelog](https://keepachangelog.com/) format.

### 3. Commit Changes

```bash
git add custom_components/pecron/manifest.json CHANGELOG.md
git commit -m "Bump version to 0.2.0"
git push
```

### 4. Create Git Tag

```bash
git tag -a v0.2.0 -m "Release version 0.2.0"
git push origin v0.2.0
```

Or without annotation:

```bash
git tag v0.2.0
git push origin v0.2.0
```

### 5. GitHub Actions Will Automatically:

- Validate the version format (v0.0.0)
- Verify version matches manifest.json
- Check changelog entry exists
- Create GitHub Release with changelog notes

## Release Validation

The release workflow validates:

1. **Version Format**: Must be `v{major}.{minor}.{patch}` (e.g., v1.2.3)
2. **Manifest Version**: Tag version must match `manifest.json` version
3. **Changelog Entry**: Release version must exist in CHANGELOG.md

If validation fails, the release workflow will fail with clear error messages.

## Release Checklist

- [ ] All features/fixes merged to main
- [ ] All CI checks pass on main
- [ ] CHANGELOG.md updated
- [ ] Version bumped in manifest.json
- [ ] Changes committed and pushed
- [ ] Git tag created with correct format
- [ ] Tag pushed to GitHub
- [ ] Check GitHub Actions workflow completes
- [ ] Verify release appears at https://github.com/jsight/ha-pecron/releases

## Rollback

If you need to remove a release:

```bash
# Delete local tag
git tag -d v0.2.0

# Delete remote tag
git push origin :refs/tags/v0.2.0

# Delete GitHub release (via web UI)
```

## HACS Automatic Updates

Once a release is published on GitHub:

1. HACS will detect the new release
2. Users with HACS will see an update available
3. Update will be installed from the GitHub release

No additional action needed for HACS integration once it's registered.

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (v1.0.0): Incompatible API changes, breaking changes
- **MINOR** (v0.1.0): New features, backwards compatible
- **PATCH** (v0.0.1): Bug fixes, backwards compatible

Example progression:
- v0.1.0 (initial release)
- v0.1.1 (patch)
- v0.2.0 (new feature)
- v0.2.1 (patch)
- v1.0.0 (major milestone)
