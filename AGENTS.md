# Working on DX Talker

Read [README.md](README.md), [ROADMAP.md](ROADMAP.md), [docs/STATUS.md](docs/STATUS.md), [requirements](docs/requirements.md), [architecture](docs/architecture.md) and [open questions](docs/questions.md) before starting work. Read relevant operator help before changing user behavior.

## Evidence and scope

This repository currently contains historical binaries and planning documentation. Do not invent recovered source, a working modern application, confirmed hardware compatibility or successful endpoint tests. Separate user supplied history, direct archive observations, proposals and validated implementation.

Preserve the original ZIP byte for byte. Do not run legacy binaries as part of ordinary development. Record static findings with archive paths and inspection methods. Do not silently convert uncertain history into fact.

Use the roadmap to select a bounded next task. Document unresolved choices before building dependencies on them. A proposed architecture does not authorize a fixed framework, hardware purchase, account creation or login to a live cluster.

## Documentation accompanies implementation

Every change to operator behavior must update its corresponding page in docs/help in the same change. Update docs/STATUS.md with actual implementation and verification evidence. Update ROADMAP.md when milestone status changes and CHANGELOG.md for meaningful changes. Record consequential choices and their reasons in docs/decisions.md. Resolve questions with dated evidence.

The Markdown pages under docs/help are the canonical help text. Keep page IDs in docs/help/manifest.json stable. Build the eventual application's Help and Info sections from these files rather than maintaining a separate manual. Before an application release, check that every visible setting, error recovery path and supported hardware method is covered accurately.

Do not mark a milestone complete because a design document exists. Record what was tested, on which Windows version and with which interface when applicable. Identify simulated verification separately from physical RF verification.

## Implementation constraints

Feed text is untrusted input. Only validated spots can reach announcement generation. Login prompts, banners, chat and arbitrary remote commands must not be spoken or executed. Never store real credentials in examples, captures or diagnostics.

All radio audio and PTT must go through one transmission coordinator. Startup and recovery must leave transmission disabled. Identification, spot audio and manual tests must not overlap. Implement a bounded transmit duration, immediate stop and guaranteed release attempts on cancellation and failures. Hardware behavior after process or cable failure must be tested and documented.

Do not add a license or claim rights to archive contents without a project owner decision. Do not introduce a build command or supported platform claim until it has actually been established and checked.

## Completion record

A finished task includes the concrete change, relevant help updates, verification results and any remaining limitations. For documentation changes, validate local links, help manifest targets, status consistency and preservation of archive contents. For implementation work, run checks appropriate to the behavior and report any checks that could not run.
