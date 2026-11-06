DX Talker 0.2.0a10 fixes an intermittent audio playback warning and improves playback diagnostics.

The app could report RuntimeError when an audio stream finished normally between its completion wait and native state check. Playback now handles that interleaving and gives a completed buffer a bounded interval for its completion notification. Cancellation, maximum duration, genuine early stops, incomplete audio and driver faults still stop output. RF still attempts PTT release and requires deliberate restart.

Known playback failures now show readable guidance instead of only RuntimeError. Exported reports include a fixed cause code, queued versus expected audio frames, sample rate, channel count and local/radio route without audio samples, device names or credentials. Existing profiles and speech choices are preserved. Android is unchanged by this Windows playback fix.
