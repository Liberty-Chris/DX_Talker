# Ubuntu desktop

The Ubuntu pilot targets Ubuntu 22.04 and 24.04 desktop on 64 bit Intel and AMD computers. Download DXTalker-Ubuntu-amd64.deb from the release page. This is not a Raspberry Pi or other ARM package. A graphical desktop session is required. Python is included in the package.

## Install and start

Close DX Talker before installing or replacing the package. In a terminal opened in the download folder, run:

```bash
sudo apt install ./DXTalker-Ubuntu-amd64.deb
```

Ubuntu installs the required system libraries and offline speech engine. Open DX Talker from the application menu, or run `dxtalker`. Do not run the application as root. Installing a new package over the existing one preserves settings. To remove it, run `sudo apt remove dxtalker`. Removal leaves your own settings and voice packs in place.

Settings, appearance, profiles, logs and downloaded updates normally live under `~/.config/dxtalker`. A configured XDG_CONFIG_HOME changes the parent folder. Export profile collections through Source for transfer to another machine or Android. Remembered passwords are excluded from transfers. Enter them again on the destination.

## Features and platform differences

The Ubuntu package uses the same desktop core for clusters, directory choices, profiles, filters, QR export, spotting, announcement formats, audio routing, receive hold, radio control, IDs, history and diagnostics. RF starts disabled. Use the ordinary help topics for these features. Mobile camera scanning is a separate Android feature.

Ubuntu uses eSpeak NG as its offline system voice. Windows System.Speech is unavailable. Choose an installed voice in Speech, adjust speed and pauses and preview through local speakers first. Piper requires a separately installed Linux executable and matching model. Recorded WAV packs and the configured ElevenLabs pilot service remain available. Voice quality and driver behavior can differ between systems.

Remember password or token uses the desktop Secret Service keyring, usually GNOME Keyring on Ubuntu. Unlock the keyring when prompted. If it is unavailable or locked, leave Remember unchecked and enter the credential for this session. DX Talker never falls back to saving the secret as plaintext. Windows protected credentials cannot be unlocked on Linux. The profile file stores only a keyring reference on Ubuntu. Replacing or deleting a remembered profile removes its old keyring entry when the keyring responds.

## Audio and serial PTT

Choose exact local output, radio output and optional receiver input names in Audio / PTT. Keep local speakers separate from a VOX radio. Preview and Test PTT are distinct operations. The Linux package uses PortAudio and pyserial through the same transmission coordinator as Windows. Physical interface compatibility still requires a bench test with the actual computer, radio and adapter.

Linux serial ports commonly appear as `/dev/ttyUSB0`, `/dev/ttyACM0` or `/dev/ttyS0`. A stable `/dev/serial/by-id/...` path can be entered for an adapter. If serial access is denied, check that the selected device belongs to the dialout group. An administrator can add your login with `sudo usermod -aG dialout "$USER"`. Sign out completely and back in before retrying. Do not launch DX Talker with sudo to work around permissions. RTS, DTR, both lines and VOX remain the available methods. A DB9 serial connector carries control signals, not radio audio.

## Updates and recovery

Check now reads the shared release feed and selects only the Ubuntu package. Download update verifies its checksum over verified HTTPS before Install update is available. Install update stops output and disconnects, then asks for administrator authentication through Ubuntu's desktop authentication agent. DX Talker closes while apt replaces the package. Reopen it from the application menu afterward. RF remains disabled on startup.

If authentication is cancelled or installation fails, reopen the existing app. Review `update-install.log` in the settings folder, or install the downloaded verified package manually with apt. You do not need to uninstall first. Package manager changes are interactive; DX Talker does not silently grant itself administrative access.

HTTPS uses Ubuntu's trusted CA bundle and checks both certificates and hostnames. A certificate error needs clock, CA package or local HTTPS filtering investigation. Certificate verification is never disabled to recover a connection.

## Verification limits

Automated checks render speech to WAV, use synthetic keyring values and visit the actual desktop pages. Installer checks cover installing, replacing and removing the package with a retained settings marker. They do not play audio, open a physical serial port or transmit. Live audio, receive monitoring, serial polarity, stop behavior, driver failures and extended operation need operator testing on each selected interface. Raspberry Pi sizing remains an estimate until a separate ARM build is measured.
