# 🎓 Master Installation Guide (Zero to Hero)

Bu proje için tek, sıralı ve eksiksiz kurulum rehberi. Birden fazla döküman arasında kaybolmanıza gerek yok; adımları sırayla takip edin.

---

## 🗺️ Yol Haritası (Roadmap)
1.  **Phase 1: Altyapı (Infrastructure)** -> Kubernetes Cluster Kurulumu.
2.  **Phase 2: Platform (The Stack)** -> Elastic Stack & Logstash Kurulumu.
3.  **Phase 3: Görünürlük (Visibility)** -> Windows Logları, GPO ve Firewall Ayarları.
4.  **Phase 4: Zeka (Intelligence)** -> Python MCP Sunucusu ve LLM Bağlantısı.

---

## ✅ Phase 1: Altyapı (Infrastructure)

Eğer halihazırda bir Kubernetes Cluster'ınız varsa bu adımı atlayın.
Yoksa ve "1 Master, 2 Worker" yapısında bir cluster kuracaksanız:

1.  **3 adet Ubuntu Sunucu** hazırlayın.
2.  Detaylı kurulum komutları için (Kubeadm, Containerd, Calico) şuraya gidin:
    👉 **[KUBERNETES_SETUP.md](KUBERNETES_SETUP.md)**
3.  `kubectl get nodes` komutunda 3 node'u da "Ready" görene kadar devam etmeyin.

---

## ✅ Phase 2: Platform (Elastic Stack)

Cluster hazır. Şimdi üzerine Elastic Stack (Elasticsearch, Kibana, Fleet, Logstash) kuracağız.

1.  **ECK Operatörünü Kurun:**
    ```bash
    kubectl create -f https://download.elastic.co/downloads/eck/2.11.0/all-in-one.yaml
    ```
2.  **Bileşenleri Sırayla Uygulayın:**
    ```bash
    kubectl apply -f kubernetes/elasticsearch.yaml
    # (Bekleyin: kubectl get elasticsearch -> Green olmalı)
    
    kubectl apply -f kubernetes/kibana.yaml
    kubectl apply -f kubernetes/fleet-server.yaml
    kubectl apply -f kubernetes/logstash.yaml
    ```
3.  **Şifreleri Alın:**
    ```bash
    # Elastic User Password
    kubectl get secret quickstart-es-elastic-user -o jsonpath='{.data.elastic}' | python -m base64 -d
    ```
4.  **Erişim:**
    *   Kibana: `https://<NODE-IP>:5601`
    *   Logstash (Syslog): `UDP 30514`

---

## ✅ Phase 3: Görünürlük (Log Sources)

Veri akışını başlatalım.

### A. Windows Policy (GPO) - Domain Controller
Active Directory ve PowerShell loglarını açmak için Group Policy ayarlarını yapın.
👉 **[GPO_CONFIGURATION.md](GPO_CONFIGURATION.md)** (Bu adımları tamamlayıp dönün).

### B. Endpoint Telemetry (Sysmon) - Tüm Sunucular
Daha detaylı (Process, Network, DNS) logları için Sysmon kurun.
1.  Bu repodaki `scripts/` klasörünü sunucuya kopyalayın.
2.  Admin PowerShell'de çalıştırın:
    ```powershell
    .\scripts\install_sysmon.ps1
    ```

### C. Firewall Logs (Syslog)
Fortigate/PaloAlto/CheckPoint cihazınızdan Syslog yönlendirmesi yapın:
*   **Hedef IP:** Kubernetes Worker Node IP'niz.
*   **Hedef Port:** 30514 (UDP).

---

## ✅ Phase 4: Zeka (AI & MCP Server)

Son olarak, LLM'in sistemi yönetmesini sağlayacak "Beyin" katmanını kuruyoruz.

1.  **Python Hazırlığı (Windows Makinenizde):**
    ```powershell
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    ```

2.  **Yapılandırma:**
    Project root dizininde `.env` dosyası oluşturun (`.env.example`'dan kopyalayın) ve Phase 2'de aldığınız Elastic şifresini girin:
    ```ini
    ELASTIC_URL=https://<KIBANA-IP>:9200
    ELASTIC_USER=elastic
    ELASTIC_PASSWORD=<SIFRE>
    VERIFY_CERTS=false
    ```

3.  **Sunucuyu Başlatın:**
    ```powershell
    python src/server.py
    ```
    *Kalıcı servis olarak kurmak isterseniz: [DEPLOYMENT.md](DEPLOYMENT.md#option-b-permanent-service-recommended)*

4.  **LLM Bağlantısı (Claude Desktop Örneği):**
    Config dosyasına şunu ekleyin:
    ```json
    "mcpServers": {
      "elastic-soc": {
        "command": "C:\\Path\\To\\venv\\Scripts\\python.exe",
        "args": ["C:\\Path\\To\\src\\server.py"]
      }
    }
    ```

🎉 **Tebrikler!** Tam teşekküllü, AI destekli SOC sisteminiz hazır.
LLM'e sorabilirsiniz: *"Son 1 saatteki en kritik 5 alarmı göster ve ilgili IP için loglarda arama yap."*
