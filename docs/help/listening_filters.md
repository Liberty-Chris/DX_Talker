# What do you want to hear?

On desktop, What do you want to hear? is embedded directly on Source beside connection settings. Narrow windows place it below those settings with the normal page scrollbar. The Live spots shortcut opens Source and scrolls to the editor. On Android, open Filters from Listen. Choose bands, modes and activities without learning cluster commands. Selecting or unselecting a filter saves it immediately on desktop and Android. There is no Apply step and the cluster stays connected. Pending announcements are cleared so the new choices take effect. The main spot list and announcements use the same filters. The All received display bypass has been removed. Why hidden? shows rejection counts without putting rejected spots back into the list.

## Combine interests

Choose POTA, 20m and SSB to hear spots meeting all three conditions. Choose 20m and 40m to accept either band while retaining the mode and activity conditions. All removes the band or activity restriction. All known modes accepts recognized modes and excludes Unknown. Include unknown must be explicitly selected to admit uncertain modes. Selecting CW and Include unknown accepts either while retaining the selected bands and other filters. Unselecting the final choice selects None and accepts no spots in that group. Use All or choose an item to resume.

Mode comes from an explicit feed field or a recognizable comment tag such as CW, SSB, USB, LSB, FT8, FT4, RTTY, PSK, FM or AM. A supplied mode takes precedence over frequency inference. When there is no mode tag, a frequency inside a documented single mode segment is classified as that mode. Conflicting or unsupported mode information remains Unknown and is never overwritten by frequency inference. Mixed mode portions, calling frequencies and unreviewed portions remain Unknown. The same rule applies to CW, SSB, FT8, FT4, RTTY, PSK, FM and AM. Current conservative frequency inference covers CW; shared phone and digital portions cannot identify one of the other modes on frequency alone. See the [classification table and sources](../mode_inference.md). POTA, SOTA and FOTA require those tags in the received comment. No activity tag means none of these tags was found, not proof that a station is not activating. Spot comments remain outside announcements, disk history and diagnostic exports.

## My operating privileges

FCC license class is optional and starts Off for unrestricted listening. Select Novice, Technician, General, Advanced or Extra and the FCC operating region. US Region 2 is the starting point for the continental United States. Region 1 and Region 3 refer to locations under FCC regulation in those ITU regions; they do not implement another country's licensing rules.

The bundled rules intersect class frequency authorizations with emission categories for the supported LF, MF, HF, VHF and UHF bands through 23cm. Band edges use exact decimal comparisons. A range's upper edge is excluded. Unknown mode or mode bandwidth conditions can make eligibility unverified. By default, selecting a license class hides unverified spots. Include unverified license eligibility is a separate opt in. It never admits a frequency known to be outside that class's authorizations.

This is a spot selection aid. It does not tune the radio or establish permission to transmit. Check your actual transmit frequency, split operation, sideband, occupied bandwidth, power, station conditions and location restrictions. For example, a spot on a lower phone segment edge can require a different dial frequency so its sideband stays inside the segment. A spotter or DX station's location does not set your license jurisdiction.

### Corrected US reference

The rule data is identified as FCC-2026-02-13-reviewed-2026-11-07. The supplied matrix's General 20m phone entry is corrected to 14.225 MHz. Novice and Technician 80m, 40m and 15m segments are CW only. Their 10m data and phone permissions are distinct. CW is not limited to customary CW calling frequencies. The 219 to 220 MHz fixed forwarding allocation is not an ordinary personal DX operating band and is excluded. The gap from 220 to 222 MHz is not merged into 1.25m privileges.

60m includes 5351.5 to 5366.5 kHz plus four discrete channels. For the discrete channels, CW uses center frequencies 5332, 5348, 5373 and 5405 kHz. The phone/data dial values are 5330.5, 5346.5, 5371.5 and 5403.5 kHz. The filter uses those mode specific reported values rather than allowing the entire surrounding spectrum. Emission and bandwidth conditions still apply.

The 7.075 to 7.100 MHz phone exception depends on operating location. FCC Regions 1 and 3 are handled explicitly. Region 2 eligibility there remains unverified because the filter has no operating coordinates to establish the exception. FM below 29 MHz also remains unverified where the emission bandwidth condition cannot be established from the spot. General class has no 75m authorization in FCC Region 1. Geographic exclusions and coordination requirements on other bands remain the operator's responsibility.

These are regulatory frequency/emission rules, separate from voluntary band plans, customary FT8/FT4 frequencies and calling frequencies. Updating a preferred operating frequency does not change a license authorization.

### Sources

[47 CFR 97.301, authorized frequency bands](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-D/part-97/subpart-D/section-97.301)

[47 CFR 97.303, frequency sharing and 60m channel definitions](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-D/part-97/subpart-D/section-97.303)

[47 CFR 97.305, authorized emission types](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-D/part-97/subpart-D/section-97.305)

[47 CFR 97.307, emission standards and Novice/Technician restrictions](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-D/part-97/subpart-D/section-97.307)

Rules are bundled for offline use and change through reviewed application updates. Sources are provided here rather than filling the listening controls with regulatory text.

## Location filters

Location and advanced filters separates Reporting station countries, continents and regions from DX station countries and continents. The reporting station is the person who submitted the spot. A nearby reporter may be useful, but similar reception is not guaranteed.

Use country codes such as US, CA or JP. Continent codes are AF, AN, AS, EU, NA, OC and SA. Region labels such as NC, SC or GA must match the supplied metadata. Several comma separated values within a field accept any listed value. Different location fields must all match. Blank fields accept all.

Location comes from explicit HTTPS feed metadata or an operator maintained known station list. Ordinary Telnet spot lines usually lack these fields. DX Talker does not guess current location from a callsign or call area. Known station locations uses the format `WB4IUY=US,NA,NC;KF4DBX=US,NA,IN`. These are operator supplied locations, which can become outdated when someone travels. A known station entry fills missing metadata for either station role; explicit feed metadata takes priority. There is no automatic lookup or account requirement.

Selected location filters hide missing locations unless Include unknown locations is enabled. Known nonmatching locations remain hidden. If no reports match, check Why hidden? before concluding the feed is broken. Desktop counts describe retained rows; Android counts cover reports hidden since the session began or filters were last applied. Existing cluster side filters can remove spots before DX Talker receives them. App filters cannot recover those reports and do not silently reset your server preferences.

## Presets and transfer

Save combinations as named listening presets, independently of cluster profiles. Loading a preset immediately saves and activates its choices. Save current choices as a named preset, remove an unwanted preset or overwrite its name to update it. Preset management does not require an Apply step. There can be up to 30 presets, subject to the bounded settings and transfer size.

Version 3 profile/QR collections include the current filters, license choices, known locations and saved listening presets without passwords or tokens. Review these locations before sharing a collection. Both receivers must support version 3; older applications should be updated first. Existing version 1 and 2 imports remain supported. Android legacy imports reset missing filter fields to their defaults while preserving the active connection profile.

## Keeping up

The additional gap accepts zero to 120 seconds. Zero adds no configured pause, but speech still takes time to prepare and play. The queue remains bounded and expires old spots. Pending count, oldest queued spot age, expired count and desktop preparation time help identify delays. Catch up to live on desktop or Live now on Android discards pending spots. It preserves the connection and does not interrupt the current announcement or cancel required IDs.

Desktop filter choices save immediately without applying unrelated connection or radio edits. Text and numeric filters save after a short typing pause when valid. Incomplete or invalid text stays visible with a Not saved message while the last valid value remains active. An unfinished text field does not block saving a band, mode or activity selection. Frequency limits are in the Source editor under Location and advanced filters.


Android keeps a highlighted Apply filters button below the scrolling form. The pending message distinguishes unsaved choices from applied filters. Applying clears old rows and queued announcements so new matching spots use the chosen rules, including when editing while listening is stopped. An active cluster stays connected. The service confirms application before reporting new matching spots. Preset loading stages its canonical settings, including units; it does not use a second hidden units draft.

Live rows show only recognized modes and actual POTA/SOTA/FOTA tags. Untagged activity and unknown mode placeholders are omitted. License filter names describe your selected listening rule above the list, not a station's license class. Desktop has a separate Mode column beside Spotted by and preserves Source for the feed name.

These are shared selection filters, not a promise to speak every historical row. Listening must be enabled and unmuted. Existing age, repeat, queue and receive hold controls still govern when eligible spots are spoken. Include unknown mode does not bypass a separately selected activity, location or license eligibility filter. Older app versions should be updated before importing presets that use the new None selection.
