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

The desktop offers a shared ElevenLabs provider for live online speech and a generator for reusable Recorded packs. Testers do not enter keys. The generator uses the same private service, allowed voice list and testing allowance. The owner configures the upstream account key on DreamHost as described in [shared speech setup](../server/speech/README.md).

The generator produces the same mono 22050 Hz PCM16 WAV format and checksummed manifest as the Piper builder. Progress, cancellation and verified clip resume remain available. Normal Recorded playback never contacts the service. Voice and model provenance is retained in PROVENANCE.txt and the manifest. This grants no additional sharing rights.

The standard pack contains 77 assets plus an optional custom intro. Each generation request uses the shared account’s allowance; cached service segments can be reused across testers. A failed or cancelled request is not automatically retried and may already have consumed credits. App shutdown prevents subsequent generation requests without relying on interface callbacks.

The developer only script `scripts/build_elevenlabs_pack.py` remains available for an owner who intentionally generates directly using a private local key. It prompts privately or reads ELEVENLABS_API_KEY. It is not the tester workflow and does not embed a key in the app or pack.

API references: [Create speech](https://elevenlabs.io/docs/api-reference/text-to-speech/convert) and [List voices](https://elevenlabs.io/docs/api-reference/voices/search).
