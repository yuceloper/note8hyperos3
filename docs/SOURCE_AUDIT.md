# Hazırlama betikleri: ilk kaynak denetimi

Tarih: 2026-11-08. Bu kayıt, kullanıcı tarafından gönderilen 29 metin dosyasının incelenmesini kapsar. ROM derlemesi, politika derlemesi veya cihaz testi bu denetimde çalıştırılmadı.

## Doğrulananlar

- 8 Python dosyası AST ve bytecode derleme kontrolünden, 10 JSON dosyası ayrıştırma kontrolünden geçti. Betiklerin üst seviye kodu yürütülmedi.
- İçe alınan 29 dosyanın baytları değiştirilmedi; SHA256 ve boyutları [manifestte](source-import-manifest.json).
- İncelenen betiklerde adb/fastboot üzerinden flash komutu yok. Hazırlama betikleri Linux çalışma ağacını değiştirebilir; mevcut V12 ağacında topluca tekrar çalıştırılmamalı.
- Politika betiği secilc çağrısında neverallow devre dışı bırakma seçeneği kullanmıyor. Bu inceleme geçmiş derleme raporunu yeniden doğrulamaz.

## Kapsam ve eksik girdiler

| Paket | Repodaki içerik | Eksik / dışarıdan gereken |
| --- | --- | --- |
| H3_Lineage23_Policy_v2 | Politika dönüşüm/derleme betiği, rapor | Donor CIL/mapping dosyaları, Lineage vendor/public/ODM CIL, secilc |
| H3_Base_Prep_v1 | Çalışma ağacı hazırlama betiği, hash raporu | init.rc.candidate, derlenmiş politika/context girdileri, başlangıç ağacı |
| H3_Boot_Prep_v1 | Boot dönüştürme ve fstab yerleştirme betikleri, diff | Kaynak boot.img ve fstab.qcom; üretilen fstab.emmc ve boot adayı |
| H3_Crypto_Prep_v2 | Boot/fstab dönüştürme ve yerleştirme betikleri, diff | Boot v1 girdileri; üretilen fstab.emmc ve boot v2 |
| H3_BootDevices_v3 | Cmdline ve geçmiş hash raporu | Dönüşüm betiği ve boot adayı; yalnızca rapordan yeniden üretilemiyor |
| H3_BPF_v6 | Yerleştirme betiği, girdi/asset hash listeleri, raporlar | assets/ içindeki netbpfload, özel kütüphaneler ve BPF nesneleri; dönüştürme tarifi |
| H3_Netd_v7 | Yerleştirme betiği, old-action, asset hash listesi | expected-init.sha256, assets/ içeriği ve dönüştürme tarifi |

Betikler /linux, /prep, /package, /policy ve /out gibi belirli container bağlama yollarına bağlı. Genel bir komut satırı build arayüzü henüz yok. Boot referans betikleri bazı girdileri analysis/ ve out/ altında arıyor.

V8 grafik, V9 bölge, V10 uygulama, V11 parmak izi politikası, V12 perf property değişikliklerinin hazırlama betikleri bu pakette yok. ADB anahtarı, init tanı değişikliği ve ODM bağlantı etiketi düzeltmesinin yeniden üretim adımları da tamamlanmalı. Özel anahtarlar repoya alınmamalı.

## Takip gerektiren bulgular

1. Python assert kontrolleri -O ile devre dışı kalabilir. Geçmiş betikler python3 -O ile çalıştırılmamalı; gelecekte ortak ön kontrol katmanında açık hata kontrollerine geçilmeli.
2. Betikler aşamaya özgü kaynak hash'leri/yedek dizinleri bekliyor; idempotent bir build zinciri değiller. Kısmi hata sonrası otomatik devam/geri alma garantisi yok.
3. Politika dönüşümü coredump_file ve debug tracing allow kuralları da kaldırıyor. Cihazdaki crash dump sorununun nedeni olduğu kanıtlanmış değil; tanı sırasında etkisi incelenmeli.
4. Bir vendor_init kamera property set allow kuralı kaldırılıyor. Kamera başlatmasına etkisi henüz doğrulanmadı; model uyumsuzluğu uyarısıyla aynı neden olduğu varsayılmamalı.
5. validation.json ve README içindeki NOT_BOOT_TESTED ifadeleri paketlerin hazırlandığı tarihsel durumu anlatır; güncel cihaz durumunun kaydı docs/STATUS.md'dir. Bu raporlar yeni test yapılmış gibi güncellenmedi.

## Sonraki kaynak işi

Mac'teki eksik metin girdilerini ve V8–V12 adımlarını kurtar. Binary girdiler için hash kontrollü yerel edinme/çıkarma tarifleri ekle. Araç sürümlerini kaydet ve temiz, ayrı bir çalışma ağacında zinciri doğrula. Bu yapılana kadar repodan V12 yeniden üretilebilir sayılmaz.
