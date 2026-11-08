# V13 ilk cihaz ölçümü

Tarih: 2026-11-08. Kullanıcının cihaz çıktısından özet; kontrollü A/B testi değil.

Paketlenen system SHA256: `0ea573631092bec771c6754c28f2a8143a6de0168fa5ac908b14d53c29a33216`.
Beklenen perf kütüphanesi SHA256: `c03f761417871e9b14102cf49669bff8bd60c12715b26b8b9a617cb8e3d6675a`. Bu sonuç mesajında cihazdan sha256sum verilmedi; kurulu dosya hash'i ayrıca doğrulanmalı.

USB kopmasıyla yarım kalan flash sonrası fastboot iletişimi yeniden kuruldu, kullanıcıya tüm system imajını baştan yazma talimatı verildi. Sonraki runtime çıktısı Android'in çalıştığını gösteriyor; tam fastboot bitiş çıktısı bu kayıtta yok.

| Ölçüm | Launcher | SystemUI |
| --- | --- | --- |
| Kare | 2848 | 10797 |
| Jank | 83 (%2.91) | 108 (%1.00) |
| Legacy jank | 380 (%13.34) | 1657 (%15.35) |
| p50 | 16 ms | 18 ms |
| p90 | 26 ms | 28 ms |
| p95 | 44 ms | 32 ms |
| p99 | 150 ms | 129 ms |
| GPU p50 | 5 ms | 10 ms |
| GPU p90 | 16 ms | 13 ms |
| GPU p95 | 18 ms | 13 ms |
| GPU p99 | 20 ms | 17 ms |

Pipeline: Skia OpenGL. İki SystemUI bloğu aynı verinin tekrarı; iki ayrı koşu değil.

Son 3000 all-buffer log satırında IPerf:: veya Content FPS Hint was not delivered eşleşmesi çıkmadı. Bu bütün açılış boyunca hatasızlık veya çalışan boost desteği kanıtı değil.

V12'deki SystemUI p95 150 ms ve jank %5.73 ile karşılaştırıldığında bu örnek daha iyi. Koşullar/kare sayıları farklı (V12 1013, V13 10797), sayaç sıfırlaması ve eşit senaryo doğrulanmadı; iyileşme nedensel olarak V13'e atfedilemez. Launcher p95 40→44 ms; genel performans çözümü kabul edilmedi.

Crash buffer: 05:43:01 civarında init adıyla SIGABRT; crash_dump helper exec başarısız/öldürülmüş. Önceki sürümlerde de benzer kayıt vardı. Kaynak servis belirsiz; kök neden belirlenmedi.

Sonraki kontroller: cihaz hash'i, kullanıcı akıcılık değerlendirmesi, SIM/arama/parmak izi gerileme kontrolü; eşit koşullarda tekrarlı geçiş ölçümü; init servis çıkış/başlatma kayıtlarıyla SIGABRT kaynağını bulma. PR henüz kararlı düzeltme olarak kabul edilmez.
