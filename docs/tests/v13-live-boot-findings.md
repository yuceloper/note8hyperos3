# V13 canlı açılış: telefon ANR ve Bluetooth zaman aşımı

2026-11-08, kullanıcı tarafından sağlanan iki dakikalık canlı açılış kaydının incelenmesi. Ham kayıt kişisel bilgiler içerebildiğinden repoya alınmadı.

## Doğrulanan bulgular

- sys.boot_completed=1. Kurulu perf kütüphanesi SHA256 önceki cihaz çıktısında c03f761417871e9b14102cf49669bff8bd60c12715b26b8b9a617cb8e3d6675a olarak doğrulandı.
- 05:54:22.169: PID 4073 init adıyla SIGABRT. crash_dump ptrace reddi var; servis adı/abort nedeni logcat'te yok. kernel.txt boş. Ana init PID 1 çalışmaya devam ediyor.
- 05:54:27.287: com.android.phone PID 3170 için ANR. Sebep satırı: com.android.internal.stk.command yayını, com.android.stk/.StkCmdReceiver.
- 05:54:27.313: sistem telefon sürecini bg anr nedeniyle öldürüyor. Süreç daha sonra PID 4558 olarak yeniden başlıyor. Bu olay SIM gecikmesi için somut bir katkı adayıdır; ANR'nin kök nedeni henüz bilinmiyor. Yayının STK olması tek başına STK kodunun kusurlu olduğunu kanıtlamaz; main-thread stack gerekli.
- 05:55:00.787: yeniden başlayan telefon sürecinde SIM0 PIN_REQUIRED; 05:55:00.946: SystemUI bunu alıyor. Bu koşudaki süreler cihaz saatindeki olay farklarıdır; toplam boot süresi olarak yorumlanmamalı.
- Bluetooth: 05:54:19.199, 05:54:31.394, 05:54:43.740, 05:54:56.516 BLE_START_TIMEOUT. Ardından BLE_STOP_TIMEOUT ve süreç yeniden başlatmaları. Bluetooth çalışıyor olarak işaretlenemez.

## Sonraki adımlar

Öncelik: telefon ANR main-thread stack'ini DropBox/lastanr veya mevcut /data/anr kaydından al. Bluetooth başlangıç kilitlenmesini ayrıca incele. STK'yı kaldırma/devre dışı bırakma veya genel SELinux izni ekleme bu kayıtlarla gerekçelendirilemez. Init çökmesi açık kalır; crash_dump'a init ptrace izni eklemek henüz kök neden çözümü değildir.
