# Stable release acceptance

Pilot builds do not invent a usage agreement or collect signatures. Stable installer builds are gated on owner approved TERMS.txt and PRIVACY.txt in this folder, plus approved.json with owner_approved true and SHA256 hashes for both exact files. The project owner supplies and approves the actual legal text before enabling a stable release.

The stable installer displays the privacy notice and requires acceptance of the terms through its license page. Local diagnostic logging defaults off for stable versions and can be enabled in the app. No telemetry transport or automatic report upload exists. Any future telemetry service needs its own explicit consent, scope, retention and revocation controls; accepting terms must not silently enable it.

The approval record is a release gate, not a claim of legal review or a digital signature. Installer acceptance is not identity verification. Platform store terms and consent must be reviewed independently for Android and iOS.
