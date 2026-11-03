# Mevcut durum

Son kayıt: 2026-11-03. Kaynak: cihaz çıktıları ve kullanıcı testleri; bağımsız tam doğrulama değildir.

## Karşılaştırma sürümü: V12

- system imajı: hyperos3-ginkgo-v12-padded.img
- SHA256: 781ac1ef64c1d780b4ed23ca255a95ce0b27d09511a4b181db6f8bfa214d302e
- Boyut: 8589934592 bayt (padded).
- Politika SHA256 (V11'den korunan): 4deded9b6bd729155ed39c5e8e9c7a0673ecc9fb7a82a5c7c624c24d5d8d7475
- V12 deneysel ayarları: vendor.display.disable_content_fps_hint=1 ve vendor.display.disable_compositor_tid_hint=1.
- İmaj cihazda açıldı; iki property 1 olarak doğrulandı. Genel performans düzeltmesi kabul edilmedi.
- V13 henüz hazırlanmış veya test edilmiş değil.

## Gözlenen özellikler

| Alan | Kanıt / sınır |
| --- | --- |
| Açılış, ekran, dokunmatik | V12 açılıyor; uzun süreli güvenilirlik doğrulanmadı |
| SIM | LOADED,ABSENT ve operatör görüldü; PIN/şebeke 2–3 dakika gecikebiliyor |
| Parmak izi | V11 sonrası kullanıcı kayıt ve kilit açmanın çalıştığını bildirdi; gecikme var |
| Telefon/Mesajlar/Kişiler | V10 uygulama yolları ve Dialer destek kütüphanesi doğrulandı; arama/SMS uçtan uca testi eksik |
| Wi-Fi | Kurulumda bağlantı kuruldu; dayanıklılık testi yok |
| Google kurulumu | Elle paket etkinleştirme sonrası tamamlandı; temiz kurulum çözümü eksik |

## Açık sorunlar

1. Kamera: donor MiuiCamera model uyumsuzluğu uyarısıyla kapanıyor. Alternatif uygulamayla kamera HAL işlevi henüz doğrulanmadı.
2. Uygulama geçişleri ve SystemUI animasyonlarında takılma.
3. Qualcomm Perf HAL 2.2 / perf2 bulunamıyor; HyperOS istemcileri çağrı yapmaya devam ediyor. Bu, tüm takılmanın kanıtlanmış nedeni değil.
4. Açılışta init adıyla SIGABRT; gerçek servis kaynağı belirsiz. Crash dump yardımcısı da başarısız.
5. SIM PIN ve şebeke gecikmesi.
6. Google kurulumunda elle etkinleştirme gereksinimi.
7. Wallpaper Carousel, window type 2009 izni nedeniyle tekrarlayan çökme yaptı; kullanıcı ayarlardan kapattı. Temel neden giderilmedi.

## Performans kanıtı

Aşağıdaki koşular eşdeğer kontrollü testler değil; yalnızca başlangıç kaydıdır.

| Ölçüm | V11 Launcher | V12 Launcher | V11 SystemUI | V12 SystemUI |
| --- | --- | --- | --- | --- |
| Kare | 710 | 442 | 965 | 1013 |
| Jank | %2.25 | %3.62 | %2.59 | %5.73 |
| p50 | 16 ms | 11 ms | 15 ms | 19 ms |
| p95 | 40 ms | 40 ms | 42 ms | 150 ms |
| GPU p95 | 16 ms | 12 ms | 13 ms | 14 ms |

Güncel boşta CPU örnekleri yaklaşık %99 idle gösterdi. Bu, geçiş anındaki yükü veya beklemeyi açıklamaz. Eski dumpsys cpuinfo açılış örneği güncel yük olarak kullanılmamalı.

Vendor libqti-perfd-client.so fonksiyonları incelendi: minimal uyumluluk uygulaması; HyperOS istemcisiyle doğrudan değiştirilebilir kabul edilmiyor.

## Doğrulanmamış alanlar

Arama ve ses yolları, SMS, mobil veri, GPS fix, Bluetooth ses, hotspot, sensörler, USB aktarımı, şarj/ısı, derin uyku, gece pil tüketimi ve 48 saat kullanım. Güvenlik/şifreleme ve uygulama bütünlük uyumluluğu için de tam test yok.
