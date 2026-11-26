# SMSC Fix для m21 — патч libsec-ril (KernelSU-модуль)

## Суть (найдено в XDA и подтверждено upstream-релизом)

Проблема `SEND_SMS → SYSTEM_ERR (error 108)` на Samsung Exynos с LineageOS/crDroid 17–23 вызывается тем, что `libsec-ril.so` возвращает ошибку в `SmsManager::OnGetSmscAddressDone` (`OnGetSmscAddressDone: failed. (7)` — `RESULT_RIL_INVALID_SMSC_ADDRESS`), поэтому SMSC остаётся пустым и отправка падает.

**Upstream-фикс** (релиз Exynos7870-labs `a3y17lte-22_R5` / `j5y17lte-22_R2`): *"Patched libsec-ril to use the default SMSC"*.

**Точный байт-патч** (из XDA `xdaforums.com/t/solved-gsi-related-can-not-receive-sms.4636173`):
- В `SmsManager::OnGetSmscAddressDone(AsyncResult*)` по адресу `0x281370` заменить
  `mov x3, x21` (`e3 03 15 aa`) → `mov x3, #0x0` (`03 00 80 d2`).
- Это заставляет RIL использовать SMSC по умолчанию.

## Что сделано

- Библиотека взята с текущего crDroid 17: `/vendor/lib64/libsec-ril.so` (6 139 137 B, vendor `M215FXXU3CWB1`).
- Дизассемблировано `aarch64-linux-gnu-objdump`.
- Патч применён и проверен: дизассемблер показывает `281370: d2800003 mov x3, #0x0`.
- Собран KernelSU-модуль `KSU_SMSC_Fix.zip` (1.8 МБ) с `system/vendor/lib64/libsec-ril.so`.
- Скрипт: `C:\Users\Admin\AppData\Local\Temp\opencode\patchwork\make_patch.sh`.

## Файлы

- `C:\Users\Admin\AppData\Local\Temp\opencode\patchwork\KSU_SMSC_Fix.zip` — модуль для прошивки
- `libsec-ril.so.orig` — оригинал
- `libsec-ril.so` — пропатченный
- `libsec-ril.orig.asm` — дизассемблер

## Как прошить (потом)

```
adb push KSU_SMSC_Fix.zip /sdcard/Download/
adb shell su -c 'ksud module install /sdcard/Download/KSU_SMSC_Fix.zip'
adb reboot
```
Затем проверить `m21_send_test_sms` и logcat на `OnGetSmscAddressDone`.

## ✅ РЕЗУЛЬТАТ (2026-11-25)

- Модуль `KSU_SMSC_Fix_v2.zip` **прошит и активен**. Поскольку KSU-оверлей не монтируется на этом ядре, в модуль добавлен `service.sh`, который при каждой загрузке делает `mount -o bind` пропатченной библиотеки на `/vendor/lib64/libsec-ril.so` и перезапускает `rild`.
- После перезагрузки хэш `/vendor/lib64/libsec-ril.so` = `c82018fc...` (патченный) — применение автоматическое.
- Отправка SMS **работает**: лог `RILJ: [0410]< SEND_SMS { mMessageRef = 104, mErrorCode = 0 }`, `SYSTEM_ERR` больше нет.

**Второй найденный баг:** в MCP `m21_send_test_sms` использовался код метода `4` (`sendDataForSubscriber`) вместо `5` (`sendTextForSubscriber`) — из-за чего `service call` возвращал «Parceled data not fully consumed». Исправлено и пересобрано.

**Приложение SMSC Tool:** собрано с выбором SIM 1 / SIM 2, кнопками «Прочитать» / «Записать» / «Открыть *#*#4636#*#*», областью статуса. Root в приложении требует добавления `com.opencode.smstool` в allow-лист KernelSU (менеджер KSU → Superuser → приложение → Grant). APK: `SmscTool-build\SmscTool.apk`.

**Итоговая причина SMS-проблемы:** `SmsManager::OnGetSmscAddressDone` в `libsec-ril.so` возвращал ошибку → SMSC не инициализировался → `SEND_SMS` падал с `SYSTEM_ERR`. Патч `mov x3, #0` (использовать SMSC по умолчанию) решает проблему —这正是 upstream-фикс из релиза Exynos7870-labs R5.
