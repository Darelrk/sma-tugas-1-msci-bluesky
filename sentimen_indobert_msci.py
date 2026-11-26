import json
import os
import re
import time
from collections import Counter
import numpy as np
import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sklearn.feature_extraction.text import TfidfVectorizer

print("=" * 80)
print("KLASIFIKASI SENTIMEN DATASET MSCI MENGGUNAKAN INDOBERT & DOMAIN FINANCIAL AWARE")
print("Model Transformer: ayameRushia/bert-base-indonesian-1.5G-sentiment-analysis-smsa")
print("Kelas: Positif | Netral | Negatif")
print("=" * 80)

# 1. Pemuatan Dataset Hasil Preprocessing
preprocessed_file = "all_unique_msci_preprocessed.csv"
if not os.path.exists(preprocessed_file):
    raise FileNotFoundError(f"Berkas {preprocessed_file} tidak ditemukan!")

df = pd.read_csv(preprocessed_file, encoding="utf-8-sig")
print(f"[*] Berhasil memuat {len(df)} postingan dari {preprocessed_file}")

# 2. Inisialisasi Model IndoBERT (Lokal Cache)
MODEL_NAME = "ayameRushia/bert-base-indonesian-1.5G-sentiment-analysis-smsa"
print(f"[*] Memuat model transformer & tokenizer [{MODEL_NAME}]...")
t_load_start = time.time()

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
model.eval()
print(f"[*] Model berhasil dimuat ke [{device}] dalam {time.time() - t_load_start:.2f} detik")

# 3. Leksikon Finansial (Loughran-McDonald & InSet Market Adaptation)
FINANCIAL_NEGATIVE = {
    "downgrade", "anjlok", "plunge", "kejatuhan", "gantung", "dana keluar", "merosot",
    "terpuruk", "tertekan", "kekhawatiran", "warning", "selloff", "rout", "outflow",
    "ancam", "hancur", "terburuk", "ambles", "jatuh", "rugi", "panik", "kebakaran",
    "pelepasan", "koreksi tajam", "tekanan jual", "peringatan", "terparah"
}

FINANCIAL_POSITIVE = {
    "rebound", "penguatan", "menguat", "tumbuh", "positif", "optimis", "keuntungan",
    "kenaikan", "lonjakan", "terbang", "hijau", "surplus", "inflow", "aman", "stabil",
    "sukses", "peluang", "meningkat", "percaya diri", "tahan banting", "resilient"
}

# 4. Inferensi Sentimen Berkelompok (Batch Inference)
BATCH_SIZE = 32
texts = []
for _, row in df.iterrows():
    # Ambil teks asli tanpa link URL untuk konteks semantik penuh
    raw = str(row.get("text", "")).strip()
    clean_no_url = re.sub(r"https?://\S+", "", raw).strip()
    texts.append(clean_no_url if clean_no_url else "netral")

print(f"[*] Menjalankan inferensi IndoBERT secara berkelompok (Batch size = {BATCH_SIZE})...")
t_infer_start = time.time()

raw_probs = []
with torch.no_grad():
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        inputs = tokenizer(
            batch,
            padding=True,
            truncation=True,
            max_length=128,
            return_tensors="pt"
        ).to(device)
        
        outputs = model(**inputs)
        probs = torch.softmax(outputs.logits, dim=-1).cpu().numpy()
        raw_probs.extend(probs)

print(f"[*] Inferensi transformer selesai dalam {time.time() - t_infer_start:.2f} detik")

# 5. Integrasi Domain Financial Context
sent_labels = []
conf_scores = []
final_prob_pos = []
final_prob_neu = []
final_prob_neg = []

for idx, p in enumerate(raw_probs):
    p_pos, p_neu, p_neg = float(p[0]), float(p[1]), float(p[2])
    text_lower = texts[idx].lower()
    
    # Hitung bobot leksikon pasar modal
    neg_score = sum(1.5 for kw in FINANCIAL_NEGATIVE if kw in text_lower)
    pos_score = sum(1.5 for kw in FINANCIAL_POSITIVE if kw in text_lower)
    
    # Sesuaikan probabilitas dengan prioritas konteks domain pasar modal
    adj_pos = p_pos + (0.35 * pos_score)
    adj_neg = p_neg + (0.35 * neg_score)
    adj_neu = p_neu
    
    # Normalisasi kembali ke distribusi probabilitas sum = 1
    total_adj = adj_pos + adj_neu + adj_neg
    adj_pos /= total_adj
    adj_neu /= total_adj
    adj_neg /= total_adj
    
    # Penentuan label dominan
    if adj_neg > adj_pos and adj_neg > 0.40:
        label = "Negatif"
        conf = adj_neg
    elif adj_pos > adj_neg and adj_pos > 0.40:
        label = "Positif"
        conf = adj_pos
    else:
        label = "Netral"
        conf = adj_neu
        
    sent_labels.append(label)
    conf_scores.append(round(conf, 4))
    final_prob_pos.append(round(adj_pos, 4))
    final_prob_neu.append(round(adj_neu, 4))
    final_prob_neg.append(round(adj_neg, 4))

df["sentimen"] = sent_labels
df["prob_positif"] = final_prob_pos
df["prob_netral"] = final_prob_neu
df["prob_negatif"] = final_prob_neg
df["skor_konfidensi"] = conf_scores

# 6. Ekspor Berkas Hasil Sentimen
output_csv = "all_unique_msci_sentiment.csv"
output_json = "all_unique_msci_sentiment.json"

export_cols = [
    "uri", "author_handle", "created_at", "waktu_wib", "tanggal", "jam",
    "text", "clean_text", "preprocessed_text", "sentimen",
    "prob_positif", "prob_netral", "prob_negatif", "skor_konfidensi",
    "like_count", "repost_count", "reply_count"
]
df[export_cols].to_csv(output_csv, index=False, encoding="utf-8-sig")

with open(output_json, "w", encoding="utf-8") as jf:
    json.dump(df[export_cols].to_dict(orient="records"), jf, indent=2, ensure_ascii=False)

print(f"\n[✓] Berkas hasil sentimen tersimpan:")
print(f"  - CSV  : {output_csv} ({os.path.getsize(output_csv)} bytes)")
print(f"  - JSON : {output_json} ({os.path.getsize(output_json)} bytes)")

# 7. Ringkasan Distribusi Sentimen
total_post = len(df)
sent_counts = df["sentimen"].value_counts()

print("\n" + "=" * 70)
print("DISTRIBUSI SENTIMEN DATASET MSCI STANDALONE INDONESIA MARKET")
print("=" * 70)
for s in ["Negatif", "Netral", "Positif"]:
    cnt = sent_counts.get(s, 0)
    pct = (cnt / total_post) * 100
    print(f" - {s:<10} : {cnt:>4} post ({pct:>5.1f}%)")

# 8. Dinamika Sentimen Sepanjang Waktu (WIB)
df["tanggal_wib"] = pd.to_datetime(df["created_at"], format="ISO8601", utc=True).dt.tz_convert("Asia/Jakarta").dt.date
kunci_tgl = [pd.to_datetime(t).date() for t in ["2026-10-15", "2026-10-16", "2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22", "2026-11-12", "2026-11-23"]]
sub_df = df[df["tanggal_wib"].isin(kunci_tgl)]
tgl_pivot = pd.crosstab(sub_df["tanggal_wib"], sub_df["sentimen"], margins=True)

print("\n--- Sebaran Sentimen pada Hari-Hari Kunci (WIB) ---")
print(tgl_pivot)

# 9. Pembobotan Kata Kunci Berdasarkan Sentimen (Class-based TF-IDF / Keyword Weights)
print("\n" + "=" * 70)
print("PEMBOBOTAN KATA KUNCI PER SENTIMEN (KEYWORD WEIGHTS)")
print("=" * 70)

docs_per_class = df.groupby("sentimen")["preprocessed_text"].apply(lambda texts: " ".join(texts.fillna("")))
tfidf = TfidfVectorizer(max_features=1500, ngram_range=(1, 2))
tfidf_matrix = tfidf.fit_transform(docs_per_class)
features = np.array(tfidf.get_feature_names_out())

keyword_weights_summary = {}
for idx, sent_class in enumerate(docs_per_class.index):
    row = tfidf_matrix[idx].toarray()[0]
    top_indices = np.argsort(row)[::-1][:10]
    top_words = features[top_indices]
    top_weights = row[top_indices]
    
    keyword_weights_summary[sent_class] = list(zip(top_words, top_weights))
    print(f"\n--- Top 10 Bobot Kata Kunci Sentimen [{sent_class.upper()}] ---")
    for w, sc in zip(top_words, top_weights):
        print(f"  * {w:<25} : Bobot {sc:.4f}")

# Simpan ringkasan bobot kata kunci ke JSON
with open("keyword_weights_indobert.json", "w", encoding="utf-8") as kwf:
    json.dump({k: [{"kata": w, "bobot": round(float(s), 4)} for w, s in v] for k, v in keyword_weights_summary.items()}, kwf, indent=2)

print("\n[✓] Bobot kata kunci disimpan ke: keyword_weights_indobert.json")

# 10. Contoh Postingan per Kelas Sentimen
print("\n" + "=" * 70)
print("CONTOH POSTINGAN PER KELAS SENTIMEN")
print("=" * 70)
for s in ["Negatif", "Positif", "Netral"]:
    sample = df[df["sentimen"] == s].sort_values(by="skor_konfidensi", ascending=False).head(2)
    print(f"\n[SENTIMEN: {s.upper()}]")
    for _, r in sample.iterrows():
        t_prev = (r['text'][:110] + '...') if len(str(r['text'])) > 110 else str(r['text'])
        print(f"  - @{r['author_handle']} (Skor: {r['skor_konfidensi']:.4f}):")
        print(f"    \"{t_prev}\"")

print("\n[SELESAI] Klasifikasi Sentimen & Pembobotan Kata Kunci Berhasil!\n")
