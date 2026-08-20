#!/usr/bin/env python3
"""
Build a patched DJI Fly APK with FCC area code forced.

Usage: python3 build.py <original.apk> [output.apk]
"""

import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
WORK_DIR = SCRIPT_DIR / "_build"
KEYSTORE = SCRIPT_DIR / "keys" / "debug.keystore"
KS_PASS = "fccmod"
KS_ALIAS = "fccmod"


def find_apktool():
    if shutil.which("apktool"):
        return ["apktool"]
    for p in [
        Path.home() / "Desktop" / "FCC dji fly" / "apktool.jar",
        SCRIPT_DIR.parent / "FCC dji fly" / "apktool.jar",
    ]:
        if p.exists():
            return ["java", "-jar", str(p)]
    raise FileNotFoundError("apktool not found")


def run(cmd, **kw):
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    r = subprocess.run(cmd, **kw)
    if r.returncode != 0:
        sys.exit(r.returncode)
    return r


def decompile(apk, out):
    print("\n[1/4] Decompiling...")
    if out.exists():
        shutil.rmtree(out)
    run([*find_apktool(), "d", "-f", "-o", str(out), str(apk)], timeout=600)


def patch_so(tree):
    print("\n[2/4] Patching libsdk_jni.so...")
    so = tree / "lib" / "arm64-v8a" / "libsdk_jni.so"
    assert so.exists(), f"{so} not found"
    tmp = so.with_suffix(".so.tmp")
    run([sys.executable, str(SCRIPT_DIR / "patcher" / "patch_so.py"), str(so), str(tmp)])
    so.unlink()
    tmp.rename(so)


def rebuild(tree, out):
    print("\n[3/4] Rebuilding APK...")
    run([*find_apktool(), "b", "-o", str(out), str(tree)], timeout=600)


def sign(unsigned, signed):
    print("\n[4/4] Signing...")
    if not KEYSTORE.exists():
        KEYSTORE.parent.mkdir(parents=True, exist_ok=True)
        run([
            "keytool", "-genkey", "-v",
            "-keystore", str(KEYSTORE), "-alias", KS_ALIAS,
            "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000",
            "-storepass", KS_PASS, "-keypass", KS_PASS,
            "-dname", "CN=Unknown, OU=Unknown, O=Unknown, L=Unknown, ST=Unknown, C=US",
        ])

    aligned = unsigned.with_suffix(".aligned.apk")
    if shutil.which("zipalign"):
        run(["zipalign", "-f", "4", str(unsigned), str(aligned)])
    else:
        shutil.copy2(unsigned, aligned)

    if shutil.which("apksigner"):
        shutil.copy2(aligned, signed)
        run(["apksigner", "sign",
             "--ks", str(KEYSTORE), "--ks-pass", f"pass:{KS_PASS}",
             "--ks-key-alias", KS_ALIAS, str(signed)])
    else:
        run(["jarsigner", "-keystore", str(KEYSTORE),
             "-storepass", KS_PASS, "-keypass", KS_PASS,
             "-signedjar", str(signed), str(aligned), KS_ALIAS])

    mb = signed.stat().st_size / 1024 / 1024
    print(f"\nDone: {signed} ({mb:.0f} MB)")


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <original.apk> [output.apk]")
        sys.exit(1)

    apk = Path(sys.argv[1]).resolve()
    assert apk.exists(), f"not found: {apk}"
    out = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else SCRIPT_DIR / "DJI-Fly-FCC.apk"

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    tree = WORK_DIR / "decompiled"
    unsigned = WORK_DIR / "unsigned.apk"

    decompile(apk, tree)
    patch_so(tree)
    rebuild(tree, unsigned)
    sign(unsigned, out)


if __name__ == '__main__':
    main()
