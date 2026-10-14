# Source connections

Status: planned. No source adapter or successful live sign in has been verified yet.

## Cluster host and port

The supplied example uses host `w4mr.ddns.net`, port `7373` and a TCP/Telnet connection. This is not a web page URL. In the intended application, choose the cluster connection type and enter host and port separately.

The source may prompt for a callsign, password or other information. Its actual exchange must be confirmed before final instructions are written. Signing in to a cluster is separate from a DX Talker account. No application account is currently planned as a prerequisite.

Plain TCP/Telnet does not inherently encrypt submitted credentials. Use the service's documented connection method and do not assume HTTPS protections apply.

## Web feed URL

A web feed needs a supported provider and payload format. A regular website address may return an HTML page rather than DX spots. Web feed support is planned after a specific provider, authentication mechanism and format are confirmed.

## Connection status

The intended status display distinguishes connecting, awaiting login, receiving spots and retrying after a disconnect. A successful network connection does not necessarily mean login succeeded.

After a disconnect, old queued spots should expire rather than transmit as a backlog. Reconnecting must not automatically enable RF. See [troubleshooting](troubleshooting.md) for planned recovery guidance.
