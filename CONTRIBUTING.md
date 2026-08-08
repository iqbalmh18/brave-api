# Contributing

Thanks for your interest in brave-api. This project aims for the quality bar
of libraries like httpx, pydantic, and FastMCP before it reaches 1.0.

## Development setup

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync --group dev
```

## Commands

All quality gates must pass locally and in CI:

```bash
uv run pytest                 # unit tests (integration tests are opt-in)
uv run pytest -m integration  # live API tests, requires network access
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv build
uv run twine check dist/*
```

## Guidelines

- Keep the public API small and intentional. New public symbols must be
  documented in the README and re-exported from `brave_api/__init__.py`.
- Everything under `brave_api/_internal/` is private by convention.
- Every non-trivial behavior change needs a test.
- Run `ruff format` before committing; CI enforces it.
- Do not edit `CHANGELOG.md` by hand. It is generated from commit history by
  `python-semantic-release`; editorial content above the
  `<!-- version list -->` marker is preserved.

## Commit conventions

Releases are derived from [Conventional Commits](https://www.conventionalcommits.org/).
The commit type determines the version bump:

| Commit type | Bump | Example |
|---|---|---|
| `feat` | minor | `feat: add image search` |
| `fix` | patch | `fix: handle empty image results` |
| `perf`, `refactor` | patch | `perf: reduce stream allocations` |
| `feat!` / `BREAKING CHANGE:` | major | `feat!: redesign StreamResult API` |
| `docs`, `test`, `chore`, `ci`, `build`, `style` | none | `docs: update README` |

Put the important narrative of a change (why, migration notes) in the commit
body after a blank line — it becomes part of the generated release notes.

### Pull request titles

PR titles follow the same convention, because squash-merging uses the PR
title as the commit message. The `PR Title Validation` workflow blocks merges
with non-conventional titles.

- Issue titles are free-form (they are not part of the release pipeline).
- PR titles and commit messages must use a conventional prefix:
  `feat:`, `fix:`, `perf:`, `refactor:`, `docs:`, `test:`, `chore:`, ...

## Releasing

Releases are fully automated by [python-semantic-release](https://python-semantic-release.readthedocs.io/).
Pushing to `main` triggers the `Release` workflow:

1. CI runs (tests, ruff, pyright) and must pass.
2. `python-semantic-release` determines the next version from the commits
   since the last tag (`feat` -> minor, `fix` -> patch, breaking -> major).
3. Only when there are release-worthy commits (`feat`/`fix`/`perf`/`refactor`)
   it updates `brave_api/_version.py`, regenerates `CHANGELOG.md`, creates the
   `chore(release): <version>` commit, pushes the `v<version>` tag, and creates
   a GitHub Release with the built wheel and sdist attached.

Pushing the `v*` tag then triggers the `Publish` workflow, which rebuilds the
distributions and uploads them to PyPI.

No release is created for `docs`/`test`/`chore`/`ci`-only pushes — they just
run CI.

### Publishing to PyPI (one-time setup)

PyPI publishing uses [Trusted Publishing / OIDC](https://docs.pypi.org/trusted-publishers/)
— no API tokens are stored. To add the publisher on PyPI:

1. Open https://pypi.org/manage/account/publishing/ for `brave-api-python`.
2. Add a pending publisher with:
   - Owner: your GitHub username
   - Repository: `brave-api`
   - Workflow name: `publish.yml`
   - Environment: `pypi` (optional but recommended)

### Releasing locally (dry run)

To see what the next version and changelog would look like without changing
anything:

```bash
uv run semantic-release --noop version
```

## Code of conduct

Be respectful. This project accepts everyone's contribution regardless of
experience, identity, or the size of the fix.
