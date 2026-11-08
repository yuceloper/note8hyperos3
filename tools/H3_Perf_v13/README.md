# V13 — eksik Qualcomm Perf HAL bağlantı deneyi

Durum: çevrimdışı kontroller geçti; Android cihazında denenmedi. Akıcılık düzeltmesi olarak kabul edilmedi.

## Hipotez

Ginkgo V12, Lineage libperfmgr güç HAL'ini çalıştırıyor. HyperOS'un libqti-perfd-client_system.so kütüphanesi ise cihazda bulunmayan Qualcomm perf2 AIDL ve perf HIDL 2.2/2.3 servislerini arıyor. Tekrarlanan aramaları kaldırmanın geçiş gecikmesine etkisini ölçmek istiyoruz. Log azalması tek başına başarı değildir.

Bu aday Qualcomm boost desteği sağlamaz, Lineage güç HAL'ine istek çevirmez. Bu kütüphaneden Qualcomm perf bağlantısı kullanan işlemler mevcut başarısızlık yollarına döner. İleride gerçek Qualcomm perf servisi eklenirse bu değişiklik geri alınmalıdır.

## Değişiklik

Kaynak SHA256: `0b2ffd2e0ae31e3907b07f9060eb3284b611f27a44d7aa5bcdf72ac0de0192b3`

Aday SHA256: `c03f761417871e9b14102cf49669bff8bd60c12715b26b8b9a617cb8e3d6675a`

94800 baytlık ARM64 ELF dosyasında dört girişin ilk 12 baytı `bti c; mov w0, wzr; ret` olur. 48 baytlık alan değiştirilir; 39 baytın değeri farklıdır. Fonksiyonlar bool false döner; başarı/handle uydurulmaz. Yaprak dönüş stack'i ve callee-saved register'ları değiştirmez. Prologdan önce döndüğü için PAC imzalama/çözme yolu yürütülmez; BTI giriş işareti tutulur.

| Dosya ofseti = sanal adres | İç fonksiyon |
| --- | --- |
| 0x8f7c | isHalTypeAidl.cfi |
| 0x9168 | getPerfAidlAndLinkToDeath |
| 0x9e04 | getPerfServiceAndLinkToDeath |
| 0xee94 | getPerfServiceAndLinkToDeathV2_3 |

Adresler kaynak ELF .gnu_debugdata sembollerinden doğrulandı. Çağıran kodlar W0 bool sonucunu kontrol ediyor; AIDL callback kaydı tür seçiminden bağımsız bağlantı çağırdığı için AIDL bağlantı yardımcısı da kapsama alındı. Dynsym, sürüm bilgisi, bağımlılıklar, CFI jump tabloları ve .text dışındaki bütün bölümler aynı kalır. Kaynak hash'i değişirse bu ofsetler kullanılmaz.

## Betikler

- prepare.py: yalnızca yerel girdiden ayrı çıktı üretir. Varlığı olmayan output dizini ister.
- install.py: yalnızca çevrimdışı Linux V12 çalışma ağacını değiştirir. Kütüphane, V12 build.prop, V8 SurfaceFlinger ve V11 politika hash'lerini doğrular. Yedek oluşturur; uid/gid, mode, xattr ve zamanları korur. Normal Python hatasında geri yüklemeyi dener; elektrik kesintisi/işlemin öldürülmesi için atomik işlem garantisi yoktur.
- install.py --restore: beklenen V13 dosyasını doğrulanmış V12 yedeğine döndürür; yarım kalan geri almadan sonra dosya zaten V12 ise metadata doğrulamasını tamamlar. Başka hash'teki dosyanın üzerine yazmaz.
- verify.py: doğru yerel binary ile yapısal kontrolleri ve geçici ağaçta install/restore testlerini çalıştırır. Security SELinux xattr'ı veya Android linker/CFI çalışmasını test etmez.

## Yerel çıktı ve kontroller

```bash
python3 tools/H3_Perf_v13/prepare.py --source /path/to/original/libqti-perfd-client_system.so --out out/perf-v13-candidate
python3 tools/H3_Perf_v13/verify.py --source /path/to/original/libqti-perfd-client_system.so
```

Binary dosyaları repoya eklenmez. prepare.py standart Python kütüphanesiyle hash kontrollü yeniden üretir. Girdi olarak vendor/lib64/libqti-perfd-client.so kullanmayın; isimleri ve arayüzleri farklıdır.

### Kurulum revizyonu 2

İlk cihaz sahibi denemesinde Docker mevcut xattr'ı yeniden set etmeye EPERM verdi; geri alma da aynı noktada durdu. Revizyon 2 yalnızca gerçekten değişmiş uid/gid/mode/xattr değerlerini yazar, tüm değerleri yine doğrular. Her setxattr çağrısının reddedildiği senaryoda install/restore testi geçti. Bu gerçek security.selinux veya cihaz açılış testinin yerine geçmez. İçerik yazımıyla bozulabilen capability/IMA/EVM etiketleri varsa yazmadan durur.

İlk denemeden kalan ağaç için önce eski yedekle --restore çalıştırın. Başarıdan sonra eski yedeği silmeden yeni bir yedek dizini (örneğin hyperos3-perf-v13-r2) ile uygulayın. Binary yama ve aday SHA256 değişmedi.

## V12 çalışma ağacına uygulama

Mac repo kökünden, bu kaynaklar çalışma kopyasında mevcutsa:

```bash
docker run --rm -i \
  -v note8-hyperos3-work:/linux \
  -v "$PWD/tools/H3_Perf_v13:/package:ro" \
  ginkgo-port-tools:erofs python3 /package/install.py \
  --root /linux/build/hyperos3-ginkgo-v1 \
  --backup /linux/backups/hyperos3-perf-v13
```

Hash uyuşmazlığında durun; kontrolü kaldırmayın. Başarı, yalnızca çalışma ağacının hazırlanmasıdır. İmaj paketleme ve cihaz testi ayrı aşamalardır; bu betikler adb/fastboot kullanmaz.

Geri alma aynı komuta `--restore` eklenerek yapılır. Bu yalnızca çalışma ağacını geri alır; telefonda kurulu imajı değiştirmez.

## Cihaz kabul ölçütleri

1. Önceden çalışan açılış, dokunmatik, SIM, arama ve parmak izi testlerinde gerileme yok.
2. İlgili kütüphane hash'i doğrulanır. Aynı istemciden servis aramaları kaybolmalı; başka istemcilerden kalan loglar ayrıca incelenir.
3. Aynı ısı/pil/şarj ve uygulama koşullarında en az üç V12/V13 geçiş koşusu; Launcher/SystemUI p95/p99 ve kullanıcı gözlemi birlikte değerlendirilir.
4. Yeni native/Java crash, ANR, bağlantı sorunu veya pil/ısı gerilemesi olmamalı.
5. Fayda belirsiz ya da sonuç kötü ise çalışma ağacı geri alınır; deney kalıcı çözüm sayılmaz.

Kamera, SIM gecikmesi ve açılış SIGABRT sorunu bu adayla çözüldü sayılmaz.
