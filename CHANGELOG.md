# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Releases are generated automatically from [Conventional Commits](https://www.conventionalcommits.org/)
by [python-semantic-release](https://python-semantic-release.readthedocs.io/).
The release list starts at the marker below; content above it is editorial and
preserved across releases.

<!-- version list -->

## v1.1.0 (2026-08-16)

### Chores

- Remove comments from workflows and pyproject ([#7](https://github.com/iqbalmh18/brave-api/pull/7),
  [`7b3c673`](https://github.com/iqbalmh18/brave-api/commit/7b3c6739d49a8a07e493693ff902a1749dabb2fe))

- Update README and SVG banner for improved clarity and design
  ([`d715cc2`](https://github.com/iqbalmh18/brave-api/commit/d715cc201421dfcc08c7312ad5aff633715536e0))

### Documentation

- Simplify README by removing architecture and general features
  ([`6d3ef4e`](https://github.com/iqbalmh18/brave-api/commit/6d3ef4efd127f030958ffaa056fe69a84f58c469))

  Removed sections on architecture and general features to streamline the README.

### Features

- Search verticals and documentation ([#8](https://github.com/iqbalmh18/brave-api/pull/8),
  [`9276298`](https://github.com/iqbalmh18/brave-api/commit/92762982612cf137bd6d502c0db562b948addd59))

  * feat(search): add search verticals and documentation

  * style(docs): align README and docs colors


## v1.0.3 (2026-08-08)

### Bug Fixes

- Persist-credentials false so release tag uses PAT.
  ([#6](https://github.com/iqbalmh18/brave-api/pull/6),
  [`4b333bb`](https://github.com/iqbalmh18/brave-api/commit/4b333bb5d6bc4085b1edaeea58dc4ae94b1cc7aa))

  * fix: render commit bodies in release notes

  * fix: persist-credentials false so release tag uses PAT


## v1.0.2 (2026-08-08)

### Bug Fixes

- Render commit bodies in release notes ([#5](https://github.com/iqbalmh18/brave-api/pull/5),
  [`bbfd317`](https://github.com/iqbalmh18/brave-api/commit/bbfd31785e918062bb166fd2ccbbfcb09259478d))


## v1.0.1 (2026-08-08)

### Bug Fixes

- Release workflows ([#4](https://github.com/iqbalmh18/brave-api/pull/4),
  [`b959b59`](https://github.com/iqbalmh18/brave-api/commit/b959b5936eccb95f5186173cc89f700d2f92e0d3))

- Use release token so tag push triggers publish workflow
  ([#4](https://github.com/iqbalmh18/brave-api/pull/4),
  [`b959b59`](https://github.com/iqbalmh18/brave-api/commit/b959b5936eccb95f5186173cc89f700d2f92e0d3))

### Continuous Integration

- Add manual publish trigger ([#4](https://github.com/iqbalmh18/brave-api/pull/4),
  [`b959b59`](https://github.com/iqbalmh18/brave-api/commit/b959b5936eccb95f5186173cc89f700d2f92e0d3))


## v1.0.0 (2026-08-08)

### Bug Fixes

- Make semantic release build with uv ([#3](https://github.com/iqbalmh18/brave-api/pull/3),
  [`c53b07f`](https://github.com/iqbalmh18/brave-api/commit/c53b07fa149b7da77e3efc76c064cc61f295809f))

- Make semantic release build with uv ([#2](https://github.com/iqbalmh18/brave-api/pull/2),
  [`77c0133`](https://github.com/iqbalmh18/brave-api/commit/77c013339c4db93b8ec0e16f5edac46d3384ca97))

- Use release token so tag push triggers publish workflow
  ([#3](https://github.com/iqbalmh18/brave-api/pull/3),
  [`c53b07f`](https://github.com/iqbalmh18/brave-api/commit/c53b07fa149b7da77e3efc76c064cc61f295809f))

### Continuous Integration

- Pass GITHUB_TOKEN to PR title validation ([#1](https://github.com/iqbalmh18/brave-api/pull/1),
  [`94b4095`](https://github.com/iqbalmh18/brave-api/commit/94b4095a77d2ad38e565e9bd82110a3bb08b408f))

### Features

- Introduce typed streaming and release automation
  ([#1](https://github.com/iqbalmh18/brave-api/pull/1),
  [`94b4095`](https://github.com/iqbalmh18/brave-api/commit/94b4095a77d2ad38e565e9bd82110a3bb08b408f))
