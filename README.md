# Tugas 1 — Social Media Analytics: Isu MSCI Standalone Indonesia Market di Bluesky

Repositori ini berisi data mentah, *collection log*, sampel validasi presisi, skrip Python, data hasil olahan (EDA, *preprocessing*, sentimen IndoBERT), dasbor interaktif, serta laporan akhir untuk **Tugas 1: Satu Medsos, Banyak Temuan** (Mata Kuliah *Social Media Analytics*).

- **Platform:** Bluesky Social (`app.bsky.feed.searchPosts` via AT Protocol)
- **Periode Pengamatan:** 24 Agustus 2026 s/d 25 November 2026 WIB (`2026-08-23T17:00:00Z` – `2026-11-24T17:00:00Z`)
- **Laporan PDF:** [`Laporan_Analisis_MSCI_Standalone_Bluesky.pdf`](Laporan_Analisis_MSCI_Standalone_Bluesky.pdf)
- **Laporan DOCX:** [`Laporan_Analisis_MSCI_Standalone_Bluesky.docx`](Laporan_Analisis_MSCI_Standalone_Bluesky.docx)

---

## Ringkasan 3 Temuan Utama

1. Pengumpulan data dari 6 kata kunci bertingkat menghasilkan **1.286** baris mentah dan **873** post unik (duplikasi lintas kata **32,12%** / 413 post) dengan presisi tiap kata kunci **90,0%–100,0%** pada uji Wilson 95%.
2. Aktivitas diskusi tersebar di **41** hari aktif dengan rata-rata **21,29** post/hari (median **10**), memuncak pada **16 Oktober 2026** (**156** post/hari), dan terkonsentrasi **50,2%** pada 10 akun teratas (`CR1` **13,1%** / **114** post).
3. Klasifikasi sentimen IndoBERT mencatat **83,5%** (**729** post) Netral, **8,6%** (**75** post) Positif, dan **7,9%** (**69** post) Negatif dengan puncak sentimen negatif pada **19 Oktober 2026** (**16** post).

---

## Pemisahan Data Mentah vs Data Hasil Olahan

### 1. Data Mentah (*Raw Crawl*) & Log Integritas (*Collection Log*)
Berkas mentah hasil penarikan langsung dari API Bluesky beserta sampel validasi (`seed=42`) dan log audit SHA-256:

| Kata Kunci | Mentah | Berkas Data Mentah | SHA-256 CSV | SHA-256 JSONL | Berkas Log & Sampel |
|---|---:|---|---|---|---|
| `msci standalone indonesia market` | 151 | `pilot_msci_standalone_indonesia_market.csv` / `.jsonl` | `ec1d684d291fcc77b0115e0880078b19abd100dfa08676fbfb51171cad7212de` | `83d2b2c5dcecb55d8640e8195122dd128a1bf63605d6f70d34768614d731a4ab` | `collection_log_msci_standalone_indonesia_market.json`, `sampel_msci_standalone_indonesia_market.csv` |
| `msci standalone` | 224 | `pilot_msci_standalone.csv` / `.jsonl` | `279969d993aea1409c50e7dab2d5be61a2ea50efa29f72b92072ab5947f889d1` | `2c4a6136c82798d72d4d6e4e331452c8b0dee03465015f1b3e62da19d418dfd0` | `collection_log_msci_standalone.json`, `sampel_msci_standalone.csv` |
| `msci indonesia` | 500 | `pilot_msci_indonesia.csv` / `.jsonl` | `624ef03a0a115e51aa3d26d193403350245cd7db20c7391f4cc9977c1d188971` | `bbd1ed300cd313d6a2fb0e96ae994f1c48ee21d6a4d2b09b2458f51d9c130a4c` | `collection_log_msci_indonesia.json`, `sampel_msci_indonesia.csv` |
| `msci downgrade` | 198 | `pilot_msci_downgrade.csv` / `.jsonl` | `e81368708c3751ffef57a26573192f6a207609ece5176e24c1822322990ece83` | `b68992156c84f6e391541d8f5963bbc3a1b8aa2b1c4d50c850ad6b8e6fbf7c3e` | `collection_log_msci_downgrade.json`, `sampel_msci_downgrade.csv` |
| `msci ihsg` | 181 | `pilot_msci_ihsg.csv` / `.jsonl` | `bb8fe8d36e58177e5ecd479d5076f07cde54023fa8a8dc36d5b45b87b53b2eb4` | `f7229d195c59b10a193978b3cb74a7d14d90cf21bd61ae841422911e9e6413b9` | `collection_log_msci_ihsg.json`, `sampel_msci_ihsg.csv` |
| `reklasifikasi msci` | 32 | `pilot_reklasifikasi_msci.csv` / `.jsonl` | `9b2b8b7fbdb3ad1fe41c5889234d42b648058c88728e595f60ebd70ddc896fa2` | `39a6277b6217fec20e27ffe09797709d02c4c02db32aa52f924fc74d4bb37789` | `collection_log_reklasifikasi_msci.json`, `sampel_reklasifikasi_msci.csv` |

### 2. Data Hasil Olahan (*Processed Data*) & Laporan
| Berkas | Keterangan | SHA-256 |
|---|---|---|
| `all_unique_msci_posts.csv` / `.json` | Korpus gabungan unik hasil deduplikasi URI (873 post) | `38ab1e79467dd5799adfb78b62ca41826b3026a392513002bf111299707bdde4` (CSV) |
| `all_unique_msci_preprocessed.csv` / `.jsonl` | Hasil *case folding*, *cleaning*, *tokenizing*, *stopword removal*, dan *stemming* Sastrawi | `1c7d8d3d24dbe0b4ae1b4207c74c1d8e1d0bb0d359842980bde24915f9f266cb` (CSV) |
| `all_unique_msci_sentiment.csv` / `.json` | Hasil klasifikasi sentimen 3-kelas IndoBERT + skor probabilitas | `b34b92c13a828b6351d09dd6e2f615974d19777ad0ed266cb502a6b405` (CSV) |
| `keyword_weights_indobert.json` | Bobot kata kunci pembeda tiap sentimen (c-TF-IDF) | — |
| `eda_msci_dashboard.html` | Dasbor visualisasi interaktif berbasis HTML | — |
| `Laporan_Analisis_MSCI_Standalone_Bluesky.pdf` | Laporan analisis akhir (PDF, 10 halaman) | `46d874bb8df9fc00d61003ae77ab6541ea777b1ee9db2f3790634dd4df8bbf40` |
| `Laporan_Analisis_MSCI_Standalone_Bluesky.docx` | Laporan analisis akhir (Word) | `d24eccd713756451e6a38ee9edd51156beb3d45f136cf149075630f64f22c033` |

### 3. Skrip Reproduksi
1. `crawl_msci.py` — Penarikan data multi-keyword & pencatatan `collection_log_*.json` (kredensial dibaca dari variabel lingkungan `BSKY_HANDLE` / `BSKY_APP_PASSWORD` atau prompt interaktif).
2. `analisis_materi4_msci.py` — Perhitungan presisi Wilson 95%, `harian.describe()`, CR1/CR5/CR10, bigram, dan domain.
3. `preprocessing_msci.py` — Pipeline *tokenizing*, *stopword removal*, dan *stemming* Sastrawi.
4. `sentimen_indobert_msci.py` — Klasifikasi sentimen IndoBERT (`ayameRushia/bert-base-indonesian-1.5G-sentiment-analysis-smsa`) dan ekstraksi bobot kata kunci c-TF-IDF.
