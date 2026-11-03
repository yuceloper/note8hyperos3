# Test prosedürü

Bu liste planı gösterir; işaretlenmemiş maddeler başarılı sayılmaz. Acil numaralara test araması yapılmaz.

## Her aday için kayıt

- Tarih, cihaz modeli (seri numarası gerekmez), Git commit ve aday adı.
- system/boot/vendor hash'leri; hangi bölümlerin değiştiği.
- Temiz kurulum / veri korunarak güncelleme.
- Hipotez, değişiklik, beklenen sonuç, geri alma yolu.
- Sonuç: başarılı / başarısız / belirsiz; ham kayıtların yerel yolu.
- Ortam: pil/şarj durumu, ısı, ağ, ekran ayarı ve açılıştan geçen süre.

Kişisel verileri, numaraları, IMSI/IMEI/seri numaralarını, Wi-Fi bilgilerini, hesapları ve anahtarları ham loglarla public repoya yüklemeyin. Paylaşılacak özetleri inceleyip temizleyin.

## Her flash sonrası kısa kontrol

- [ ] Beklenen aday ve hash doğrulandı.
- [ ] sys.boot_completed=1, SystemUI ve launcher çalışıyor.
- [ ] Ekran, dokunmatik, kilitleme/uyanma.
- [ ] SIM durumu, telefon süreci, şebeke.
- [ ] Parmak izi (önce cihaz PIN'iyle açılış gerektiğini dikkate al).
- [ ] Yeni crash/ANR/servis yeniden başlama kaydı yok.
- [ ] Önceki çalışan özelliklerde gerileme yok.

## Telefon

Beş yeniden başlatmada açılıştan PIN ekranına ve PIN girişinden şebekeye süreyi ayrı ölç.
Arama başlat/al; ahize, mikrofon, hoparlör, ekranın kulağa yaklaşınca kapanması ve geri açılması.
SMS gönder/al, Wi-Fi kapalı mobil veriyi doğrula. IMS/VoLTE ayrıca test edilir; operatör adı tek başına bunları kanıtlamaz.

## Kamera ve donanım

Ön/arka fotoğraf, video ve video sesi; flaş; art arda aç/kapat.
20 parmak izi denemesinde ekran açık/kapalı ayrımı ve gecikmeyi kaydet.
GPS'i açık alanda gerçek fix ile doğrula. Bluetooth medya/arama, sensörler, hotspot, USB ve şarjı ayrı kaydet.

## Performans

Aynı pil/ısı/şarj koşulunu kullan. Açılış işleri bittikten sonra aynı uygulamalarla aynı 5–6 geçişi yap; önce gfxinfo sayaçlarını sıfırla. En az üç koşu kaydet.
Launcher/SystemUI kare sayısı, p50/p90/p95/p99, jank ve GPU sürelerini birlikte tut. gfxinfo tüm SurfaceFlinger geçişlerini kapsamaz.
Geçiş sırasında CPU/GPU frekansları ve sistem kayıtlarını mümkünse eşzamanlı al. Boşta top veya tarihsel cpuinfo tek başına geçiş nedeni göstermez.
Öznitelik: gecikme, takılma, bozuk efekt. Animasyon süresini azaltmak render düzeltmesi sayılmaz.

## Dayanıklılık / sürüm adayı

48 saat: yeniden başlama/çökme/ANR, bildirim gecikmesi, bağlantı kaybı, ısı ve şarj.
Gece testi: süre, başlangıç/bitiş pil yüzdesi, ağ ve ekran koşullarını yaz; tek geceden genel sonuç çıkarma.
Temiz kurulumu yalnızca gerekli düzeltmeler imaja alındıktan ve yedek/geri dönüş hazır olduğunda planla.

## Sonuç şablonu

| Test | Beklenen | Gözlenen | Durum | Kanıt |
| --- | --- | --- | --- | --- |
| Örnek: gelen arama | Çalar, ses iki yönde çalışır | Henüz denenmedi | Belirsiz | — |

Başarısız/belirsiz sonuçlarla günlük kullanıma hazır etiketi verilmez.
