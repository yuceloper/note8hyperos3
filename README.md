# Redmi Note 8 — HyperOS 3 Türkiye portu

**Durum: geliştirme / test. Günlük kullanım için doğrulanmış sürüm yok.**

Hedef cihaz: Redmi Note 8 (ginkgo). Donor: creek Türkiye, HyperOS 3 OS3.0.302.0.WBOTRXM (Android 16 / SDK 36). Donanım tabanı: ginkgo LineageOS 23.2 (20261007) kernel/vendor.

Bu proje resmî Xiaomi ROM'u değildir. Açılması, tüm donanımın ve güvenlik işlevlerinin doğrulandığı anlamına gelmez.

## Proje kayıtları

- [Mevcut durum ve bilinen sorunlar](docs/STATUS.md)
- [Öncelikler ve çıkış şartları](docs/ROADMAP.md)
- [Test prosedürü ve sonuç şablonu](docs/TESTING.md)

## Repo kapsamı

Şimdilik geliştirme kayıtları bulunur. Mac'teki hazırlama betikleri, araç sürümleri ve patch kaynakları henüz bu repoya aktarılmadı; yalnızca bu repodan ROM yeniden üretilemez. Geçmiş aday adları, kaynak commit/tag anlamına gelmez.

ROM arşivleri, çıkarılmış dosya sistemleri, imajlar, özel anahtarlar ve ham cihaz kayıtları Git'e eklenmez. İleride betikler ve küçük, incelenebilir yamalar konu dalları ve PR üzerinden takip edilecek.

## Çalışma ilkeleri

Her aday tek ana hipotezi test eder. Önce kaynak hash kontrolü, yedek ve geri dönüş yolu hazırlanır. Sonuç başarılı / başarısız / belirsiz olarak kaydedilir. Yalnızca log azalması performans başarısı sayılmaz. Neverallow kontrolleri korunur; genel permissive veya sahte servis bildirimi çözüm sayılmaz.
