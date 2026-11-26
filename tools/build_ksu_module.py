#!/usr/bin/env python3
"""Build a KernelSU/Magisk module that bind-mounts your patched libsec-ril.so.

Why a module instead of replacing /vendor? On these devices /vendor is a
read-only EROFS partition and KSU's in-kernel overlay may not mount modules.
The module's service.sh bind-mounts the patched library from /data/adb/modules
onto /vendor/lib64/libsec-ril.so and restarts rild, so rild loads the patch.

Usage:
    python3 build_ksu_module.py --lib /path/to/libsec-ril.so.patched --out m21_smsc_fix.zip
"""
import argparse
import os
import stat
import zipfile

SERVICE = """#!/system/bin/sh
# Bind-mount patched libsec-ril over vendor (KSU overlay is unreliable here).
MOD=/data/adb/modules/m21_smsc_fix
LIB="$MOD/system/vendor/lib64/libsec-ril.so"
TARGET=/vendor/lib64/libsec-ril.so
for i in 1 2 3 4 5 6 7 8 9 10; do
  [ -f "$TARGET" ] && break
  sleep 2
done
mount -o bind "$LIB" "$TARGET"
PID=$(pidof rild)
[ -n "$PID" ] && kill -9 $PID
"""

MODULE_PROP = """id=m21_smsc_fix
name=M21 SMSC Fix (libsec-ril)
version=v1.0
versionCode=1
author=opencode
description=Patched libsec-ril: OnGetSmscAddressDone uses default SMSC. Fixes SEND_SMS SYSTEM_ERR.
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lib", required=True, help="your patched libsec-ril.so")
    ap.add_argument("--out", required=True, help="output module ZIP")
    args = ap.parse_args()
    lib = os.path.abspath(args.lib)
    out = os.path.abspath(args.out)
    if not os.path.isfile(lib):
        print(f"not found: {lib}")
        return 2
    if open(lib, "rb").read(4) != b"\x7fELF":
        print("input is not an ELF file")
        return 2
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    if os.path.exists(out):
        os.remove(out)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("module.prop", MODULE_PROP)
        zi = zipfile.ZipInfo("service.sh")
        zi.external_attr = (stat.S_IFREG | 0o755) << 16
        z.writestr(zi, SERVICE)
        z.write(lib, "system/vendor/lib64/libsec-ril.so")
    print(f"module: {out} ({os.path.getsize(out)} bytes)")
    print("Install: ksud module install <zip> (or via Magisk/KernelSU manager), then reboot.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
