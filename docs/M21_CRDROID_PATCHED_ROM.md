# crDroid 17 + SMSC-патч + KernelSU — единый установочный ZIP

## Что это

Готовый прошивочный ZIP, в который уже встроено:
1. **crDroid 17.0** (ROM version 13.1, Android 17, SPL 2026-11-01) — без изменений partitions
2. **KernelSU** — заменён `boot.img` на уже пропатченный (взятый с рабочего устройства)
3. **SMSC RIL fix** — пропатченный `libsec-ril.so` и `service.sh` для bind-mount; файлы распаковываются `updater-script` в `/data/adb/modules/smsc_fix_m21` при прошивке

## Файлы

| Место | Файл | SHA-256 |
|---|---|---|
| ПК | `G:\08_Прошивки\Android\AndroidBuilds\ROMs\crDroidAndroid-17.0-20261111-m21-v13.1-SMSC-KSU.zip` | `0AC7B6A7A7261253043F7058CF0643388641802BE22F39CC4A0B9C85C4A3D7B6` |
| Телефон | `/sdcard/Download/crDroid-17-SMSC-KSU.zip` | тот же |

Размер: 1 331 116 396 байт (1.24 ГБ).

## Установка

1. TWRP → Wipe → Format Data (если нужна чистая установка).
2. Install → выбрать `crDroid-17-SMSC-KSU.zip` → прошить.
3. Reboot to System.
4. **Отдельно прошивать Everline-KSU НЕ НУЖНО** — KSU уже в `boot.img`.
5. **Отдельно ставить SMSC-патч НЕ НУЖНО** — он распакован updater-script.

## Что происходит при загрузке

`service.sh` из встроенного модуля:
```
mount -o bind /data/adb/modules/smsc_fix_m21/system/vendor/lib64/libsec-ril.so /vendor/lib64/libsec-ril.so
pid=$(pidof rild); kill -9 $pid
```
→ `rild` загружает пропатченную библиотеку → `SmsManager::OnGetSmscAddressDone` использует SMSC по умолчанию → SMS отправляются (`mErrorCode=0`).

## Почему KSU-модуль, а не «просто файлы»

В `boot` этого устройства только GKI-ramdisk (`init` + `fstab`), раздела `vendor_boot` нет — вписать свой скрипт в ramdisk напрямую нельзя. KSU-модуль — минимальный и рабочий способ automatize bind-mount. Для пользователя это не отдельный шаг: всё уже внутри одного ZIP прошивки.

## Проверка после прошивки

```
adb shell su -c 'sha256sum /vendor/lib64/libsec-ril.so'
# должно быть: c82018fc6be22e6c36ccc340cc9bb76f5cde3c8b395da53da95878a5d164999e
```
И отправить тестовое SMS через приложение «Сообщения».
