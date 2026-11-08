param([Parameter(Mandatory=$true)][string]$Source,[Parameter(Mandatory=$true)][string]$Destination)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class XPIconHandle {
    [DllImport("user32.dll")] public static extern bool DestroyIcon(IntPtr handle);
}
'@
$image = [System.Drawing.Image]::FromFile($Source)
$bitmap = [System.Drawing.Bitmap]::new($image, 32, 32)
$handle = $bitmap.GetHicon()
$icon = [System.Drawing.Icon]::FromHandle($handle)
$output = [System.IO.File]::Create($Destination)
try { $icon.Save($output) }
finally {
    $output.Dispose(); $icon.Dispose(); [XPIconHandle]::DestroyIcon($handle) | Out-Null
    $bitmap.Dispose(); $image.Dispose()
}
