Option Explicit
Dim speaker, defaultVoice, incoming, failed
On Error Resume Next
Set speaker = CreateObject("SAPI.SpVoice")
failed = Err.Number <> 0
Err.Clear
If Not failed Then failed = speaker.GetVoices.Count = 0
If Not failed Then Set defaultVoice = speaker.Voice
If Err.Number <> 0 Then failed = True
On Error GoTo 0
If failed Then
  WScript.StdOut.WriteLine "<error/>"
  WScript.Quit 1
End If
WScript.StdOut.WriteLine "<ready/>"
Do Until WScript.StdIn.AtEndOfStream
  incoming = WScript.StdIn.ReadLine
  On Error Resume Next
  ProcessRequest incoming
  If Err.Number <> 0 Then
    Err.Clear
    WScript.StdOut.WriteLine "<error/>"
  End If
  On Error GoTo 0
Loop

Function Esc(value)
  Dim i, n, ch, output
  output = ""
  For i = 1 To Len(value)
    ch = Mid(value, i, 1)
    n = AscW(ch)
    If n < 0 Then n = n + 65536
    Select Case ch
      Case "&": output = output & "&amp;"
      Case "<": output = output & "&lt;"
      Case ">": output = output & "&gt;"
      Case """": output = output & "&quot;"
      Case Else
        If n > 127 Then
          output = output & "&#" & CStr(n) & ";"
        Else
          output = output & ch
        End If
    End Select
  Next
  Esc = output
End Function

Function GenderOf(token)
  On Error Resume Next
  GenderOf = LCase(token.GetAttribute("Gender"))
  If Err.Number <> 0 Then
    Err.Clear
    GenderOf = ""
  End If
  On Error GoTo 0
End Function

Sub ProcessRequest(text)
  Dim document, request, mode, token, tokens, i, name, gender, selected, output, stream, speech, flags, bad
  Set document = CreateObject("Msxml2.DOMDocument.3.0")
  document.async = False
  document.resolveExternals = False
  document.validateOnParse = False
  If Len(text) > 131072 Or Not document.loadXML(text) Then Err.Raise 5
  Set request = document.documentElement
  If request.nodeName <> "request" Then Err.Raise 5
  mode = request.getAttribute("mode")
  Set tokens = speaker.GetVoices
  If mode = "voices" Then
    output = "<voices>"
    For i = 0 To tokens.Count - 1
      If i >= 64 Then Exit For
      output = output & "<voice>" & Esc(Left(tokens.Item(i).GetDescription, 256)) & "</voice>"
    Next
    WScript.StdOut.WriteLine output & "</voices>"
    Exit Sub
  End If
  If mode <> "render" Then Err.Raise 5
  name = request.getAttribute("voice")
  gender = LCase(request.getAttribute("gender"))
  selected = False
  Set speaker.Voice = defaultVoice
  For i = 0 To tokens.Count - 1
    Set token = tokens.Item(i)
    If name <> "" Then
      If token.GetDescription = name Then
        Set speaker.Voice = token
        selected = True
        Exit For
      End If
    ElseIf gender <> "" And gender <> "any" Then
      If GenderOf(token) = gender Then
        Set speaker.Voice = token
        Exit For
      End If
    End If
  Next
  If name <> "" And Not selected Then Err.Raise 5
  speaker.Rate = CInt(request.getAttribute("rate"))
  speaker.AllowAudioOutputFormatChangesOnNextSet = False
  Set speech = request.selectSingleNode("speech")
  If speech Is Nothing Then Err.Raise 5
  Set stream = CreateObject("SAPI.SpFileStream")
  stream.Format.Type = 22
  stream.Open request.getAttribute("output"), 3, False
  On Error Resume Next
  Set speaker.AudioOutputStream = stream
  flags = 16
  If request.getAttribute("xml") = "1" Then flags = 8
  speaker.Speak speech.text, flags
  bad = Err.Number <> 0
  Err.Clear
  stream.Close
  If Err.Number <> 0 Then bad = True
  Err.Clear
  Set speaker.AudioOutputStream = Nothing
  Err.Clear
  On Error GoTo 0
  If bad Then Err.Raise 5
  WScript.StdOut.WriteLine "<ok voice=""" & Esc(Left(speaker.Voice.GetDescription, 256)) & """/>"
End Sub
