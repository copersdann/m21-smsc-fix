# m21-smsc-fix

Fix for **SMS sending failure** on Samsung Galaxy M21 (SM-M215F, Exynos 9611)
running LineageOS / crDroid 24 (Android 17) with Samsung RIL v5.0.

## Problem

Sending SMS fails with:

```
RILJ: SEND_SMS error 39
RilRequest: SEND_SMS error: CommandException: SYSTEM_ERR
SMSDispatcher: SMS failed with error 108, errorCode 0
```

SMSC is valid, SIM is `IN_SERVICE`, CS domain reports `VOICE,SMS,VIDEO`.
The real cause is `SmsManager::OnGetSmscAddressDone` inside Samsung's
proprietary `libsec-ril.so`: it returns an invalid-SMSC error, so the SMSC is
never initialized and the modem does not answer `SEND_SMS`.

## Fix

A 4-byte AArch64 patch in `libsec-ril.so`:

```
SmsManager::OnGetSmscAddressDone(AsyncResult*)  @ VA 0x281370
    mov x3, x21   (e3 03 15 aa)   ->   mov x3, #0x0  (03 00 80 d2)
```

This makes RIL use the default SMSC. It matches the upstream fix described in
Exynos7870-labs `a3y17lte-22_R5`: *"Patched libsec-ril to use the default SMSC"*.

## Important: no binaries here

This repository contains **only scripts and documentation**. Samsung's
`libsec-ril.so` is proprietary; you must extract your own copy from your own
device and patch it locally. Nothing in this repo redistributes Samsung code.

## Usage

### 1. Get your own `libsec-ril.so`

With root (KernelSU/Magisk):

```sh
adb shell su -c 'cp /vendor/lib64/libsec-ril.so /sdcard/Download/libsec-ril.so'
adb pull /sdcard/Download/libsec-ril.so .
```

### 2. Patch it

```sh
python3 tools/apply_smsc_patch.py --input libsec-ril.so --output libsec-ril.so.patched
python3 tools/apply_smsc_patch.py --input libsec-ril.so --verify-only
```

The script maps VA `0x281370` through the ELF program headers and verifies the
original bytes. It is written for `libsec-ril.so` from vendor build
`M215FXXU3CWB1` (SM-M215F). For other builds, locate the instruction inside
`OnGetSmscAddressDone` first with an AArch64 disassembler.

### 3. Build a KernelSU module

```sh
python3 tools/build_ksu_module.py --lib libsec-ril.so.patched --out m21_smsc_fix.zip
adb push m21_smsc_fix.zip /sdcard/Download/
adb shell su -c 'ksud module install /sdcard/Download/m21_smsc_fix.zip'
adb reboot
```

The module's `service.sh` bind-mounts the patched library over `/vendor/lib64/libsec-ril.so`
and restarts `rild` at boot, because `/vendor` is read-only EROFS and KSU's
in-kernel overlay is unreliable on this kernel.

### 4. Verify

```sh
adb shell su -c 'sha256sum /vendor/lib64/libsec-ril.so'
adb shell su -c 'ksud module list'
```

Send a test SMS. In logcat you should see `SEND_SMS ... mErrorCode = 0`
and no `SYSTEM_ERR`.

## Tested environment

- Device: Samsung Galaxy M21 / SM-M215F (`m21`), Exynos 9611, 4 GB RAM
- ROM: crDroid 17.0 (ROM version 13.1), Android 17, SPL 2026-11-01
- Baseband: `M215FDDU3CVL1`
- Vendor: `samsung/m21nsxx/m21:12/SP1A.210812.016/M215FXXU3CWB1`
- Root: KernelSU 3.3.1 + NeoZygisk 2.4 + Vector 2.2
- Reference ROM used during development (not hosted here):
  `crDroidAndroid-17.0-20261111-m21-v13.1.zip`, SHA-256
  `89dceae6842db06246244f93ccc0846eddc2afd3cac8777cfc982e6dec561934`
  (patched derivative SHA-256: `0ac7b6a7a7261253043f7058cf0643388641802be22f39cc4a0b9c85c4a3d7b6`)

## Credits / license

- Scripts: MIT (see [LICENSE](LICENSE)).
- Byte-patch approach: XDA thread "Solved: GSI-related can not receive SMS"
  and Exynos7870-labs Vector/lineage_release issue #7.
- Samsung blobs, ROM and GApps remain property of their respective owners.
  This project does not distribute them.

See [docs/M21_SMSC_PATCH.md](docs/M21_SMSC_PATCH.md) for the full investigation log.
