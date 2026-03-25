import undetected_chromedriver as uc
import google.generativeai as genai
import time
import os
import re
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from dotenv import load_dotenv

# --- CONFIG ---
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key) 

model = genai.GenerativeModel('gemini-2.5-flash')

def get_dashboard_data(opsi):
    options = uc.ChromeOptions()
    current_dir = os.getcwd()
    options.add_argument(f"--user-data-dir={os.path.join(current_dir, 'profil_bot')}")
    options.add_argument("--window-position=-2000,0") 
    
    url_index = "https://eclass.ukdw.ac.id/e-class/id/kelas/index"
    driver = None
    try:
        driver = uc.Chrome(options=options, version_main=145)
        driver.get(url_index)
        time.sleep(5)

        # --- LOGIKA AUTO-LOGIN ---
        # Memastikan submit ditekan jika profil belum otomatis masuk
        if "login" in driver.current_url.lower() or len(driver.find_elements(uc.By.NAME, "id")) > 0:
            try:
                submit_button = driver.find_element(uc.By.CSS_SELECTOR, "input[type='submit']")
                submit_button.click()
                time.sleep(5)
                if driver.current_url != url_index: driver.get(url_index)
            except: pass

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # --- OPSI 1: DAFTAR KELAS (Ringkas) ---
        if opsi == 1:
            container = soup.find('div', id='content-right')
            if not container: return "Konten kelas tidak ditemukan."
            kelas_boxes = container.find_all('div', class_='kelas_box')
            hasil = ["[" + " ".join(box.find('h2').get_text().split()) + "]" for box in kelas_boxes]
            return "\n".join(hasil) if hasil else "Tidak ada kelas terdaftar."

        # --- OPSI 2: PENGUMUMAN TERBARU (Format: [Tgl] Title - Isi) ---
        elif opsi == 2:
            container = soup.find('div', id='content-left')
            links = container.find_all('a', class_='menu mc')
            hasil = []
            for link in links:
                if 'pengumuman/baca' in link.get('href', ''):
                    # Ambil semua teks, pisahkan berdasarkan baris baru/spasi
                    parts = [p.strip() for p in link.get_text(separator="|").split('|') if p.strip()]
                    
                    tgl = parts[0] if len(parts) > 0 else "No Date"
                    # Title diambil dari atribut 'title' agar tidak terpotong "..."
                    title = link.get('title', 'No Title')
                    # Isi biasanya diawali '>'
                    isi = next((p.replace('>', '') for p in parts if '>' in p), "Tidak ada detail")
                    
                    hasil.append(f"📣 [{tgl}] {title} - {isi}")
            return "\n".join(hasil) if hasil else "Tidak ada pengumuman."

        # --- OPSI 3: TUGAS TERBARU (Format: [DL] Matkul - Isi) ---
        elif opsi == 3:
            container = soup.find('div', id='content-left')
            if not container: return "Konten tugas tidak ditemukan."
            
            links = container.find_all('a', class_='menu mc')
            hasil = []
            for link in links:
                # Filter hanya yang link tugas
                if 'detail_tugas' in link.get('href', ''):
                    deadline = link.get_text(separator="|", strip=True).split('|')[0]
                    matkul = link.get('title', 'No Title')
                    nama_tugas = link.get_text(separator="|", strip=True).split('>')[-1]
                    hasil.append(f"📅 [DL: {deadline}] {matkul} - Tugas: {nama_tugas}")
            
            return "\n".join(hasil) if hasil else "Tidak ada tugas terbaru."

    except Exception as e:
        return f"Terjadi kesalahan: {str(e)}"
    finally:
        if driver: driver.quit()

def tentukan_kategori_dan_matkul(perintah):
    p = perintah.lower()
    
    # 1. Deteksi Kode Matkul
    match = re.search(r'[a-z]{2}\d{4}|[a-z]{3}\d{3}', p)
    kode = match.group(0).upper() if match else None
    
    # 2. Logika Penentuan Kategori (Urutan penting!)
    if any(keyword in p for keyword in ["absen", "presensi", "alpha", "masuk", "hadir"]):
        kategori = "presensi"
    elif any(keyword in p for keyword in ["umum", "pengumuman", "info"]):
        kategori = "pengumuman"
    elif any(keyword in p for keyword in ["nilai", "skor", "grade", "nilai akhir"]):
        kategori = "nilai"
    elif any(keyword in p for keyword in ["materi", "slide", "pdf", "ppt", "excel", "word", "docx", "download"]):
        kategori = "materi"
    else:
        # Default tetap tugas, tapi hanya jika tidak ada keyword di atas
        kategori = "tugas"
    
    return kode, kategori

from bs4 import BeautifulSoup

def get_data_eclass(url, prompt):
    options = uc.ChromeOptions()
    current_dir = os.getcwd()
    bot_profile_path = os.path.join(current_dir, "profil_bot")
    options.add_argument(f"--user-data-dir={bot_profile_path}")
    options.add_argument("--window-position=-2000,0") 

    download_path = os.path.join(current_dir, "downloads")
    
    # Buat folder download jika belum ada
    if not os.path.exists(download_path):
        os.makedirs(download_path)

    # Setting agar otomatis download tanpa bertanya
    prefs = {
        "download.default_directory": download_path, # Folder tujuan
        "download.prompt_for_download": False,       # Jangan tanya lokasi
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True                 # Matikan proteksi yang menghambat
    }
    options.add_experimental_option("prefs", prefs)

    driver = None
    try:
        driver = uc.Chrome(options=options, version_main=145)
        driver.get(url)
        time.sleep(7) 

        # --- LOGIKA AUTO-LOGIN ---
        # Memastikan submit ditekan jika profil belum otomatis masuk
        if "login" in driver.current_url.lower() or len(driver.find_elements(uc.By.NAME, "id")) > 0:
            try:
                submit_button = driver.find_element(uc.By.CSS_SELECTOR, "input[type='submit']")
                submit_button.click()
                time.sleep(5)
                if driver.current_url != url: driver.get(url)
            except: pass

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # --- CABANG 1: LOGIKA PRESENSI ---
        if "presensi" in url:
            # 1. LOGIKA KLIK HADIR (Aksi)
            target_aksi = prompt.lower()
            if any(k in target_aksi for k in ["absenkan", "presensikan"]):
                try:
                    # Mencari tombol dengan attribute name='presensi_hadir'
                    tombol_hadir = driver.find_elements(By.NAME, "presensi_hadir")
                    
                    if tombol_hadir:
                        tombol_hadir[0].click()
                        time.sleep(5) # Tunggu proses submit selesai
                        return "Sistem telah menekan tombol HADIR. Silakan cek status kehadiranmu."
                    else:
                        # Jika tombol tidak ada, mungkin belum waktunya absen atau sudah absen
                        return "Mungkin waktu presensi sudah berakhir/belum dimulai."
                except Exception as e:
                    return f"Gagal melakukan presensi otomatis: {e}"
            
            # 2. LOGIKA TAMPILKAN DATA (Informasi)
            presensi_results = []
            # Mencari tabel dengan class 'data' sesuai struktur HTML yang kamu berikan
            table = soup.find('table', class_='data')
            if not table:
                return "Tabel presensi tidak ditemukan di halaman ini."
                
            rows = table.find_all('tr')[1:] # Skip header
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 5:
                    tanggal = cols[1].get_text(strip=True)
                    pertemuan = cols[2].get_text(strip=True)
                    
                    # Mencari status H (Biru) atau A (Merah) di kolom ke-5
                    status_cell = cols[4]
                    font_tag = status_cell.find('font')
                    status_bold = font_tag.find('b') if font_tag else None
                    status_code = status_bold.get_text(strip=True) if status_bold else "?"
                    status_hadir = 0
                    status_alpha = 0
                    
                    if status_code == "H":
                        status = "HADIR"
                        status_hadir += 1
                    elif status_code == "A":
                        status = "ALPHA"
                        status_alpha += 1
                    else:
                        status = f"Status: {status_code}"
                        
                    presensi_results.append(f"Pertemuan {pertemuan} ({tanggal}): {status}")
            
            return "\n".join(presensi_results) if presensi_results else "Data presensi kosong."

        # --- CABANG 2: LOGIKA TUGAS (Deep Scraping) ---
        elif "tugas" in url:
            # Cari tabel utama
            table_utama = soup.find('table', class_='data')
            if not table_utama:
                return "Tabel daftar tugas tidak ditemukan."

            rows = table_utama.find_all('tr')[1:] # Skip header (No, Judul, dll)
            hasil_tugas = []

            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 5:
                    # Ambil Judul (Kolom ke-2 / Index 1)
                    judul_tugas = cols[1].get_text(strip=True).replace('\xa0', ' ')
                    
                    # Ambil Link Detail (Kolom ke-5 / Index 4)
                    link_tag = cols[4].find('a', href=True)
                    if not link_tag: continue
                    
                    link_detail = link_tag['href']

                    # --- MASUK KE HALAMAN DETAIL ---
                    driver.get(link_detail)
                    time.sleep(2)
                    soup_detail = BeautifulSoup(driver.page_source, 'html.parser')
                    seluruh_teks_detail = soup_detail.get_text().lower()

                    # Cek Softcopy (Cari di tabel isithread di halaman detail)
                    is_dikumpul_softcopy = False
                    rows_thread = soup_detail.find_all('tr', class_='isithread')
                    for r_thread in rows_thread:
                        if "jawaban anda:" in r_thread.get_text().lower():
                            is_dikumpul_softcopy = True
                            break
                    
                    # Cek instruksi Hardcopy (Cari di teks detail)
                    is_hardcopy = "hardcopy" in seluruh_teks_detail or "hard copy" in seluruh_teks_detail
                    
                    # Penentuan Status
                    if is_dikumpul_softcopy:
                        status = "SUDAH DIKUMPUL (Softcopy)"
                    elif is_hardcopy:
                        status = "SELESAI (Metode Hardcopy)"
                    else:
                        status = "BELUM DIKUMPUL"
                    
                    hasil_tugas.append(f"- {judul_tugas}: {status}")

            return "\n".join(hasil_tugas) if hasil_tugas else "Tidak ada daftar tugas ditemukan."
        
        # --- CABANG 3: LOGIKA PENGUMUMAN ---
        elif "pengumuman" in url:
            pengumuman_results = []
            table_pengumuman = soup.find('table', class_='diskusi')
            
            if not table_pengumuman:
                return "Tabel pengumuman tidak ditemukan."

            # Ambil semua baris judul (class thread)
            threads = table_pengumuman.find_all('tr', class_='thread')
            
            for thread in threads:
                # 1. Ambil Judul
                # Kita ambil teks sebelum tag span agar bersih
                judul_full = thread.find('td').get_text(strip=True)
                tgl_text = thread.find('span', class_='tgl').get_text(strip=True) if thread.find('span', class_='tgl') else ""
                judul_bersih = judul_full.replace(tgl_text, "").strip()
                
                # 2. Ambil Isi (Baris selanjutnya dengan class isithread)
                # Kita cari tag <tr> berikutnya yang punya id dimulai dengan 'isi'
                isi_id = thread.get('id').replace('th', 'isi')
                isi_row = table_pengumuman.find('tr', id=isi_id)
                
                isi_text = "Isi tidak ditemukan."
                if isi_row:
                    # Ambil teks di dalam <td> yang punya padding 40px
                    isi_cell = isi_row.find('td')
                    if isi_cell:
                        # Membersihkan teks dari whitespace berlebih
                        isi_text = " ".join(isi_cell.get_text(separator=" ", strip=True).split())

                pengumuman_results.append(f"JUDUL: {judul_bersih}\nTANGGAL: {tgl_text}\nISI: {isi_text}\n---")

            return "\n".join(pengumuman_results) if pengumuman_results else "Tidak ada pengumuman."
        
        # --- CABANG 4: LOGIKA NILAI ---
        elif "nilai" in url:
            nilai_results = []
            # Ambil semua tabel dengan class 'data'
            all_tables = soup.find_all('table', class_='data')
            
            # Validasi: Pastikan ada minimal 2 tabel sesuai struktur yang kamu berikan
            if len(all_tables) < 2:
                # Jika cuma ada 1 tabel, mungkin dosen belum setting standar nilai
                if len(all_tables) == 1:
                    target_table = all_tables[0]
                else:
                    return "Tabel nilai tidak ditemukan."
            else:
                # Targetkan tabel kedua karena tabel pertama adalah 'Standar Nilai'
                target_table = all_tables[1]

            rows = target_table.find_all('tr')
            
            # 1. Ambil data baris tugas (Skip header) sampai sebelum 3 baris terakhir (Total, Sementara, Maks)
            data_rows = rows[1:-3]
            
            for row in data_rows:
                cols = row.find_all('td')
                if len(cols) >= 3:
                    nama_item = cols[0].get_text(strip=True)
                    bobot = cols[1].get_text(strip=True)
                    skor = cols[2].get_text(strip=True)
                    nilai_results.append(f"DATA_NILAI >> {nama_item} ({bobot}): {skor}")

            # 2. Ambil 2 baris ringkasan paling bawah (Nilai Sementara & Capaian Maksimal)
            row_end = rows[-2:]
            if len(row_end) >= 2:
                # Baris Nilai Sementara
                cols_smt = row_end[0].find_all('td')
                if len(cols_smt) >= 4:
                    n_angka = cols_smt[2].get_text(strip=True)
                    n_huruf = cols_smt[3].get_text(strip=True).replace("Huruf:", "").strip()
                    nilai_results.append(f"\nRINGKASAN >> Nilai Sementara: {n_angka} | {n_huruf}")
                
                # Baris Capaian Maksimal
                cols_maks = row_end[1].find_all('td')
                if len(cols_maks) >= 4:
                    m_angka = cols_maks[2].get_text(strip=True)
                    m_huruf = cols_maks[3].get_text(strip=True).replace("Huruf:", "").strip()
                    nilai_results.append(f"RINGKASAN >> Capaian Maksimal: {m_angka} | {m_huruf}")

            return "\n".join(nilai_results)

        # --- CABANG 5: LOGIKA MATERI ---
        elif "materi" in url:
            materi_results = []
            tables = soup.find_all('table', class_='data')
            
            if len(tables) < 2:
                return "Hanya ditemukan tabel RPS. Tabel materi utama belum tersedia."
            
            table_materi = tables[1]
            rows = table_materi.find_all('tr')[1:] 
            
            # List untuk menyimpan info lengkap guna keperluan download nanti
            daftar_download = []

            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 4:
                    nomor = cols[0].get_text(strip=True)
                    judul_tag = cols[1].find('b')
                    judul = judul_tag.get_text(strip=True) if judul_tag else cols[1].get_text(strip=True)
                    
                    link_tag = cols[3].find('a', href=True)
                    url_download = link_tag['href'] if link_tag else None
                    
                    materi_results.append(f"{nomor}. {judul}")
                    
                    # Simpan data ke list bantuan
                    daftar_download.append({
                        "nomor": nomor,
                        "judul": judul.lower(),
                        "href": url_download
                    })

            # LOGIKA DOWNLOAD: Cek apakah user ingin mendownload materi spesifik
            target_download = prompt.lower() 
            if "download" in target_download:
                # Ambil semua angka dari prompt user menggunakan regex
                angka_di_prompt = re.findall(r'\d+', target_download) 

                for item in daftar_download:
                    # Cek 1: Apakah nomor materi (misal '7') ada sebagai angka utuh di prompt?
                    is_nomor_match = item["nomor"] in angka_di_prompt
                    
                    # Cek 2: Apakah judul materi disebutkan?
                    is_judul_match = item["judul"] in target_download and len(item["judul"]) > 5
                    
                    if is_nomor_match or is_judul_match:
                        if item["href"]:
                            try:
                                # Pastikan scroll ke elemen agar terlihat oleh driver sebelum klik
                                element_klik = driver.find_element(By.CSS_SELECTOR, f'a[href="{item["href"]}"]')
                                driver.execute_script("arguments[0].scrollIntoView();", element_klik)
                                time.sleep(1)
                                
                                element_klik.click()
                                time.sleep(10) # Beri nafas untuk download
                                return f"Berhasil! Mengunduh Materi {item['nomor']}: {item['judul']}"
                            except Exception as e:
                                return f"Gagal klik: {e}"

                        return "\n".join(materi_results) if materi_results else "Data materi kosong."

    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        if driver: driver.quit()

def main():
    print("=== ASISTEN ECLASS UKDW ===")
    
    while True:
        print("\n[ MENU UTAMA ]")
        print("1. Melihat Daftar Kelas")
        print("2. Melihat Daftar Pengumuman Terbaru")
        print("3. Melihat Daftar Tugas Terbaru")
        print("4. Exit")
        
        try:
            opsi = int(input("\nSilahkan pilih opsi aksi (1-4): "))
        except ValueError:
            print("[!] Masukkan angka 1 sampai 4.")
            continue

        if opsi == 4: 
            print("Sampai jumpa!")
            break

        # --- LOGIKA DASHBOARD (OPSI 1, 2, 3) ---
        print(f"[*] Menghubungkan ke dashboard e-class...")
        data_awal = get_dashboard_data(opsi)
        
        print("\n" + "="*30)
        print(data_awal)
        print("="*30)

        # Setelah menampilkan data awal, berikan kesempatan user untuk bertanya detail
        # Contoh: "cek nilai TI0323" atau "download materi 7 TI9233"
        print("\nTips: Ketik perintah detail (contoh: 'cek nilai TI0323') atau 'kembali'")
        perintah = input("Perintah: ")

        if perintah.lower() in ['kembali', 'exit', 'back']:
            continue
        
        # --- LOGIKA DETAIL (ROUTING KE GEMINI) ---
        kode_matkul, kategori = tentukan_kategori_dan_matkul(perintah)
        
        if not kode_matkul:
            print("[!] Perintah tidak spesifik. Mohon sertakan kode matkul (contoh: TI0323)")
            continue

        # Mapping URL berdasarkan kategori
        if kategori == "materi":
            target_url = f"https://eclass.ukdw.ac.id/e-class/id/materi/index/{kode_matkul}"
        else:
            target_url = f"https://eclass.ukdw.ac.id/e-class/id/kelas/{kategori}/{kode_matkul}"

        print(f"[*] Mengambil detail {kategori} {kode_matkul}...")
        raw_data = get_data_eclass(target_url, perintah)

        # Proses dengan Gemini
        try:
            # Prompt yang lebih adaptif terhadap kategori
            prompt = f"""
            User bertanya: '{perintah}'
            Kategori terdeteksi: {kategori}
            Data mentah dari Eclass:
            {raw_data}

            Tugasmu:
            1. Analisis data sesuai kategori.
            2. Jika kategori PRESENSI: 
               - Jika user minta 'presensikan', maka lakukan aksi presensi otomatis. 
               - Jika tidak, maka tampilkan persentase kehadiran dan peringatan jika ada Alpha.
            3. Jika kategori TUGAS: List status pengumpulan tugas beserta nama tugasnya (beri notes untuk jenis tugas hardcopy).
            4. Jika kategori PENGUMUMAN:
               - Jika user minta 'cek pengumuman', tampilkan judul-judulnya saja berupa list.
               - Jika user bertanya tentang isi pengumuman tertentu, berikan isi lengkap pengumuman yang relevan.
            5. Jika kategori NILAI: Tampilkan list nilai beserta bobotnya, dan tampilkan juga "Nilai Sementara" dan "Capaian Maksimal".
            6. Jika kategori MATERI: 
               - Jika user minta 'download', maka download materi yang relevan.
               - Jika tidak, maka tampilkan list nomor, nama materi, dan jenis file-nya (docx,pdf,dsb).
            7. Berikan jawaban yang ringkas dan informatif.
            """
            response = model.generate_content(prompt)
            print("\n[Gemini]:", response.text)

        except Exception as e:
            if "429" in str(e):
                print("\n[!] Kuota Gemini habis. Coba lagi nanti.")
            else:
                print(f"\n[Error Gemini]: {e}")

if __name__ == "__main__":
    # print("--- Daftar Model Tersedia ---")
    # for m in genai.list_models():
    #     if 'generateContent' in m.supported_generation_methods:
    #         print(m.name)
    # print("-----------------------------")
    main()