import json
import os
import re
import time
from collections import Counter
import pandas as pd
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory

print("=" * 75)
print("TAHAP PREPROCESSING TEKS: DATASET MSCI INDONESIA MARKET")
print("Tahapan: Case Folding -> Cleaning -> Tokenizing -> Stopword Removal -> Stemming")
print("=" * 75)

# 1. Pemuatan Dataset Bersih Unik
input_file = "all_unique_msci_posts.csv"
if not os.path.exists(input_file):
    raise FileNotFoundError(f"Berkas {input_file} tidak ditemukan di direktori kerja!")

df = pd.read_csv(input_file, encoding="utf-8-sig")
print(f"[*] Berhasil memuat {len(df)} baris data dari {input_file}")

# 2. Inisialisasi Stopwords & Stemmer
print("[*] Menginisialisasi kamus stopword dan mesin stemmer Sastrawi...")
stop_factory = StopWordRemoverFactory()
sastrawi_stopwords = set(stop_factory.get_stop_words())

# Tambahan stopwords bahasa Indonesia & Inggris & Noise Sosmed
custom_stopwords = {
    # Bahasa Indonesia
    "yang", "di", "dan", "dari", "ini", "untuk", "ke", "pada", "adalah", "dengan",
    "akan", "juga", "itu", "atau", "oleh", "bisa", "tidak", "ada", "karena", "sudah",
    "saat", "lebih", "dalam", "bila", "jika", "lagi", "jadi", "hanya", "para", "ia",
    "kita", "mereka", "anda", "kami", "tersebut", "masih", "dapat", "belum", "saja",
    "antara", "namun", "seperti", "bagi", "lalu", "setelah", "tentang", "kembali",
    "terus", "banyak", "harus", "bukan", "hampir", "selalu", "secara", "begitu",
    "baca", "selengkapnya", "klik", "link", "halaman", "terkait", "dikutip",
    # Bahasa Inggris
    "the", "to", "in", "of", "and", "a", "for", "is", "on", "that", "it", "with",
    "as", "at", "by", "from", "be", "this", "an", "are", "not", "have", "has", "was",
    "were", "but", "all", "they", "we", "he", "she", "his", "her", "their", "our",
    "via", "breaking", "news", "translated", "after", "com", "co", "id"
}
all_stopwords = sastrawi_stopwords.union(custom_stopwords)

# Sastrawi Stemmer
stem_factory = StemmerFactory()
sastrawi_stemmer = stem_factory.create_stemmer()

# Istilah Keuangan & Pasar Modal yang dilindungi (Jangan dirusak stemmer)
PROTECTED_TERMS = {
    "msci": "msci",
    "ihsg": "ihsg",
    "bei": "bei",
    "idx": "idx",
    "ojk": "ojk",
    "downgrade": "downgrade",
    "standalone": "standalone",
    "rebalance": "rebalance",
    "rebalancing": "rebalance",
    "outflow": "outflow",
    "inflow": "inflow",
    "selloff": "selloff",
    "market": "market",
    "stocks": "stock",
    "stock": "stock",
    "shares": "share",
    "share": "share",
    "investor": "investor",
    "investasi": "investasi"
}

# 3. Fungsi-fungsi Tahapan Preprocessing

def clean_text(text):
    """Tahap 1: Case Folding & Cleaning (Noise Removal)"""
    if not text or pd.isna(text):
        return ""
    t = str(text).lower()
    t = re.sub(r"https?://\S+|www\.\S+", " ", t)       # Hapus URL
    t = re.sub(r"@[\w\.\-]+", " ", t)                  # Hapus mention @user
    t = re.sub(r"#\w+", " ", t)                        # Hapus hashtag
    t = re.sub(r"[^\w\s]", " ", t)                     # Hapus simbol & tanda baca
    t = re.sub(r"\d+", " ", t)                         # Hapus angka
    t = re.sub(r"\s+", " ", t).strip()                 # Normalisasi spasi
    return t

def tokenize(text):
    """Tahap 2: Tokenizing"""
    if not text:
        return []
    # Tokenisasi berbasis regex kata alfabetik
    tokens = [w for w in text.split() if len(w) > 1]
    return tokens

def remove_stopwords(tokens):
    """Tahap 3: Stopword Removal / Filtering"""
    return [w for w in tokens if w not in all_stopwords and len(w) > 2]

# 4. Eksekusi Tahapan Awal (Cleaning, Tokenizing, Filtering)
print("[*] Melakukan Case Folding, Cleaning, Tokenizing, dan Stopword Removal...")
t0 = time.time()

df["clean_text"] = df["text"].apply(clean_text)
df["tokens"] = df["clean_text"].apply(tokenize)
df["tokens_filtered"] = df["tokens"].apply(remove_stopwords)

# 5. Stemming Cerdas dengan Vocabulary Caching
print("[*] Mengumpulkan kosa kata unik (*unique vocabulary*) untuk optimasi Stemming...")
all_filtered_words = set()
for tokens in df["tokens_filtered"]:
    all_filtered_words.update(tokens)

print(f"[*] Total kosa kata unik yang akan di-stem: {len(all_filtered_words)} kata")
print("[*] Memulai proses stemming Sastrawi...")

stem_cache = {}
t_stem_start = time.time()
for w in all_filtered_words:
    if w in PROTECTED_TERMS:
        stem_cache[w] = PROTECTED_TERMS[w]
    else:
        stem_cache[w] = sastrawi_stemmer.stem(w)

t_stem_end = time.time()
print(f"[*] Stemming selesai dalam {t_stem_end - t_stem_start:.2f} detik!")

def stem_tokens(tokens):
    return [stem_cache.get(w, w) for w in tokens if stem_cache.get(w, w)]

df["tokens_stemmed"] = df["tokens_filtered"].apply(stem_tokens)
df["preprocessed_text"] = df["tokens_stemmed"].apply(lambda tok: " ".join(tok))

# Konversi list tokens ke string representasi JSON untuk ekspor CSV
df["tokens_str"] = df["tokens"].apply(lambda x: json.dumps(x, ensure_ascii=False))
df["tokens_filtered_str"] = df["tokens_filtered"].apply(lambda x: json.dumps(x, ensure_ascii=False))
df["tokens_stemmed_str"] = df["tokens_stemmed"].apply(lambda x: json.dumps(x, ensure_ascii=False))

# 6. Ekspor Berkas Hasil Preprocessing
output_csv = "all_unique_msci_preprocessed.csv"
output_jsonl = "all_unique_msci_preprocessed.jsonl"

export_columns = [
    "uri", "author_handle", "created_at", "waktu_wib", "tanggal", "jam",
    "text", "clean_text", "preprocessed_text",
    "tokens_stemmed_str", "tokens_filtered_str", "langs",
    "like_count", "repost_count", "reply_count"
]

df[export_columns].to_csv(output_csv, index=False, encoding="utf-8-sig")

with open(output_jsonl, "w", encoding="utf-8") as jf:
    for _, row in df.iterrows():
        rec = {
            "uri": row["uri"],
            "author_handle": row["author_handle"],
            "created_at": row["created_at"],
            "waktu_wib": row["waktu_wib"],
            "original_text": row["text"],
            "clean_text": row["clean_text"],
            "tokens": row["tokens"],
            "tokens_filtered": row["tokens_filtered"],
            "tokens_stemmed": row["tokens_stemmed"],
            "preprocessed_text": row["preprocessed_text"],
            "langs": row.get("langs", ""),
            "like_count": row.get("like_count", 0),
            "repost_count": row.get("repost_count", 0)
        }
        jf.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"\n[✓] Berkas hasil preprocessing berhasil disimpan:")
print(f"  - CSV   : {output_csv} ({os.path.getsize(output_csv)} bytes)")
print(f"  - JSONL : {output_jsonl} ({os.path.getsize(output_jsonl)} bytes)")

# 7. Evaluasi Statistik Sebelum vs Sesudah Preprocessing
words_raw = []
for t in df["text"].fillna(""):
    words_raw.extend(str(t).split())

words_clean = []
for t in df["clean_text"]:
    words_clean.extend(t.split())

words_filtered = []
for toks in df["tokens_filtered"]:
    words_filtered.extend(toks)

words_stemmed = []
for toks in df["tokens_stemmed"]:
    words_stemmed.extend(toks)

print("\n" + "=" * 75)
print("STATISTIK KOMPARATIF HASIL PREPROCESSING")
print("=" * 75)
print(f"1. Total Kata Mentah (Original)     : {len(words_raw):>6} kata (Kosa kata unik: {len(set(words_raw))})")
print(f"2. Setelah Cleaning & Case Folding   : {len(words_clean):>6} kata (Kosa kata unik: {len(set(words_clean))})")
print(f"3. Setelah Stopword Removal          : {len(words_filtered):>6} kata (Kosa kata unik: {len(set(words_filtered))})")
print(f"4. Setelah Stemming Sastrawi         : {len(words_stemmed):>6} kata (Kosa kata unik: {len(set(words_stemmed))})")
reduction_rate = (1 - (len(words_stemmed) / len(words_raw))) * 100 if words_raw else 0
print(f"-> Reduksi Redundansi & Derau       : {reduction_rate:.2f}%")

print("\n--- TOP 20 KATA DASAR SETELAH PREPROCESSING (STEMMED & CLEAN) ---")
stemmed_counter = Counter(words_stemmed).most_common(20)
for rank, (word, count) in enumerate(stemmed_counter, 1):
    print(f" {rank:>2}. {word:<22}: {count:>4} kemunculan")

print("\n" + "=" * 75)
print("CONTOH TRANSFORMASI PREPROCESSING (BEFORE VS AFTER)")
print("=" * 75)
sample_indices = [0, 5, 10, 25, 50]
for idx in sample_indices:
    if idx < len(df):
        row = df.iloc[idx]
        print(f"\n[Contoh #{idx+1} | @{row['author_handle']}]")
        print(f"  - Original : \"{row['text'][:120]}...\"" if len(str(row['text'])) > 120 else f"  - Original : \"{row['text']}\"")
        print(f"  - Cleaned  : \"{row['clean_text'][:120]}\"")
        print(f"  - Stemmed  : \"{row['preprocessed_text'][:120]}\"")
        print(f"  - Tokens   : {row['tokens_stemmed'][:8]}")

print("\n[SELESAI] Tahapan Preprocessing Berhasil Sempurna!\n")
