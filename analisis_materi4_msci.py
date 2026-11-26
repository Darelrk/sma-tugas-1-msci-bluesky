import glob
import math
import os
import re
import json
from collections import Counter
import pandas as pd
import numpy as np

print("=" * 80)
print("ANALISIS EKSPLORATIF (EDA) DATASET MSCI INDONESIA MARKET")
print("Sesuai Modul: Materi Praktik 4 Akuisisi dan Analisis Data Bluesky")
print("=" * 80)

# -------------------------------------------------------------------
# 0. PEMUATAN BERKAS & VALIDASI LINTAS KATA KUNCI (LANGKAH 6)
# -------------------------------------------------------------------
pilot_files = [f for f in glob.glob("pilot_*.csv") if "msci" in f or "reklasifikasi" in f]
print(f"\nDitemukan {len(pilot_files)} berkas pilot:")
for pf in sorted(pilot_files):
    print(f"  - {pf}")

df_list = []
kw_stats = []
for pf in sorted(pilot_files):
    kw_name = os.path.basename(pf).replace("pilot_", "").replace(".csv", "").replace("_", " ")
    temp_df = pd.read_csv(pf, encoding="utf-8-sig")
    temp_df["source_keyword"] = kw_name
    df_list.append(temp_df)
    kw_stats.append({
        "kata_kunci": kw_name,
        "total_mentah": len(temp_df),
        "post_unik": temp_df["uri"].nunique()
    })

df_all = pd.concat(df_list, ignore_index=True)
total_mentah = len(df_all)
df_unique = df_all.drop_duplicates(subset="uri").copy()
total_unik = len(df_unique)
duplikasi_lintas = total_mentah - total_unik

print("\n" + "=" * 70)
print("LANGKAH 6: RINGKASAN KOLEKSI & DUPLIKASI LINTAS KATA KUNCI")
print("=" * 70)
print(f"{'Kata Kunci':<35} | {'Mentah':<8} | {'Unik':<8}")
print("-" * 55)
for s in kw_stats:
    print(f"{s['kata_kunci']:<35} | {s['total_mentah']:<8} | {s['post_unik']:<8}")
print("-" * 55)
print(f"Total Baris Mentah        : {total_mentah}")
print(f"Total Post Unik Gabungan  : {total_unik}")
print(f"Duplikasi Lintas Keyword  : {duplikasi_lintas} post ({(duplikasi_lintas/total_mentah*100 if total_mentah else 0):.2f}%)")

# -------------------------------------------------------------------
# 1. EVALUASI SAMPEL & INTERVAL WILSON SCORE 95% (LANGKAH 7)
# -------------------------------------------------------------------
print("\n" + "=" * 70)
print("LANGKAH 7: EVALUASI KUALITAS KATA KUNCI DENGAN WILSON SCORE (95% CI)")
print("=" * 70)

def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = k / n
    c = (p + z*z/(2*n)) / (1 + z*z/n)
    h = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / (1 + z*z/n)
    return max(0.0, c - h), min(1.0, c + h)

sample_files = [f for f in glob.glob("sampel_*.csv") if "msci" in f or "reklasifikasi" in f]

def label_relevansi(text):
    if not text or pd.isna(text):
        return 0, "Teks kosong / media gambar saja"
    t = str(text).lower()
    core_finance = ["msci", "standalone", "downgrade", "emerging market", "ihsg", "idx", "bei", "bursa efek", "pasar modal", "reklasifikasi", "saham", "capital outflow", "investor asing"]
    if any(cf in t for cf in core_finance):
        return 1, "Relevan dengan evaluasi/reklasifikasi pasar modal Indonesia oleh MSCI"
    return 0, "Di luar konteks pasar modal Indonesia"

sample_results = []
for sf in sorted(sample_files):
    kw_name = os.path.basename(sf).replace("sampel_", "").replace(".csv", "").replace("_", " ")
    s_df = pd.read_csv(sf, encoding="utf-8-sig")
    
    # Labeling
    s_df["relevan"] = s_df["text"].apply(lambda x: label_relevansi(x)[0])
    s_df["catatan"] = s_df["text"].apply(lambda x: label_relevansi(x)[1])
    s_df.to_csv(sf, index=False, encoding="utf-8-sig")
    
    n = len(s_df[s_df["text"].notna()])
    k = int((s_df["relevan"] == 1).sum())
    p = k / n if n > 0 else 0
    lo, hi = wilson(k, n)
    
    if p >= 0.70:
        keputusan = "Pertahankan (Presisi Tinggi)"
    elif p >= 0.50:
        keputusan = "Bersyarat (Perlu Filter Kontekstual)"
    else:
        keputusan = "Gugurkan (Derau Tinggi)"
        
    sample_results.append({
        "kata_kunci": kw_name,
        "n": n,
        "k_relevan": k,
        "presisi": p,
        "wilson_ci": f"[{lo:.2f} - {hi:.2f}]",
        "keputusan": keputusan
    })

print(f"{'Kata Kunci':<32} | {'n':<4} | {'k':<4} | {'Presisi':<7} | {'Wilson 95% CI':<15} | {'Keputusan'}")
print("-" * 85)
for sr in sample_results:
    print(f"{sr['kata_kunci']:<32} | {sr['n']:<4} | {sr['k_relevan']:<4} | {sr['presisi']:<7.2f} | {sr['wilson_ci']:<15} | {sr['keputusan']}")

# -------------------------------------------------------------------
# 2. PENGOLAHAN DERET WAKTU (BAGIAN 6)
# -------------------------------------------------------------------
print("\n" + "=" * 70)
print("BAGIAN 6: PENGOLAHAN DERET WAKTU & STATISTIK DESKRIPTIF HARIAN")
print("=" * 70)

df_unique["waktu_utc"] = pd.to_datetime(df_unique["created_at"], format="ISO8601", utc=True, errors="coerce")
df_unique = df_unique.dropna(subset=["waktu_utc"]).copy()
df_unique["waktu_wib"] = df_unique["waktu_utc"].dt.tz_convert("Asia/Jakarta")
df_unique["tanggal"] = df_unique["waktu_wib"].dt.date
df_unique["jam"] = df_unique["waktu_wib"].dt.hour

harian = df_unique.groupby("tanggal").size().rename("post")

print("--- Hasil harian.describe() ---")
print(harian.describe())

print("\n--- Sebaran Tanggal dengan Volume Terbesar (Puncak Diskusi) ---")
print(harian.sort_values(ascending=False).head(10))

# -------------------------------------------------------------------
# 3. KASUS KHUSUS & KONSENTRASI AKUN (BAGIAN 6.1)
# -------------------------------------------------------------------
print("\n" + "=" * 70)
print("BAGIAN 6.1: KASUS KHUSUS (TEKS KOSONG & DUPLIKAT) & KONSENTRASI AKUN")
print("=" * 70)

df_unique["teks_norm"] = (df_unique["text"].fillna("").str.lower()
    .str.replace(r"https?://\S+", "", regex=True)
    .str.replace(r"\s+", " ", regex=True).str.strip())
df_unique["teks_kosong"] = df_unique["teks_norm"] == ""
df_unique["dup_teks"] = df_unique.duplicated("teks_norm", keep=False) & ~df_unique["teks_kosong"]

total_posts = len(df_unique)
n_kosong = int(df_unique["teks_kosong"].sum())
n_dup = int(df_unique["dup_teks"].sum())

print(f"Total Post Unik         : {total_posts}")
print(f"Teks Kosong (Media Saja): {n_kosong} ({(n_kosong/total_posts*100):.2f}%)")
print(f"Teks Duplikat           : {n_dup} ({(n_dup/total_posts*100):.2f}%)")

top_authors = df_unique["author_handle"].value_counts()
cr1 = round(top_authors.iloc[0] / total_posts, 3) if len(top_authors) >= 1 else 0
cr5 = round(top_authors.head(5).sum() / total_posts, 3) if len(top_authors) >= 5 else 0
cr10 = round(top_authors.head(10).sum() / total_posts, 3) if len(top_authors) >= 10 else 0

print(f"\nKonsentrasi Akun:")
print(f" - CR1  (1 Akun Teratas)   : {cr1*100:.1f}% ({top_authors.index[0]}: {top_authors.iloc[0]} post)")
print(f" - CR5  (5 Akun Teratas)   : {cr5*100:.1f}%")
print(f" - CR10 (10 Akun Teratas)  : {cr10*100:.1f}%")

print("\nTop 10 Akun Paling Aktif:")
for rank, (handle, count) in enumerate(top_authors.head(10).items(), 1):
    print(f" {rank:>2}. @{handle:<30} : {count:>4} post ({(count/total_posts*100):.1f}%)")

# -------------------------------------------------------------------
# 4. MATRIKS WAWASAN SOCIAL MEDIA ANALYTICS (BAGIAN 7)
# -------------------------------------------------------------------
print("\n" + "=" * 70)
print("BAGIAN 7: EKSTRAKSI MATRIKS WAWASAN SMA (KATA, BIGRAM, DOMAIN, ENGAGEMENT)")
print("=" * 70)

# Stopwords bahasa Indonesia dan istilah teknis
stopwords = {
    "yang", "di", "dan", "dari", "ini", "untuk", "ke", "pada", "adalah", "dengan",
    "akan", "juga", "itu", "atau", "oleh", "bisa", "tidak", "ada", "karena", "sudah",
    "saat", "lebih", "dalam", "bila", "jika", "lagi", "jadi", "hanya", "para", "ia",
    "kita", "mereka", "anda", "kami", "tersebut", "masih", "dapat", "belum", "saja",
    "the", "to", "in", "of", "and", "a", "for", "is", "on", "that", "it", "with",
    "as", "at", "by", "from", "be", "this", "an", "are", "not", "have", "has", "was"
}

words = []
bigrams = []
domains = []

for _, r in df_unique.iterrows():
    raw_text = str(r["text"]) if pd.notna(r["text"]) else ""
    
    # Ekstraksi Link Domain
    urls = re.findall(r"https?://([A-Za-z0-9\.\-_]+)", raw_text)
    for d in urls:
        domains.append(d.lower())
        
    # Pembersihan kata
    clean = re.sub(r"https?://\S+", "", raw_text.lower())
    clean = re.sub(r"[^\w\s]", " ", clean)
    tokens = [w for w in clean.split() if len(w) > 2 and w not in stopwords]
    words.extend(tokens)
    
    for i in range(len(tokens) - 1):
        bigrams.append(f"{tokens[i]} {tokens[i+1]}")

word_counts = Counter(words).most_common(15)
bigram_counts = Counter(bigrams).most_common(15)
domain_counts = Counter(domains).most_common(10)

print("\n--- Top 15 Kata Paling Sering Muncul (Unigram) ---")
for w, c in word_counts:
    print(f" - {w:<20}: {c:>4} kali")

print("\n--- Top 15 Frasa 2 Kata (Bigram) ---")
for b, c in bigram_counts:
    print(f" - {b:<30}: {c:>4} kali")

print("\n--- Ekologi Informasi: Domain Web Paling Banyak Dirujuk ---")
if domain_counts:
    for d, c in domain_counts:
        print(f" - {d:<30}: {c:>4} rujukan")
else:
    print(" (Tidak ada tautan eksternal terdeteksi dalam teks)")

# Engagement Highlights
print("\n--- Post dengan Keterlibatan (Engagement) Tertinggi ---")
top_liked = df_unique.sort_values(by="like_count", ascending=False).head(5)
for idx, r in top_liked.iterrows():
    print(f"Likes: {r['like_count']:>3} | Reposts: {r['repost_count']:>3} | @{r['author_handle']}")
    txt_preview = (r['text'][:90] + '...') if len(r['text']) > 90 else r['text']
    print(f"  Teks: \"{txt_preview}\"")

# Distribusi Bahasa Platform vs Realita
print("\n--- Distribusi Tag Bahasa Platform (Langs) ---")
lang_counts = df_unique["langs"].fillna("kosong / tidak ada tag").value_counts()
print(lang_counts.head(8))

print("\n" + "=" * 80)
print("ANALISIS LENGKAP SELESAI")
print("=" * 80)
