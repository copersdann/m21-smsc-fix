#!/usr/bin/env python3
"""Patch libsec-ril.so so SmsManager::OnGetSmscAddressDone uses the default SMSC.

Encountered on Samsung Exynos devices (SM-M215F) on LineageOS/crDroid 22/23/24
(Android 15-17): SEND_SMS fails with SYSTEM_ERR / error 108 because
OnGetSmscAddressDone returns an invalid-SMSC error. The upstream fix used by
Exynos7870-labs R5 is "Patched libsec-ril to use the default SMSC".

Byte patch (AArch64):
    mov x3, x21   (e3 03 15 aa)  ->  mov x3, #0x0  (03 00 80 d2)
at virtual address 0x281370 of libsec-ril.so from vendor M215FXXU3CWB1.

Usage:
    python3 apply_smsc_patch.py --input libsec-ril.so.orig --output libsec-ril.so

The input file is YOUR OWN copy of the proprietary library from your device.
This repository does not distribute any Samsung binaries.
"""
import argparse
import struct
import sys

PATCH_VA = 0x281370
OLD = bytes.fromhex("e30315aa")  # mov x3, x21
NEW = bytes.fromhex("030080d2")  # mov x3, #0x0  (movz x3, #0)


def va_to_offset(data: bytes, va: int) -> int:
    if data[:8] != b"\x7fELF\x02\x01\x01\x00":
        raise ValueError("expected an ELF64 little-endian ARM64 file")
    e_phoff = struct.unpack_from("<Q", data, 0x20)[0]
    e_phentsize = struct.unpack_from("<H", data, 0x36)[0]
    e_phnum = struct.unpack_from("<H", data, 0x38)[0]
    for i in range(e_phnum):
        base = e_phoff + i * e_phentsize
        p_type = struct.unpack_from("<I", data, base)[0]
        p_offset = struct.unpack_from("<Q", data, base + 8)[0]
        p_vaddr = struct.unpack_from("<Q", data, base + 16)[0]
        p_filesz = struct.unpack_from("<Q", data, base + 32)[0]
        if p_type == 1 and p_vaddr <= va < p_vaddr + p_filesz:  # PT_LOAD
            return p_offset + (va - p_vaddr)
    raise ValueError(f"VA {va:#x} is not mapped by any PT_LOAD segment")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="path to your libsec-ril.so")
    ap.add_argument("--output", help="patched output path (default: <input>.patched)")
    ap.add_argument("--verify-only", action="store_true", help="only check, do not write")
    args = ap.parse_args()

    data = open(args.input, "rb").read()
    off = va_to_offset(data, PATCH_VA)
    current = data[off:off + 4]
    print(f"input      : {args.input}")
    print(f"file offset: {off:#x} (VA {PATCH_VA:#x})")
    print(f"bytes      : {current.hex()}")

    if current == NEW:
        print("already patched")
        return 0
    if current != OLD:
        print(f"unexpected bytes: expected {OLD.hex()}, got {current.hex()}", file=sys.stderr)
        print("This patch is for libsec-ril.so from vendor M215FXXU3CWB1 (SM-M215F).")
        print("For other builds, locate the instruction in OnGetSmscAddressDone first.", file=sys.stderr)
        return 2
    if args.verify_only:
        print("PATCHABLE (verify-only)")
        return 0

    out = args.output or (args.input + ".patched")
    patched = bytearray(data)
    patched[off:off + 4] = NEW
    with open(out, "wb") as f:
        f.write(patched)
    print(f"patched    : {out}")
    print(f"bytes now  : {bytes(patched[off:off+4]).hex()}")
    print("Verify with: aarch64-linux-gnu-objdump -d -C <out> | grep 281370")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
