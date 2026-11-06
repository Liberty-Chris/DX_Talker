# Shared ElevenLabs pilot service

The Windows app uses one shared DX Talker account without asking testers for API keys. The service runs as ordinary PHP on DreamHost. It needs PHP 8.2 or newer, JSON, cURL, HTTPS and writable private storage with working file locks. It does not need a background daemon, container or database server.

The chosen pilot URL is `https://www.jcara.club/dxtalker-speech/speech.php`. This repository prepares the service but does not deploy it or contain an account key.

## Where I enter the key

After merging this PR, run the setup command on the DreamHost shell. The `ElevenLabs API key` prompt hides what is typed. Setup stores the key in `~/dxtalker-private/speech/config.json` with account only permissions, outside the public website folder. That private file is where I can later change the key, allowed voices, model and testing limits. Rerunning setup with a blank key keeps the existing key. Do not paste this file into GitHub or distribute it with DX Talker.

Choose a voice in the ElevenLabs dashboard and copy its voice ID. The initial setup enables one voice; additional `{"id":"VOICE_ID","name":"Readable voice name"}` entries can be added to the private `voices` array. The server controls the model and allowlist. Testers see only voice choices.

## Install on DreamHost

Check the website’s actual document root first. The example below assumes the existing website folder is `~/jcara.club`. If that is different in the DreamHost panel, substitute its actual folder. The public service folder must be inside that document root. The private directory must stay outside it.

```bash
git clone --branch main https://github.com/Liberty-Chris/DX_Talker.git "$HOME/dxtalker-service-src"
cd "$HOME/dxtalker-service-src"
php -r 'echo PHP_VERSION, PHP_EOL; echo extension_loaded("curl") ? "curl available\n" : "curl MISSING\n";'
python3 server/speech/configure.py --web-root "$HOME/jcara.club/dxtalker-speech" --url 'https://www.jcara.club/dxtalker-speech/speech.php'
```

The setup prompts for the key, voice ID, readable label and model. The default model is `eleven_multilingual_v2`. Initial limits are 10,000 uncached text bytes per UTC day, 2,000 service requests per day and 300 requests per hour per server observed IP. These are conservative pilot limits, not a promise about a particular dollar amount or ElevenLabs plan allowance. Input accounting uses UTF8 bytes and includes failed upstream requests. Configure account level credit restrictions in ElevenLabs as well.

The installer creates a public `speech.php` containing only an include path and a private directory containing gateway.php, config.json and client.json. Quota state and audio cache remain in private storage. It refuses to overwrite an unrelated public speech.php. No WordPress files are modified.

Use a valid HTTPS certificate and keep certificate verification enabled. The service rejects plain HTTP. With Cloudflare, use a verified HTTPS connection to the origin. The service uses the server observed address for rate limiting and ignores forwarded IP headers; a reverse proxy may therefore group several testers under one hourly allowance.

Verify the catalog without generating speech:

```bash
python3 scripts/check_shared_speech.py --client-config "$HOME/dxtalker-private/speech/client.json"
```

To explicitly test the real provider and consume account allowance, add a preview output path. This saves a WAV without playing it or opening PTT:

```bash
python3 scripts/check_shared_speech.py --client-config "$HOME/dxtalker-private/speech/client.json" --preview "$HOME/dxtalker-preview.wav"
```

## Configure app builds once

`~/dxtalker-private/speech/client.json` contains the public service URL and a revocable pilot admission value. It does not contain the ElevenLabs key. In the repository’s Settings, Secrets and variables, Actions, create a repository secret named `DXTALKER_SPEECH_CONFIG` and paste the contents of client.json into it. This is the client file, not config.json.

The Windows build injects that client configuration into `assets/services/speech.json` before packaging. The build script rejects an owner configuration containing an API key. Builds without the secret retain an unconfigured service and show an explanatory message if ElevenLabs is selected. Tests never need the real secret and fork pull requests do not receive it. Run a trusted Windows workflow after setting the secret and publish the resulting build for testers.

The admission value is included in the app and can be extracted from it. It is a revocable pilot access mechanism, not a secret that can be protected inside a public binary or a replacement for individual public release authentication. Server limits and voice/model restrictions bound pilot use. Rotate it with `--rotate-pilot-token` when needed, replace the build secret with the new client.json and distribute an updated build. Old clients will be rejected. The ElevenLabs key can be rotated privately without rebuilding the app.

## Operator controls

Set `enabled` to JSON `false` in the private config to stop the service. Edit `daily_characters`, `daily_requests` and `hourly_requests_per_ip` to adjust testing allowances. The state uses UTC day/hour boundaries and atomically reserves new text before contacting ElevenLabs. Failed requests are not refunded or retried automatically. Two upstream jobs may run concurrently; stale reservations expire after three minutes. The client can cancel locally but a request already accepted by the service can still consume allowance.

Audio segments are cached by a hash of model, voice and text for up to one day, with a default 20 MiB and 2,000 file bound. The service stores no raw text in its quota state or request logs. It retains generated audio in the private cache. Quota state contains hashed IP identifiers. Web server access logs remain subject to the hosting account’s policy. Text necessarily reaches the private service and ElevenLabs; this setup does not promise zero retention by ElevenLabs.

The endpoint accepts at most 1,000 text bytes and 128 bounded plan segments per request. It returns mono 22050 Hz PCM16 with the requested pauses. The app prepares the complete result before the existing coordinator may key PTT. Upstream URLs are fixed, redirects are disabled and certificate checks remain enabled. Failure stops speech output visibly rather than silently switching providers.

## Checks

```bash
php -l server/speech/gateway.php
php server/speech/test_gateway.php
python3 -m unittest discover -s tests -p 'test_cloud_speech.py' -v
```

The PHP checks exercise the actual service logic with a synthetic provider, including atomic quota reservation, cache reuse, admission, malformed payloads, provider failure and parallel requests where pcntl is available. They do not call a paid API. Actual DreamHost deployment, HTTPS reachability and provider generation remain owner acceptance steps.
