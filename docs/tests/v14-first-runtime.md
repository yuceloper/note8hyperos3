# V14 ilk cihaz gözlemi — 2026-11-08

## İmaj ve geri dönüş

Kullanıcı V14 vendor imajını üretti: b03c5cbf02807164b2c7338b40b81c925f73f1567f0ba94131f4657ac32bdccd. İmaj kurucusu tam imaj farkını, inode/xattr değişmediğini, geri çıkarılan aday hash'ini ve salt okunur fscheck sonuçlarını doğrulayarak tamamlandı. Flash öncesi recovery'de alınan tam vendor yedeğinin SHA256 değeri kaynakla aynı: e8f49bb8c25cb983caee5249ba08b4c72c74fa68600538d13e5fa5e69fd505f6. Mac yedeği out/backups/pre-v14-20261108-161325/vendor.img.

Kullanıcı flash sonrası PIN ekranının telefon açılır açılmaz geldiğini, şebeke ve genel toparlanmanın yaklaşık bir dakika sürdüğünü bildirdi. Kurulu vendor kütüphane hash'ini shell'den okumak Permission denied ile engellendi; runtime kütüphane hash'i henüz bağımsız doğrulanmadı. Tek açılışla kalıcı başarı veya nedensellik kesinleşmez.

## Yaklaşık 288 saniyelik çalışma süresinde

- sys.boot_completed=1.
- ActivityManager lastanr: no ANR has occurred since boot. Önceki V13 ANR bulgularının aksine bu açılışta raporlanmış ANR yok; bu sonuç crash/yeniden başlama olmadığına tek başına kanıt değildir.
- Telefon PID3152; SIM LOADED,ABSENT ve Vodafone TR bildirilmiş.
- top: 800% toplam ölçeğinde 768% idle; ölçüm anında bütün CPU'ların doygunluğuna kanıt yok. Bu ölçüm ilk bir dakikanın yükünü temsil etmez.
- MemAvailable 1,069,504 KiB (~1.02 GiB); swap kullanımı ~636 MiB. MemFree'nin ~67 MiB olması tek başına OOM kanıtı değil.
- İlk paylaşılan crash kaydında 16:25:39 PID4299 init-domain SIGABRT ve crash_dump helper hatası devam ediyor. Servisin kimliği ve gecikmeyle ilişkisi belirlenmedi.

## Radyo kaydının sınırı

Paylaşılan bölüm yalnız son 150 radio satırı: 16:26:20.684–16:28:30.625. PIN giriş anı ve ilk şebeke kayıt geçişi yakalamada yok; bir dakikalık gecikmenin kaynağı bu kesitle ölçülemez.

16:26:20.709 slot 0 için inService:true; LTE sinyal bildirimi geliyor (RSRP -109 dBm). isDelayNotifySignalStrength:false: bu satırda sinyal bildirimi geciktirme aktif değil; bütün açılış için genellenemez. IMS capability available:true, regTech=0 kaydı var, ama bu gerçek arama/ses/VoLTE regresyon testi değildir.

slot 1, subId=-1 ve önceki ABSENT durumuyla tutarlı biçimde boş cell-info döndürüyor; 64/128 saniyelik yeniden denemeler boş ikinci slot için. Bunu takılı SIM'in şebeke aramasıyla karıştırmamak gerekir.

NR alanındaki 2147483647 geçerli bir RSRP ölçümü değil; NR/VoNR unsupported satırlarından LTE yolunun bozuk olduğu sonucu çıkarılmaz. Wi-Fi VALIDATED kaydı mobil veri bağlantısının testi sayılmaz.

## Fastboot yeniden başlatma ayrı sorun

Kullanıcı fastboot reboot'un Rebooting yazısında takıldığını ve ancak elle yeniden başlatınca USB okuma hatası oluştuğunu açıkladı. USB'nin komut sırasında kendiliğinden koptuğu yönündeki önceki açıklama geri alındı. Bu durum, tamamlanmış flash'ın başarısız olduğu anlamına gelmez; bootloader/host reboot takılması ayrıca araştırılmalı.

## Durum

V14: ilk cihaz gözlemi olumlu, PIN gecikmesi kullanıcıya göre belirgin azaldı ve bu boot'ta raporlanmış ANR yok. Beş açılış, PIN/sinyal zaman çizelgesi ve arama/ses/SMS/veri testleri tamamlanmadı. Genel akıcılık, ilk dakika gecikmesi ve init alt süreç çökmesi çözülmüş değil. Yeni ayar veya V15 yaması için bu kesit yeterli kanıt sağlamıyor.
