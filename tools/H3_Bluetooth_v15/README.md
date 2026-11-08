# V15 Bluetooth ConfigStore kaydı — offline aday

## Sorun ve kanıt

V14 logunda Bluetooth thread'i vendor.qti.hardware.btconfigstore@2.0::IBTConfigStore/default için bekliyor; BLE_START_TIMEOUT/BLE_STOP_TIMEOUT sonrası process yeniden başlıyor. Çalışan HCI1.0/SAR1.1 kayıtları var; ConfigStore manifestte tanımlı ama kayıtlı görünmüyor.

bluetooth-reference-v1 paketindeki 22 dosyanın hash'i doğrulandı. Vendor hem 1.0 hem 2.0 ConfigStore implementasyonlarını içeriyor. Servis ikilisi libqti_vndfwk_detect.so/getVendorEnhancedInfo kullanıyor; main içinde dönüş değerinin bit0'ı w19'a alınır. HCI ve SAR kayıtları koşulsuz; FM/ANT ayrı koşullu blokta; ConfigStore2.0 ve mevcut 1.0 fallback bloğu 0x22ec adresindeki cbz w19,0x23e0 ile atlanabiliyor. ConfigStore2.0 kaydı başarısız olursa mevcut kod 1.0'ı deniyor.

Bu, gözlenen eksik kayıt için somut bir yazılım koşulu. Canlı getVendorEnhancedInfo dönüş değeri ve erken registration hata mesajları yakalanmadı; bu nedenle koşulun mevcut cihazda tek neden olduğu veya patch'in kesin çözüm olduğu henüz kanıtlanmadı. Aday, manifestte ilan edilen ve vendor'da var olan ConfigStore'u framework-enhanced bitinden bağımsız kaydetmeyi dener; kayıt hatalarını gizlemez.

## Kapsam

- Hedef /vendor/bin/hw/android.hardware.bluetooth@1.0-service-qti, 15912 bayt.
- Kaynak SHA256 a96b72946f161eb0e585a86386d0913175c40ecb88da66853434fddaf86a0b7b.
- VA/dosya offset 0x22ec: b3070034 (cbz w19,0x23e0) -> 1f2003d5 (nop).
- Aday SHA256 fd4ef96ba17e49eb259bbe673d7b7709dc1e40badc961e8bd3d6caa997cab59a.
- Yalnız .text içindeki dört bayt değişir. FM/ANT koşulları, HCI/SAR, ConfigStore2.0 gerçek implementasyonu ve 1.0 fallback korunur. getVendorEnhancedInfo sonucu değiştirilmez; başarılı kayıt cevabı uydurulmaz.
- APEX veya APK değiştirilmez; imza değişikliği yok. SELinux politikası/manifest değişmez.

## Offline kontroller

Capstone ile tek branch ve yeni nop doğrulandı; diğer section ve byte'lar aynı. Unicorn ARM64 main-flow fixture'larında orijinal/yamalı servis enhanced=0/1, ConfigStore2.0 success/failure ve 1.0 fallback ile karşılaştırıldı. enhanced=0 için yalnız ConfigStore kayıt denemesi ekleniyor; enhanced=1 akışları aynı; FM/ANT gating korunuyor. Dış registration çağrıları taklit edildi: gerçek HIDL/Binder/driver testi yapılmadı.

32 MiB ext4 fixture üzerinde gerçek servis dosyası ve security.selinux xattr ile imaj kurucusu test edildi. Yalnız dört data byte'ı değişti; inode/xattr aynı; kaynak/aday e2fsck temiz; geri okunan dosya hash'i doğru. Yanlış, kesik veya zaten yamalı kaynak reddedilir. Bu fixture gerçek vendor'ın yerine geçmez.

## İmaj kurucusu

build_vendor.py yalnız doğrulanmış V14 vendor imajını kabul eder: b03c5cbf02807164b2c7338b40b81c925f73f1567f0ba94131f4657ac32bdccd. Böylece V14 OEM düzeltmesi korunur. Aynı dizinde prepare.py gerekir; Python3.11+, debugfs ve e2fsck kullanır.

Kaynak image read-only; ayrı kopyada bmap ile eşlenen dört byte değiştirilir. İmajın tamamı karşılaştırılır, inode/stat/xattr aynı kalmalı, kaynak hash'i korunmalı, kaynak ve aday read-only fscheck geçmeli, aday dosya dump hash'i eşleşmeli. Başarıda vendor-ginkgo-v15.img ve validation.json oluşur. Mevcut output dizini reddedilir. .partial dosyası geçerli flash adayı değildir. ADB/fastboot çağrılmaz.

İmaj AVB imzasını yeniden üretmez; mevcut çalışan boot/fstab doğrulama düzeni ve geri dönüş korunmalı. V14 vendor test imajı geri dönüş adayıdır; doğrulanmış pre-V14 vendor yedeği de saklanmalı. System/boot/data değiştirilmemeli.

## Cihaz kabulü — henüz yapılmadı

ConfigStore2.0 lshal'de gerçek kayıtlı servis olarak görünmeli; beş dakika boyunca Bluetooth restart/timeout döngüsü olmamalı. Aç/kapat, tarama, eşleştirme, kulaklık A2DP/HFP, çağrı sesi, dosya aktarımı/BLE, Wi-Fi birlikte kullanım ve uyku/uyanma denenmeli. V14 PIN/telefon/şebeke davranışı bozulmamalı. Başarısız 2.0 kaydı, 1.0 fallback veya SELinux reddi ayrıca incelenmeli; blanket allow eklenmemeli. Cihaz testi olmadan aday başarılı ilan edilmez.
