# Documentation index

This documentation describes a planned modernization. The [status record](STATUS.md) is authoritative about what exists today.

## Project and engineering

[Requirements](requirements.md) captures intended behavior and acceptance criteria. [Architecture](architecture.md) describes proposed component boundaries. [Decisions](decisions.md) records accepted choices and proposals. [Questions](questions.md) holds unresolved details. [Legacy findings](legacy.md) records what the archive actually reveals.

The root [roadmap](../ROADMAP.md) orders delivery. [Agent instructions](../AGENTS.md) establish the maintenance workflow. The [changelog](../CHANGELOG.md) records meaningful repository changes.

## Operator documentation

[Help and Info](help/index.md) is the canonical source for the future application's operator documentation. [Getting started](help/getting_started.md), [source connections](help/connections.md), [radio setup](help/radio.md), [identification](help/identification.md), [troubleshooting](help/troubleshooting.md) and [About](help/about.md) are initial pages.

## Keeping help current

Each behavior change updates the relevant help page in the same change. Keep planned behavior clearly labeled until tested implementation replaces it. Preserve stable page IDs in [the help manifest](help/manifest.json) so the app can open a specific topic from a setting or error.

The future build must package these Markdown pages for offline use. Rendering technology is undecided. Before release, validate manifest targets, local links, navigation and correspondence between the packaged manual and application version. Development evidence belongs in project documents while operator instructions belong in help.
