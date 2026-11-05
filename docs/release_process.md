# Release and update process

## Publish

1. Merge reviewed changes and choose the next version. Update dxtalker/__init__.py, scripts/installer.iss, scripts/windows_version.txt and docs/help/manifest.json together. Maintain numeric EXE version information too.
2. Update CHANGELOG.md, operator help, status and docs/releases/current.md. Run the unit suite, documentation checker and scripts/check_versions.py.
3. Build and test the Windows artifact. Confirm supported targets and known limitations. Create a matching version tag such as v0.2.0a1 and push it.
4. The Windows pilot workflow runs core and desktop tests, source and packaged speech smoke checks, installer compilation and install/reinstall/removal checks. Only after both test and Windows jobs succeed does the publish job upload the setup executable, portable ZIP and SHA256SUMS.txt to GitHub Releases. The tag must exactly match the application version.
5. Tags containing a, b or rc are published as prereleases. Pilot clients see these; Stable clients see final releases only. The updater looks for the fixed installer and checksum asset names. Failed builds do not publish an update.

GitHub Actions contents write permission is restricted to the publish job. Branch and pull request builds produce artifacts but never publish releases. No credential, cluster or radio access is part of the release workflow.

## First update test

The old 0.1.0a2 installation has no updater. Install 0.2.0a1 once manually from a successful artifact or release. Configure a synthetic profile, choose a log folder and change a speech setting. Keep output stopped.

Publish the next tested prerelease with a higher version and distinct release notes. In the older updater enabled app select Pilot and Check now. Confirm the notification and correct notes, download it, confirm verification and install. Confirm the displayed new version, retained profile, retained history configuration and disabled output after launch.

Repeat with automatic checks disabled, an unavailable network, interrupted download, a bad checksum and a failed installer launch. Unit fixtures exercise the discovery, ordering, truncation, hash and cancellation cases without a live release. Windows CI exercises settings migration, protected secret roundtrip and installation separately. The complete two release operator upgrade test remains required before claiming it has passed.

Do not publish a fabricated newer release merely to force a notification. The next release should contain a real change and its own verification.

## Recovery

The current installation remains intact until the operator opens setup. A checksum failure removes only the partial download. No background installer or automatic RF restart is used. A failed installation can be retried with the published setup. Account data is outside the install directory. The current installer is unsigned; checksum verification does not replace publisher signing.
