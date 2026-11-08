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


## Publish from the Actions page

The Windows pilot workflow has an optional Publish the current main version after verification input. After merging the version changes, open Actions, choose Windows pilot, choose Run workflow, select main and enable that input. Leave it disabled for an ordinary verification build.

The publish job runs only on main or a version tag and requires core tests, Windows package and installer checks plus a real Piper render check. It derives the release version from the application, verifies version alignment and creates the version tag if needed. An existing tag pointing to a different commit fails publication. A successful run publishes the installer, portable ZIP, release notes and SHA256SUMS.txt. Preview versions remain prereleases for the Pilot channel.

For the first live update test, keep 0.2.0a1 installed. After publishing 0.2.0a2, open History / Updates, choose Pilot and Check now. Confirm version and change notes, then Download update and Install update. Confirm 0.2.0a2 on reopening and check that preferences remain and output is disabled. The person running the installed Windows app must confirm the final operator result.


## Publication retries and workflow runtime

The workflows use pinned action versions declaring Node.js 24. This is the GitHub Actions runtime; the application remains Python and Kotlin with Java 17 for Android builds.

Publication jobs are serialized across workflow runs. Repeating publication for the exact tagged commit checks the existing release through the GitHub API. A published release with every expected uploaded, nonempty asset succeeds with a notice and preserves its existing downloads. Missing releases are created only after an explicit API 404. Draft or incomplete releases, network failures and permission errors stop for review. Existing tags pointing to another commit still stop publication. A new application build intended for release needs a new version, not a reused tag. Asset presence checks do not replace checksum validation of downloaded installers.

The version alignment check also verifies the opening version in docs/releases/current.md. Updating that file affects future publication only; release notes already published on GitHub must be edited separately.

## Android test downloads

Open Actions and choose Android APK, then select a successful run for the intended main commit. Download its debug APK artifact, extract the ZIP and install app-debug.apk. Pull request artifacts are candidate builds, not published Windows updates. Starting with a18, the publish workflow also calls the Android workflow on the same commit, waits for both Android jobs and attaches the tested APK to the same GitHub Release as Windows and XP. Choose the Android phones and tablets link to download DXTalker-Android.apk directly. The APK is included in SHA256SUMS.txt. It does not appear in the desktop updater. Check the run commit and app version rather than assuming the most recent run contains a new version. Artifact downloads require GitHub sign in and expire according to the workflow retention setting.


## Version ownership and published text corrections

A release version belongs to one tested commit. PR 25 changed workflow tooling while retaining a12, so publishing its merge commit stopped at the existing tag guard. Run 42442975977 confirmed this cause after all packaging checks passed. The next release is a13 with matching application, installer, EXE numeric metadata, help version, Android version name and increased Android version code. Ordinary merges and workflow runs do not increment versions automatically.

Publication now checks tag ownership in the Linux core job before Windows packaging. A conflict explains that the version and metadata must be increased. The publish job repeats that check under publication concurrency to catch another run publishing in the meantime.

Archived release descriptions live at docs/releases/vVERSION.md. The Release notes workflow validates each archive and, on main pushes that change those files or its tooling, updates matching published release bodies. It can also be run manually on main. Its write permission is limited to the sync job, which edits only notes using gh release edit. It does not create a release, move tags or replace assets. PR validation has read permission and never edits releases. Failed lookups and draft releases stop synchronization. The initial archive corrects a12's accidentally copied a11 description. Current.md remains the description for the next publication and is not used to rewrite older releases.

## XP installers and download labels

The Windows pilot workflow includes a reusable XP x86/x64 job. Publication depends on both XP architectures as well as modern Windows, portable core and neural speech checks. Each XP job stages a hash verified private official runtime, executes shared fixtures with that interpreter, compiles a native launcher and setup, verifies UI/system speech/QR/DPAPI, checks public update HTTPS and exercises install, upgrade, desktop shortcut preservation and removal. Synthetic tests do not play audio or assert PTT. Hosted Windows is not actual XP acceptance.

Modern updater filenames stay unchanged. XP builds select only their separately named XP installer. The checksum file covers all prepared installers and ZIP files. Publication adds descriptive GitHub asset labels and a managed download table to the version specific notes. Release prose corrections retain that table and skip archived source versions that have never been published. Existing limited XP source kits remain labelled as developer material. New releases use the application installers instead.

The Android publication dependency runs for an actual tagged or manually requested publication. Ordinary PR checks keep using the existing Android APK workflow, avoiding a duplicate Android emulator run for the same PR. This change retains the pilot debug APK signing/build process. It does not establish a production signing identity, guaranteed replacement of an APK signed with a different debug key, Play Store delivery or automatic mobile updates. Those are separate release preparations.
