<div align="center">

# DJI Fly FCC Patcher

### Force FCC regulatory mode on DJI Fly for Android

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue?style=flat-square)](LICENSE)
[![GitHub release](https://img.shields.io/github/v/release/Swee1980/dji-fly-fcc-patcher?style=flat-square)](https://github.com/Swee1980/dji-fly-fcc-patcher/releases)

</div>

---

> ## Disclaimer
>
> This software is provided for educational and research purposes only. Modifying radio transmission parameters may violate laws and regulations in your country or region. You are solely responsible for ensuring that your use of this software complies with all applicable local, regional, and national laws.
>
> This project is not affiliated with, endorsed by, or sponsored by DJI. Using this tool may void your warranty and DJI Care Refresh coverage.

---

## What it does

DJI Fly selects the radio regulatory region (FCC/CE/SRRC) based on your phone's GPS, mobile carrier, and IP geolocation. This patcher overrides that at two points in the native SDK library (`libsdk_jni.so`):

| Patch point | Effect |
|-------------|--------|
| **AreaCodeLogic::UpdateAreaCode** | Forces "US" area code upstream, affecting all internal observers (frequency band selection, ground-to-sky sync, etc.) |
| **wlm_set_country_code** | Forces "US" at the WLM hardware command level |

The result is FCC power levels and channel availability regardless of physical location.

## Requirements

- Python 3.8+
- [LIEF](https://lief-project.github.io/) and [Capstone](https://www.capstone-engine.org/) — `pip install lief capstone`
- [apktool](https://apktool.org/) (in PATH or as `apktool.jar` nearby)
- `keytool` / `jarsigner` (from any JDK)
- The official DJI Fly APK (download from DJI or an APK mirror)

## Usage

```
python3 build.py path/to/DJI-Fly-official.apk
```

This will decompile, patch, rebuild, and sign the APK. Output: `DJI-Fly-FCC.apk`

Uninstall the official DJI Fly app and sideload the patched APK. No root required.

> Only the patcher is provided in this repo. You are encouraged to build the [apk](https://github.com/Swee1980/fly-releases/releases) yourself.

## Compatibility

| DJI Fly version | Arch | Status |
|-----------------|------|--------|
| v1.21.8 | arm64-v8a | Tested, working |

Other versions may work but are untested. If you test on a different version, please [open an issue](https://github.com/Swee1980/dji-fly-fcc-patcher/issues).

## How it works

The patcher uses LIEF to parse the ELF binary and Capstone to disassemble ARM64 instructions. It locates the two target functions by signature, then patches the relevant instructions to hardcode the US/FCC country code. The patched `.so` is swapped back into the APK, which is then rebuilt and signed with a debug keystore.

## Project structure

```
build.py              End-to-end build script (decompile → patch → rebuild → sign)
patcher/patch_so.py   Binary patcher (ELF parsing, disassembly, instruction patching)
keys/                 Debug keystore for signing (auto-generated on first run)
```

## Support

If this project helped you out, please consider starring the repo. It helps with visibility and lets others find it.

[![Star on GitHub](https://img.shields.io/badge/Star%20on%20GitHub-%E2%AD%90-yellow?style=for-the-badge&logo=github)](https://github.com/Swee1980/dji-fly-fcc-patcher)

## Contact

Questions, issues, or feedback?

- **GitHub Issues:** [github.com/Swee1980/dji-fly-fcc-patcher/issues](https://github.com/Swee1980/dji-fly-fcc-patcher/issues)

## License

AGPL-3.0. See [LICENSE](LICENSE).
