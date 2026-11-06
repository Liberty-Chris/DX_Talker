Option Explicit
Dim voice
Set voice = CreateObject("SAPI.SpVoice")
voice.Speak WScript.Arguments(0)
