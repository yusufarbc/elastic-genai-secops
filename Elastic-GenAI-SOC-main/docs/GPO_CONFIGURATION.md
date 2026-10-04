Harika, bu adım projenizin **"Görünürlük"** katmanını tamamlayacak. Windows varsayılan olarak "sessizdir", saldırganlar da bu sessizliği sever. Biz bu politikalarla sistemi "konuşkan" hale getireceğiz.

İşte **Elastic-GenAI-SOC** projeniz için sunucularınıza (özellikle Domain Controller ve Kritik Sunuculara) uygulamanız gereken **"Advanced Audit Policy" (Gelişmiş Denetim Politikası)** yapılandırma dökümanı.

---

# 🛡️ Windows Advanced Audit & PowerShell Logging Yapılandırma Rehberi

Bu döküman, **Group Policy Management (GPO)** kullanılarak organizasyondaki sunucuların güvenlik loglarını açmayı ve **Elastic Agent**'ın (ve LLM'in) anlamlı veriler toplamasını sağlamayı hedefler.

### 🎯 Hedef

* **Active Directory:** Kimlik hırsızlığı ve yetki yükseltme girişimlerini yakalamak.
* **PowerShell:** Fileless (dosyasız) saldırıları ve zararlı scriptleri **LLM (GenAI)** için okunabilir hale getirmek.
* **Sistem:** Log silme veya servis durdurma eylemlerini tespit etmek.

---

## BÖLÜM 1: GPO Oluşturma

1. **Domain Controller** üzerinde `gpmc.msc` (Group Policy Management) aracını çalıştırın.
2. **Group Policy Objects** klasörüne sağ tıklayın -> **New** -> İsim: `SOC-Server-Audit-Policy`.
3. Bu yeni politikayı, sunucularınızın bulunduğu OU'ya (Organizational Unit) sürükleyip bırakın (Linkleyin).
* *Not: Domain Controller'lar için "Default Domain Controllers Policy"i düzenlemek yerine yeni bir GPO oluşturup DC OU'sunun en üstüne koymak "Best Practice"tir.*



---

## BÖLÜM 2: Kritik Denetim Politikaları (Audit Policies)

Oluşturduğunuz GPO'ya sağ tıklayıp **Edit** deyin ve şu yola gidin:
📂 **Computer Configuration > Policies > Windows Settings > Security Settings > Advanced Audit Policy Configuration > System Audit Policies**

Aşağıdaki ayarları **Success (Başarılı)** ve **Failure (Başarısız)** olarak işaretleyin:

### 1. Account Logon (Sadece Domain Controller için Kritik)

* **Kerberos Authentication Service:** ✅ Success & Failure
* *Neden:* Kerberos saldırılarını (Golden Ticket vb.) yakalamak için.


* **Credential Validation:** ✅ Success & Failure
* *Neden:* Yanlış şifre denemelerini görmek için.



### 2. Logon/Logoff (Tüm Sunucular)

* **Logon:** ✅ Success & Failure
* *Neden:* Sunucuya kim RDP yaptı veya console'dan girdi?


* **Special Logon:** ✅ Success
* *Neden:* Yönetici yetkisiyle (Administrator) oturum açıldığında loglar (Event ID 4672).



### 3. Account Management (Kullanıcı Yönetimi)

* **User Account Management:** ✅ Success & Failure
* *Neden:* Yeni kullanıcı oluşturuldu mu? Şifre değişti mi?


* **Security Group Management:** ✅ Success & Failure
* *Neden:* Biri kendini "Domain Admins" grubuna eklerse alarm çalsın.



### 4. Detailed Tracking (Detaylı Takip)

* **Process Creation:** ✅ Success
* *Neden:* Sysmon kullanıyoruz ama bu da yedek (backup) olarak kalmalıdır. (Event ID 4688).



### 5. Policy Change (Politika Değişikliği)

* **Audit Policy Change:** ✅ Success & Failure
* *Neden:* Saldırgan izlerini örtmek için bu logları kapatmaya çalışırsa yakalamak için.



### 6. System (Sistem)

* **Security State Change:** ✅ Success & Failure
* *Neden:* Sistem saati değiştirilirse veya sistem kapanırsa.



---

## BÖLÜM 3: PowerShell Logging (LLM & GenAI İçin Çok Kritik 🚨)

Bu bölüm, projenizdeki Yapay Zekanın (LLM) şifreli saldırıları çözebilmesi için hayati önem taşır.

GPO Editöründe şu yola gidin:
📂 **Computer Configuration > Policies > Administrative Templates > Windows Components > Windows PowerShell**

Aşağıdaki ayarları **Enabled (Etkin)** yapın:

### 1. Turn on PowerShell Script Block Logging (Komut Dosyası Bloğu Günlüğü)

* **Durum:** Enabled
* **Açıklama:** PowerShell komutları, çalıştırılmadan hemen önce (şifresi çözülmüş/deobfuscated halde) loglanır.
* **Elastic Event ID:** 4104
* *Bu log sayesinde LLM'iniz şunu diyebilir: "Bu base64 kodunun içinde 'Invoke-Mimikatz' gizli!"*

### 2. Turn on Module Logging (Modül Günlüğü)

* **Durum:** Enabled
* **Options:** "Module Names" kısmına `*` (yıldız) koyun.
* **Açıklama:** PowerShell modüllerinin (Network, Disk vb.) aktivitelerini kaydeder.

---

## BÖLÜM 4: Komut Satırı Parametrelerini Açma

Sysmon kullanıyoruz ama Windows'un kendi loglarında da komut satırını görmek iyidir.

Yol:
📂 **Computer Configuration > Policies > Windows Settings > Security Settings > Local Policies > Security Options**

* Ayar: **Audit: Include command line in process creation events**
* Durum: **Enabled**

---

## BÖLÜM 5: Uygulama ve Test

GPO ayarlarını tamamladıktan sonra sunucularda aktif olması için:

1. **Politikayı Dağıtma:**
Sunucu üzerinde CMD (Admin) açın:
```cmd
gpupdate /force

```


2. **Kontrol Etme:**
Ayarların gelip gelmediğini görmek için:
```cmd
auditpol /get /category:*

```


*(Çıktıda "Success and Failure" ibarelerini görmelisiniz.)*
3. **Log Kontrolü (Elastic Agent Öncesi):**
Event Viewer > Windows Logs > Security altında;
* Bir PowerShell açıp `Write-Host "Test Logu"` yazın.
* Security loglarında veya `Applications and Services Logs > Microsoft > Windows > PowerShell > Operational` altında 4104 ID'li logu arayın.



---

### 🚀 Elastic Tarafında Ne Yapılacak?

Bu ayarları yaptığınızda, Elastic Agent'ınızdaki **"Custom Windows Event Logs"** entegrasyonuna ekstra bir kanal eklemenize **gerek yoktur.**

* Audit Policy logları -> Otomatik olarak **System** ve **Security** kanallarına düşer.
* PowerShell logları -> Otomatik olarak `Microsoft-Windows-PowerShell/Operational` kanalına düşer (Eğer Fleet politikanızda "Windows" entegrasyonu ekliyse bu varsayılan olarak gelir).

**Sonraki Adım:**

---

## BÖLÜM 6: DNS Server Logging (Domain Controller)

Saldırganların Command & Control (C2) sunucuları ile haberleşmesini yakalamak için DNS logları kritiktir. Sysmon (Event ID 22) istemci tarafını çözer, ancak DNS Sunucusu tarafında da loglama açılmalıdır.

### Yöntem: DNS Debug Logging

1.  **DNS Manager**'ı açın (`dnsmgmt.msc`).
2.  Sunucunuza sağ tıklayın -> **Properties**.
3.  **Debug Logging** sekmesine gelin.
4.  **"Log packets for debugging"** kutucuğunu işaretleyin.
5.  Şu ayarları seçin:
    *   **Packet direction:** Outgoing, Incoming
    *   **Transport protocol:** UDP, TCP
    *   **Packet contents:** Queries/Transfers
    *   **Packet type:** Request
    *   **File path:** `C:\Windows\System32\dns\dns.log` (veya uygun bir disk yolu).
    *   **Limit size:** 500 MB (Disk dolmasını önlemek için).

### Elastic Entegrasyonu
Bu logu okumak için Elastic Agent politikanıza **"Custom Logs"** entegrasyonu ekleyin:
*   **File path:** `C:\Windows\System32\dns\dns.log`
*   **Dataset:** `dns.debug`

---

## 🎯 Özet: Hangi Log Nereden Geliyor?

| Log Türü | Kaynak | Araç / Yöntem |
| :--- | :--- | :--- |
| **Giriş Başarı/Hata** | Active Directory | Windows Audit Policy (GPO) |
| **Zararlı Scriptler** | Tüm Sunucular | PowerShell Script Block Logging (GPO) |
| **Process/Network** | Tüm Sunucular | Sysmon (Helper Script) |
| **C2 Trafiği** | DNS Sunucusu | DNS Debug Log |
