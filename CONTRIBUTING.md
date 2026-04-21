# Contributing to Neko Futures Trader

## Commit Message Convention

This project follows [Conventional Commits](https://www.conventionalcommits.org/).

### Format
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

| Type | Description | Version Bump |
|------|-------------|-------------|
| `feat` | New feature | minor |
| `fix` | Bug fix | patch |
| `docs` | Documentation only | - |
| `style` | Code style (formatting, semicolons) | - |
| `refactor` | Code restructuring (no behavior change) | - |
| `perf` | Performance improvement | patch |
| `test` | Adding/updating tests | - |
| `chore` | Build, CI, dependencies | - |
| `ci` | CI/CD changes | - |
| `build` | Build system changes | - |

### Breaking Changes
Add `!` after type or `BREAKING CHANGE:` in footer:
```
feat!: remove deprecated API endpoint
```
→ Bumps **major** version

### Scope (optional)
Use to specify the module affected:
```
feat(scanner): add multi-timeframe support
fix(dashboard): resolve position overflow
chore(deps): update binance-connector
```

### Examples
```bash
# Good ✅
git commit -m "feat(scanner): add RSI divergence detection"
git commit -m "fix(price-monitor): handle API timeout gracefully"
git commit -m "chore: update dependencies"
git commit -m "docs: add deployment guide to README"

# Bad ❌
git commit -m "fixed stuff"
git commit -m "update"
git commit -m "WIP"
```

## Release Process

```bash
# Make sure all changes are committed
git status

# Run release script
./release.sh patch   # 1.0.0 → 1.0.1
./release.sh minor   # 1.0.0 → 1.1.0
./release.sh major   # 1.0.0 → 2.0.0

# Push to remote
git push origin main --tags
```

## Versioning

This project uses [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0) — Breaking changes
- **MINOR** (0.X.0) — New features (backward compatible)
- **PATCH** (0.0.X) — Bug fixes (backward compatible)
