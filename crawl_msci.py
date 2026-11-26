#!/usr/bin/env python3
"""
=============================================================================
Kolektor Data Bluesky Multi-Keyword: Studi Kasus MSCI Indonesia Market
Kamus Kata Kunci Bertingkat (Tiered Keyword Dictionary - Bagian 3.1 Modul 4)
Rentang: 3 Bulan Terakhir (24 Agustus 2026 s/d 25 November 2026 WIB)
=============================================================================

Kamus Kata Kunci Bertingkat:
1. 'msci standalone indonesia market' (Frasa lengkap spesifik)
2. 'msci standalone'                  (Inti status standalone)
3. 'msci indonesia'                   (Cakupan indeks pasar Indonesia)
4. 'msci downgrade'                   (Isu penurunan kelas/peringkat)
5. 'msci ihsg'                        (Dampak pada indeks saham gabungan)
6. 'reklasifikasi msci'               (Mekanisme evaluasi bursa)
"""

import argparse
import csv
import datetime
import getpass
import hashlib
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

DEFAULT_BSKY_HANDLE = ""
DEFAULT_BSKY_APP_PASSWORD = ""

PUBLIC_HOST = "https://public.api.bsky.app"
PDS_HOST = "https://bsky.social"

DEFAULT_KEYWORDS = [
    "msci standalone indonesia market",
    "msci standalone",
    "msci indonesia",
    "msci downgrade",
    "msci ihsg",
    "reklasifikasi msci"
]

DEFAULT_START_WIB = "2026-08-24"
DEFAULT_END_WIB = "2026-11-25"

EXPORT_FIELDS = [
    "uri", "cid", "author_handle", "author_did", "created_at",
    "waktu_utc", "waktu_wib", "tanggal", "jam",
    "text", "langs", "like_count", "repost_count", "reply_count", "quote_count",
    "is_repost", "is_reply"
]


def hitung_sha256(filepath):
    if not os.path.exists(filepath):
        return None
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def konversi_wib_ke_utc(tanggal_str, jam_menit="00:00:00"):
    if not tanggal_str:
        return None
    dt_wib = datetime.datetime.strptime(f"{tanggal_str} {jam_menit}", "%Y-%m-%d %H:%M:%S")
    dt_utc = dt_wib - datetime.timedelta(hours=7)
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_timestamp_ke_wib(created_at_str):
    if not created_at_str:
        return "", "", "", ""
    try:
        clean_ts = created_at_str.replace("Z", "+00:00")
        dt_utc = datetime.datetime.fromisoformat(clean_ts)
        dt_wib = dt_utc.astimezone(datetime.timezone(datetime.timedelta(hours=7)))
        waktu_utc = dt_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
        waktu_wib = dt_wib.strftime("%Y-%m-%d %H:%M:%S WIB")
        tanggal = dt_wib.strftime("%Y-%m-%d")
        jam = dt_wib.hour
        return waktu_utc, waktu_wib, tanggal, jam
    except Exception:
        return created_at_str, "", "", ""


def xrpc_request(host, method, params=None, token=None, body=None, retries=5):
    url = f"{host}/xrpc/{method}"
    if params:
        clean = {k: v for k, v in params.items() if v is not None}
        url += "?" + urllib.parse.urlencode(clean)
    headers = {
        "Accept": "application/json",
        "User-Agent": "sma-msci-multikeyword/2.0"
    }
    data = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    for attempt in range(retries):
        req = urllib.request.Request(url, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=35) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                wait_header = e.headers.get("Retry-After")
                delay = int(wait_header) if wait_header and wait_header.isdigit() else 2 ** attempt + 1
                print(f"  [HTTP {e.code}] Rate limit/server sibuk. Menunggu {delay} detik...", file=sys.stderr)
                time.sleep(delay)
                continue
            detail = e.read().decode("utf-8", errors="replace")[:300]
            raise SystemExit(f"\n[ERROR] HTTP {e.code} pada {method}: {detail}")
        except urllib.error.URLError as e:
            print(f"  [Koneksi Error] Percobaan {attempt+1}/{retries}: {e.reason}", file=sys.stderr)
            time.sleep(3)
            continue
    raise SystemExit(f"\n[ERROR] Gagal memanggil {method} setelah {retries} percobaan.")


def muat_kredensial(arg_handle=None, arg_password=None):
    h = (arg_handle or DEFAULT_BSKY_HANDLE or "").strip()
    pw = (arg_password or DEFAULT_BSKY_APP_PASSWORD or "").strip()
    if not h or not pw:
        h = h or os.environ.get("BSKY_HANDLE", "")
        pw = pw or os.environ.get("BSKY_APP_PASSWORD", "")
    return h, pw


def login_bsky(handle=None, app_password=None):
    h, pw = muat_kredensial(handle, app_password)
    print(f"[*] Melakukan autentikasi untuk @{h}...")
    res = xrpc_request(
        PDS_HOST,
        "com.atproto.server.createSession",
        body={"identifier": h, "password": pw}
    )
    print("    [✓] Autentikasi berhasil! Sesi token dibuat.")
    return res["accessJwt"]


def flatten_post(post, item=None):
    rec = post.get("record", {})
    created_at = rec.get("createdAt", "")
    w_utc, w_wib, tgl, jam = parse_timestamp_ke_wib(created_at)

    raw_text = rec.get("text") or ""
    clean_text = raw_text.replace("\r\n", " ").replace("\n", " ").strip()

    return {
        "uri": post.get("uri"),
        "cid": post.get("cid"),
        "author_handle": post.get("author", {}).get("handle"),
        "author_did": post.get("author", {}).get("did"),
        "created_at": created_at,
        "waktu_utc": w_utc,
        "waktu_wib": w_wib,
        "tanggal": tgl,
        "jam": jam,
        "text": clean_text,
        "langs": ",".join(rec.get("langs") or []),
        "like_count": post.get("likeCount", 0),
        "repost_count": post.get("repostCount", 0),
        "reply_count": post.get("replyCount", 0),
        "quote_count": post.get("quoteCount", 0),
        "is_repost": bool(item and "reason" in item),
        "is_reply": "reply" in rec,
    }


def crawl_satu_keyword(query, since_utc, until_utc, token, max_posts=500, prefix="pilot_msci"):
    jsonl_filename = f"{prefix}.jsonl"
    jsonl_file = open(jsonl_filename, "w", encoding="utf-8")
    all_rows = []
    seen_uris = set()
    cursor = None
    halaman = 0

    print(f"\n>>> Mengambil data untuk kata kunci: '{query}'")
    try:
        while len(all_rows) < max_posts:
            halaman += 1
            batch_size = min(100, max_posts - len(all_rows))
            params = {
                "q": query,
                "limit": batch_size,
                "cursor": cursor,
                "sort": "latest",
                "since": since_utc,
                "until": until_utc
            }

            resp = xrpc_request(PDS_HOST, "app.bsky.feed.searchPosts", params=params, token=token)
            posts = resp.get("posts", [])
            new_cursor = resp.get("cursor")

            if not posts:
                print(f"    Halaman {halaman}: Data habis.")
                break

            for p in posts:
                row = flatten_post(p)
                jsonl_file.write(json.dumps(row, ensure_ascii=False) + "\n")
                if row["uri"] not in seen_uris:
                    seen_uris.add(row["uri"])
                all_rows.append(row)

            jsonl_file.flush()
            print(f"    Halaman {halaman}: +{len(posts)} post diambil (Total terkumpul: {len(all_rows)})")

            if not new_cursor or new_cursor == cursor or len(posts) < batch_size:
                break

            cursor = new_cursor
            time.sleep(0.4)

    finally:
        jsonl_file.close()

    return all_rows


def ekspor_csv(rows, csv_filename):
    with open(csv_filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=EXPORT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def buat_sampel(rows, sample_filename, sample_size=50, seed=42):
    if not rows:
        return
    random.seed(seed)
    n = min(len(rows), sample_size)
    sampled = random.sample(rows, n)

    sample_fields = ["uri", "created_at", "langs", "text", "relevan", "bahasa_sebenarnya", "catatan"]
    formatted = []
    for r in sampled:
        formatted.append({
            "uri": r.get("uri", ""),
            "created_at": r.get("created_at", ""),
            "langs": r.get("langs", ""),
            "text": r.get("text", ""),
            "relevan": "",
            "bahasa_sebenarnya": "",
            "catatan": ""
        })

    with open(sample_filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=sample_fields)
        writer.writeheader()
        writer.writerows(formatted)


def main():
    parser = argparse.ArgumentParser(
        description="Skrip Crawling Multi-Keyword MSCI Indonesia Market (Materi Praktik 4)",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("-k", "--keywords", nargs="+", default=DEFAULT_KEYWORDS,
                        help="Daftar kata kunci. Default: 6 kata kunci bertingkat MSCI")
    parser.add_argument("--start", default=DEFAULT_START_WIB,
                        help=f"Tanggal mulai WIB. Default: {DEFAULT_START_WIB}")
    parser.add_argument("--end", default=DEFAULT_END_WIB,
                        help=f"Tanggal akhir WIB. Default: {DEFAULT_END_WIB}")
    parser.add_argument("--max", type=int, default=500,
                        help="Batas maksimum post per kata kunci. Default: 500")
    parser.add_argument("--sample-size", type=int, default=50,
                        help="Jumlah sampel acak pelabelan. Default: 50")
    parser.add_argument("--seed", type=int, default=42,
                        help="Seed acak sampling. Default: 42")
    parser.add_argument("--pause", type=int, default=3,
                        help="Jeda detik antar kata kunci. Default: 3")

    args = parser.parse_args()

    keywords_list = args.keywords if args.keywords else DEFAULT_KEYWORDS

    since_utc = konversi_wib_ke_utc(args.start, "00:00:00")
    until_utc = konversi_wib_ke_utc(args.end, "00:00:00")

    print("=" * 75)
    print(" CRAWLER MULTI-KEYWORD MSCI INDONESIA MARKET (3 BULAN TERAKHIR)")
    print(" Sesuai Kamus Kata Kunci Bertingkat (Bagian 3.1 Materi Praktik 4)")
    print("=" * 75)
    print(f" Daftar Kata Kunci ({len(keywords_list)} kueri):")
    for i, kw in enumerate(keywords_list, 1):
        print(f"   {i}. {kw}")
    print(f" Jendela WIB       : {args.start} 00:00 WIB s/d {args.end} 00:00 WIB")
    print(f" Jendela UTC       : {since_utc} s/d {until_utc}")
    print(f" Max Post / Kueri  : {args.max}")
    print("=" * 75)

    # 1. Login Tunggal
    token = login_bsky()

    semua_post_unik = {}
    ringkasan_koleksi = []

    # 2. Loop Crawling tiap kata kunci
    for idx, kw in enumerate(keywords_list, 1):
        clean_kw = re.sub(r"[^\w\-_]", "_", kw.strip().lower())
        prefix = f"pilot_{clean_kw}"
        csv_file = f"{prefix}.csv"
        jsonl_file = f"{prefix}.jsonl"
        sample_file = f"sampel_{clean_kw}.csv"
        log_file = f"collection_log_{clean_kw}.json"

        w_mulai = datetime.datetime.now(datetime.timezone.utc).isoformat()
        rows = crawl_satu_keyword(
            query=kw,
            since_utc=since_utc,
            until_utc=until_utc,
            token=token,
            max_posts=args.max,
            prefix=prefix
        )
        w_selesai = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Ekspor CSV & Sampel
        ekspor_csv(rows, csv_file)
        buat_sampel(rows, sample_file, sample_size=args.sample_size, seed=args.seed)

        # Hash SHA-256
        hash_csv = hitung_sha256(csv_file)
        hash_jsonl = hitung_sha256(jsonl_file)
        hash_sample = hitung_sha256(sample_file)

        # Simpan Collection Log
        log_data = {
            "kata_kunci": kw,
            "waktu_eksekusi": {"mulai": w_mulai, "selesai": w_selesai},
            "jendela_waktu": {"wib_mulai": args.start, "wib_selesai": args.end, "since_utc": since_utc, "until_utc": until_utc},
            "total_baris": len(rows),
            "integritas_berkas": {
                "csv": {"berkas": csv_file, "sha256": hash_csv},
                "jsonl": {"berkas": jsonl_file, "sha256": hash_jsonl},
                "sampel": {"berkas": sample_file, "sha256": hash_sample}
            }
        }
        with open(log_file, "w", encoding="utf-8") as lf:
            json.dump(log_data, lf, indent=2, ensure_ascii=False)

        # Catat ke kumpulan gabungan unik
        for r in rows:
            u = r["uri"]
            if u not in semua_post_unik:
                semua_post_unik[u] = {
                    "uri": u,
                    "text": r.get("text", ""),
                    "author_handle": r.get("author_handle", ""),
                    "created_at": r.get("created_at", ""),
                    "waktu_wib": r.get("waktu_wib", ""),
                    "tanggal": r.get("tanggal", ""),
                    "jam": r.get("jam", ""),
                    "langs": r.get("langs", ""),
                    "like_count": r.get("like_count", 0),
                    "repost_count": r.get("repost_count", 0),
                    "reply_count": r.get("reply_count", 0),
                    "keywords": [kw]
                }
            else:
                if kw not in semua_post_unik[u]["keywords"]:
                    semua_post_unik[u]["keywords"].append(kw)

        ringkasan_koleksi.append({
            "kata_kunci": kw,
            "total_post": len(rows),
            "csv": csv_file,
            "sampel": sample_file,
            "sha256": hash_csv
        })

        if idx < len(keywords_list):
            print(f"    [Jeda] Istirahat {args.pause} detik sebelum kata kunci berikutnya...")
            time.sleep(args.pause)

    # 3. Simpan Berkas Gabungan Unik (all_unique_msci_posts.json & .csv)
    combined_json = "all_unique_msci_posts.json"
    combined_csv = "all_unique_msci_posts.csv"

    unique_list = list(semua_post_unik.values())
    with open(combined_json, "w", encoding="utf-8") as cf:
        json.dump(unique_list, cf, indent=2, ensure_ascii=False)

    with open(combined_csv, "w", newline="", encoding="utf-8-sig") as f:
        fieldnames = ["uri", "created_at", "waktu_wib", "tanggal", "jam", "author_handle", "text", "langs", "like_count", "repost_count", "reply_count", "keywords"]
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for u in unique_list:
            u_copy = dict(u)
            u_copy["keywords"] = ", ".join(u_copy.get("keywords", []))
            writer.writerow(u_copy)

    total_mentah = sum(x["total_post"] for x in ringkasan_koleksi)
    total_unik = len(semua_post_unik)

    print("\n" + "=" * 75)
    print(" RINGKASAN KOLEKSI DATA MULTI-KEYWORD MSCI")
    print("=" * 75)
    for item in ringkasan_koleksi:
        print(f" - {item['kata_kunci']:35}: {item['total_post']:>4} baris -> {item['csv']}")
    print("-" * 75)
    print(f" Total Mentah Terkumpul : {total_mentah} baris")
    print(f" Total Post Unik        : {total_unik} post")
    if total_mentah > 0:
        duplikasi = total_mentah - total_unik
        print(f" Duplikasi Lintas Kata  : {duplikasi} post ({(duplikasi/total_mentah*100):.1f}%)")
    print(f" Berkas Gabungan Unik   : {combined_json} & {combined_csv}")
    print("=" * 75)
    print("[SELESAI] Seluruh tahapan crawling multi-keyword berhasil!\n")


if __name__ == "__main__":
    main()
