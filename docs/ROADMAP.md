# Yol haritası

Öncelik sırası aşağıdadır. Kusursuzluk veya bitiş tarihi taahhüdü yok; her aşama kanıtla kapanır.

## 1 — Tekrarlanabilir temel

- [x] V12 imaj hash'i ve gözlenen sorunları kaydet.
- [ ] Mac'teki mevcut git durumu ve yerel araç/betik envanterini al.
- [ ] Hazırlama betiklerini, araç sürümlerini ve hash kontrollü yamaları repoya aktar.
- [ ] Gerekli uyumluluk değişiklikleri ile deneysel ayarları ayır.
- [ ] Geri dönüş prosedürünü mevcut yedekler ve imajlarla doğrula.

Çıkış: kaynak/araç girdileriyle tekrarlanabilir derleme; geri dönüş dosyaları tanımlı. Şu an bu şart sağlanmış değil.

## 2 — Açılış ve telefon

- [ ] SIGABRT kaynağı ve crash dump başarısızlığını incele.
- [ ] Beş açılışta açılış/PIN istemi/PIN sonrası kayıt sürelerini ölç.
- [ ] Gelen/giden arama, ahize/hoparlör/mikrofon/yakınlık sensörü testi.
- [ ] Gelen/giden SMS ve Wi-Fi kapalı mobil veri testi.

Çıkış: tüm temel testler geçer; gecikmeler tutarlı ve açıklanmış, kullanımı engelleyen yeniden başlama yok.

## 3 — Kamera

- [ ] Uyumlu alternatif uygulamayla ön/arka fotoğraf ve video dene.
- [ ] Flaş, kayıt sesi, uygulama yeniden açılması ve ekran kilidi sonrası kullanım.
- [ ] Donor Xiaomi Kamera model kontrolü ve gerçek HAL uyumluluğunu ayrı incele.

Çıkış: çalışan temel kamera. Xiaomi Kamera zorunlu değil; eksik modlar açıkça belgelenir.

## 4 — Akıcılık

- [ ] Mevcut Perf HAL hipotezi: dışa aktarılan arayüzleri koruyan dar test adayını çevrimdışı incele.
- [ ] Aynı senaryoda CPU/GPU frekansları, kare süreleri ve beklemeleri kaydet.
- [ ] V12 ile aday arasında tekrarlı karşılaştırma.
- [ ] Faydasız/belirsiz deneyleri kalıcı düzeltme sayma.

Çıkış: aynı koşullarda tekrarlanan iyileşme; yeni çökme, ısı veya tüketim sorunu yok. Perf loglarının kaybolması tek başına yeterli değil.

## 5 — Donanım kapsamı

- [ ] Parmak izi, GPS, Bluetooth ses, sensörler.
- [ ] Hotspot, USB dosya aktarımı, şarj, ekran uyku/uyanma.
- [ ] Şifreleme/kilit ve yeniden başlatma davranışı.

Çıkış: temel test matrisinde bilinmeyen özellik kalmaz; desteklenmeyenler açıkça belirtilir.

## 6 — Sürüm adayı

- [ ] Google paketlerinin elle etkinleştirilmesi gereksinimini kalıcı çöz.
- [ ] Gerekli düzeltmeleri imaja al; sonra planlı temiz kurulum.
- [ ] 48 saat kullanım ve ekran kapalı gece pil testi.
- [ ] Bilinen hatalarla birlikte sürüm notu ve test kaydı.

Çıkış: müdahalesiz kurulum, temel işlevlerde başarısızlık ve beklenmedik yeniden başlama yok. Şimdi yeniden veri silmek gerekmiyor.

## Değişiklik politikası

Tek konu dalı → incelenebilir PR → cihaz testi → sonuç kaydı → birleştirme.
Mevcut V12 bir karşılaştırma noktasıdır; kararlı sürüm etiketi değildir.
ROM imajı checksum'ı, Git commit'i ve cihazda test edilen dosya ilişkisi her adayda ayrı kaydedilir.
