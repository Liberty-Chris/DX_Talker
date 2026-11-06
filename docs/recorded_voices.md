# Recorded voice packs

Recorded voices use small local WAV assets assembled into an announcement. No Piper model is loaded while listening or transmitting. The first reference pack is the US English LJ Speech high voice, whose model card identifies its training dataset as public domain. Model card: https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/ljspeech/high/MODEL_CARD. Dataset: https://keithito.com/LJ-Speech-Dataset/. Model training attribution is retained in the copied model card. Piper is an external GPL runtime used during generation, not bundled into the PCM pack.

Download the `DXTalker-VoicePack-LJ-high` workflow artifact or the corresponding ZIP on a published release. Extract it so a parent folder contains a voice subfolder with voice.json and the WAV files, plus the license or provenance supplied by that generator. In Speech, choose Recorded, browse to that parent folder and select the named voice. System Windows speech and optional live Piper remain available. Recorded packs have their generated speaking rate; the live speed control is disabled. Character and group pauses remain configurable.

The builder generates 77 standard assets: digits, phonetic letters, regular letter names, decimal/units/portable suffix words, reusable intro words and full New DX/New DX on phrases. Custom intro text can be added as another phrase during generation. Unknown words fail visibly rather than silently changing voice provider. Voice IDs that need arbitrary text may require added assets or a separate WAV ID. Complete phrase assets sound more natural; arbitrary concatenation has a different cadence and needs operator listening acceptance.

Install Piper separately in a generator environment and supply a local ONNX model, its matching .onnx.json file and reviewed model card/license:

```powershell
python scripts/build_voicepacks.py --model C:\Voices\en_US-ljspeech-high.onnx --license C:\Voices\en_US-ljspeech-high.MODEL_CARD --output C:\DXTalkerVoices\ljspeech --label "LJ Speech English female" --intro "New DX from my station"
```

`--models-dir` instead of `--model` generates every locally available model/speaker with its matching `<model-name>.MODEL_CARD`. It does not download all models or assume they have the same redistribution terms. Multi-speaker model IDs produce separate choices. Review each voice's model card and dataset terms before distributing generated packs. The supplied builder requires that card and copies it into the output. Supplying a file does not constitute legal approval. Existing completed packs are not overwritten; generate a new folder.

Clips are mono 22050 Hz PCM16 with silence trimming and short fades. The manifest maps token/phrase keys to safe hashed filenames and SHA256 digests. Playback checks file size, format, path and digest and bounds assembled audio to two minutes, before the coordinator enforces the configured transmit limit. No executable files or download URLs are accepted in a pack.


## ElevenLabs generation

The desktop Speech screen includes Generate ElevenLabs recorded voice with a session only key, account voice lookup, editable voice/model IDs, custom intro and progress/cancel/resume. It produces the same Recorded manifest and mono 22050 Hz PCM16 WAV assets as the Piper builder. Normal playback does not contact ElevenLabs. No ElevenLabs key or generated voice is included in the application or public workflow.

For a developer workflow, run the following from the repository. The script prompts for the key without echoing it. `ELEVENLABS_API_KEY` is also accepted as an environment variable; keys are never command line arguments.

```powershell
python scripts/build_elevenlabs_pack.py --voice-id YOUR_VOICE_ID --model-id eleven_multilingual_v2 --label "My ElevenLabs voice" --output C:\DXTalkerVoices\elevenlabs --intro "New DX on"
```

This consumes account credits for the standard vocabulary and optional intro. Each completed clip is hashed and recorded in a generation journal, allowing an interrupted batch to resume with the same settings. Changed voice settings require a new destination. Completed packs are not overwritten. A cancelled or failed request can already have incurred usage, so requests are not automatically retried. The fixed HTTPS API host does not allow redirects with the key. Responses and individual audio clips are bounded. The client requests `pcm_22050` and wraps the returned mono PCM16 in WAV containers, then trims silence and applies short fades.

The pack includes PROVENANCE.txt with the voice and model IDs. This does not grant redistribution rights. Review your account plan and voice permissions before sharing a pack. API key permission, credits, real voice pronunciation and listening quality require an account test. The project’s tests use synthetic PCM and mocked HTTP responses, not a paid API request.

API references: [Create speech](https://elevenlabs.io/docs/api-reference/text-to-speech/convert) and [List voices](https://elevenlabs.io/docs/api-reference/voices/search).
