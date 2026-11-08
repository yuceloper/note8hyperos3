# V14 kayıt incelemesi: Bluetooth ve MTD tekrar döngüleri

Girdi: v14-startup-20261108-163622.tar.gz; logcat 31077 satır, processes 6917 satır. Kişisel ağ/cihaz kimlikleri repoya eklenmedi. 2026-11-08.

## Bluetooth: bekleme yeri belirlendi

Events kaydında 16:30:27–16:35:13 arasında com.android.bluetooth için 13 process start ve 13 process died görülüyor. Çoğu yeniden başlatma aralığı yaklaşık 12–13 saniye. Bu, crash buffer'da FATAL EXCEPTION olmadan da servis yeniden başlatma döngüsü yaşanabileceğini gösteriyor.

Örnek PID13664:

- 16:34:50.257 süreç başlatılır.
- 16:34:50.901 vendor HCI servisi BluetoothHci::initialize kaydı üretir. android.hardware.bluetooth@1.1 bulunamaması tek başına başlatmayı durdurmamış; 1.0 servisi çalışıyor.
- 16:34:51.477–51.483 vendor.qti.hardware.btconfigstore@2.0::IBTConfigStore/default kayıtsız; lazy başlatma başarısız. Bluetooth thread13746 getService içinde bekliyor.
- Her saniye aynı servisi bekleme/başlatma denemeleri sürüyor.
- 16:34:56.371 BLE_START_TIMEOUT.
- 16:35:00.378 BLE_STOP_TIMEOUT.
- 16:35:01.483 süreç ölür; 16:35:03.166 yenisi başlar.

Bu kayıt, mevcut tekrarlayan Bluetooth açılış başarısızlığında config-store servis beklemesini somut hedef yapıyor. Servis manifestte eksik mi, dosyası yok mu, kurulu ama başlatılamıyor mu, yoksa donor istemci eski vendor'ın desteklediğinden yüksek sürümü mü istiyor: envanterle ayrıştırılmalı. İzin eklemek veya sürüm metnini 2.0'dan 1.0'a körlemesine değiştirmek çözüm değil; HIDL arayüzleri eşdeğer sayılmaz.

## Find Device / MTD

PID4112 süreç dökümünde com.xiaomi.finddevice olarak eşleşiyor. Logcat içinde bu PID için:

- 1314 HIDL mtdservice find reddi, default_android_hwservice hedefi.
- 1129 AIDL IMTService/default find reddi, default_android_service hedefi.

2443 satır, iki protokol denemesinin SELinux audit log biçimlerine göre sayımıdır; bağımsız 2443 kullanıcı işlemi anlamına gelmez. Bu, kalıcı servis erişim/tekrar sorunu; CPU etkisi yalnız satır sayısından ölçülemez. Default etiketlere genel find izni eklenmemeli. Gerçek MTD servisinin varlığı, doğru context, VINTF ve ihtiyaç duyduğu storage izinleri birlikte doğrulanmalı. Find Device kapatma veya sahte başarı önerilmiyor.

## Telefon ve şebeke

Bu kesitte am_anr/am_crash veya Telefon process restart kaydı bulunmadı; önceki lastanr de boot'tan beri ANR olmadığını bildiriyor. Ana süreç PID3152 devam ediyor. OEM başlangıç satırları ring buffer'da kalmamış; installed-library hash'i shell engeli yüzünden okunmadı. V14 etkisi için olumlu ilk gözlem var, beş açılış testi yok.

Radyo kaydı 16:26:01.787'den itibaren kalmış; PIN ve ilk kayıt geçişi yok. 16:26:02.255'te slot0 voice/data IN_SERVICE ve LTE görülüyor. ServiceStateAnalytics daha önce başlamış IN_SERVICE aralığı raporlayabiliyor; bunun başlangıcını tam PIN zamanıyla eşlemek bu kesitte mümkün değil. Dolayısıyla bildirilen bir dakikalık şebeke beklemesinin kaynağı hâlâ belirsiz.

## Sıra

V14 korunur. Önce Bluetooth config-store servis/istemci sürüm uyumu incelenir; sonra MTD servis entegrasyonu. Init-domain PID4299 SIGABRT'nin servis kimliği hâlâ bulunamadı. Her ikisi genel akıcılığı bozabilecek tekrar işlerini azaltmak için somut hedeflerdir; akıcılık üzerindeki etkileri kontrollü test gerektirir.
