# Generic HTTPS JSON feed

The pilot supports this explicit contract in addition to TCP/Telnet clusters. It does not claim compatibility with every DX website or provider.

## Request

Choose HTTPS JSON in Source and enter an HTTPS URL. The app sends GET with Accept: application/json and optionally Authorization: Bearer followed by the session token. It polls at a configurable interval of at least 15 seconds. Credentials cannot be embedded in the URL. Redirects are rejected so a bearer token cannot be forwarded to another service.

## Response

Return a JSON array with at most 2000 records and at most 1 MiB of encoded data. Each accepted record has these fields:

```json
[
  {
    "dx_call": "WB4IUY/P",
    "frequency_khz": "14025.5",
    "spotter": "KT4BN",
    "time": "2026-10-31T12:34:00Z"
  }
]
```

Frequency is in kilohertz and may be a JSON number or decimal string. Time must be an ISO timestamp with a timezone. Callsigns must include at least one letter and digit. Invalid records are skipped. A nonarray response is a feed failure.

Comments and other fields are ignored. Future timestamps beyond two minutes are rejected. Spot age and duplicate policies apply before RF announcements, so an unchanged snapshot is not continually replayed.

## Limits

The pilot supports HTTPS polling only for this adapter. Provider specific schemas, OAuth, pagination, streaming JSON and HTML scraping are not included. A provider can implement this contract directly or use a separately maintained adapter service. The bundled help explains operator settings.
