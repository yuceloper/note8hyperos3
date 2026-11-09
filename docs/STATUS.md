# Mevcut durum

Son kayıt: 2026-11-09. Kanıtlar cihaz çıktıları ve kullanıcı testleridir; tam donanım veya uzun süreli kararlılık sertifikası değildir. Önceki V12 durum metni tarihsel kalmıştı; aşağıdaki bilgiler güncel V35 karşılaştırma noktasını anlatır.

## Güncel karşılaştırma noktası

- Cihaz: Redmi Note 8, ginkgo. Donor: creek Turkey HyperOS 3, Android 16.
- System: hyperos3-ginkgo-v35-padded.img, 8589934592 bayt.
- System imajı SHA256: 2a6ef7d44e92d7e337cadadda56d30574e218e980d2b3d1346bc2564e5a648f5.
- Vendor: V26, SHA256 55da7275e3856b3758189f2e9e41203b2592b1e78cb9a0d346dc9db1fdd44b43. Boot değiştirilmedi.
- Kamera: özgün HyperOS Camera 6.2 kodu, com.android.camera kimliği. Model kontrolü ve Pro ET önizleme kaynak hatası için yerel düzeltmeler var; V35 başlangıç Test.txt yazma tanısını atlıyor. Bu, gerçek LUT erişiminin düzeltildiği anlamına gelmez.
- Gömülü kamera APK SHA256: a316586185bfa320d9c888667bf044d7ab835004b759a5f1b009c931d52bbeaa. Kullanıcı userdata güncellemesini kaldırdı; pm path /product/priv-app/MiuiCamera/MiuiCamera.apk doğrulandı.
- SELinux politikası: d38305ac8bff790d9f18ec8541e412ce05344a43827c6fda73ff7d12146e952a. Neverallow kontrolleri korundu. Genel permissive çözüm uygulanmadı.

## Doğrulanan kullanım ve sınırlar

| Alan | Kullanıcı testi / kanıt |
| --- | --- |
| Açılış, ekran, dokunmatik | V35 açılıyor; ilk dakika takılmaları sürüyor |
| Telefon/SIM | SIM yükleniyor ve arama yapıldı; birkaç dakikalık görüşmede ses/mikrofon normal bildirildi. PIN/şebeke gecikmesi tekrarlanabiliyor |
| Bluetooth | ConfigStore sonrası açılma ve tarama doğrulandı; kapsamlı medya/arama dayanıklılığı tamamlanmadı |
| Parmak izi | Kayıt ve kilit açma çalıştığı bildirildi; açılış yükünde gecikme var |
| Kamera/Pro | Kullanıcı normal çekim ve Pro kullanımında çalışma bildirdi; tüm mod/lens kombinasyonları denenmedi |
| Kamera–Galeri | Fotoğraf açma/yakınlaştırma, video sesli oynatma, kameraya dönüş ve kilit ekranından eski fotoğraflara erişim koruması testleri kullanıcı tarafından başarılı bildirildi |
| FindDevice/MTD | V22 sonrası kullanıcı çalıştığını bildirdi; tüm bulut/kayıp cihaz akışları doğrulanmadı |

## Açık sorunlar

1. İlk dakika CPU/bellek/servis yükü ve arayüz takılması. Tek bir boşta top çıktısı kök neden kanıtı değildir.
2. PIN girişinden sonra şebekenin geç görünmesi. SIM LOADED, operatör adı, gerçek IN_SERVICE ve geçerli sinyal ayrı ölçülmelidir.
3. Yeniden başlatma hemen sonrası ilk kamera açılışında kilit ekranı başlatma uyarısı veya ana ekrandan bağlantı hatası/3 saniyelik kapanma gözlendi. İki dakika bekleme sonrası ilk kilit ekranı açılışı ve force-stop sonrası soğuk açılış geçti. Ana ekran geri sayım hatasının kesin tetikleyicisi henüz doğrulanmadı.
4. GalleryBackgroundService bağlantısı com.miui.gallery.permission.BIND_SERVICE imza iznine takılıyor. Normal görüntüleme testleri geçse de paylaşımlı büyük önizleme/ön yükleme optimizasyonu geri yüklenmedi. Galeri imzası/izin koruması değiştirilmedi.
5. Özel/import LUT desteği doğrulanmadı; V35 gerçek LUT yollarını değiştirmiyor.
6. Temiz Google kurulumu, uzun süreli bağlantı/pil/derin uyku/GPS testleri ve 48 saat dayanıklılık tamamlanmadı.
7. Wallpaper Carousel önceki çökmesi kullanıcı tarafından kapatılarak hafifletildi; kök nedenin giderildiği iddia edilmez.

## Sıradaki iş

V37 salt okunur açılış zaman çizelgesi: açık --reboot seçeneğiyle bir yeniden başlatma, ardından üç dakika SIM/property, kayıt durumu, CPU sayaçları, bellek/PSI, top ve logcat toplama. Yeni ROM değişikliği önce ölçümle gerekçelendirilecek. V37 bir ROM imajı değildir.

HyperOS 4 için creek ilk donor hedefidir; uygun gerçek paket doğrulanana kadar V35 geliştirmesi sürer. Güncelleme takvimi ile indirilebilir/uygun donor paketi aynı şey değildir.
