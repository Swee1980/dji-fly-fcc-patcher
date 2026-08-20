# DJI Fly FCC Patcher

Patches `libsdk_jni.so` in the DJI Fly Android APK to force FCC regulatory mode regardless of GPS location.

## What it does

DJI Fly determines the radio regulatory region (FCC/CE/SRRC) based on your phone's GPS, mobile carrier, and IP geolocation. This patcher overrides that at two points in the native SDK:

- **AreaCodeLogic::UpdateAreaCode** — forces "US" area code upstream, affecting all internal observers (frequency band selection, ground-to-sky sync, etc.)
- **wlm_set_country_code** — forces "US" at the WLM hardware command level

The result is FCC power levels and channel availability, no matter where you are.

## Requirements

- Python 3.8+
- [LIEF](https://lief-project.github.io/) and [Capstone](https://www.capstone-engine.org/) (`pip install lief capstone`)
- [apktool](https://apktool.org/) (in PATH or as `apktool.jar` nearby)
- `keytool` / `jarsigner` (from any JDK)
- The official DJI Fly APK (download it yourself from DJI or an APK mirror)

## Usage

```
python3 build.py path/to/DJI-Fly-official.apk
```

This will decompile, patch, rebuild, and sign the APK. Output: `DJI-Fly-FCC.apk`

Then uninstall the official DJI Fly app and sideload the patched one. No root required.

## Pre-built APK

Don't want to build it yourself? Grab one [here](https://github.com/Swee1980/fly-releases/releases).

## Tested

- DJI Fly v1.21.8 (arm64-v8a)

## Disclaimer

This tool is provided for educational and research purposes. Modifying radio transmission parameters may violate local regulations. You are solely responsible for ensuring compliance with the laws in your jurisdiction. This project is not affiliated with or endorsed by DJI. Use at your own risk — it may void your warranty and DJI Care Refresh coverage.

## License

AGPL-3.0
