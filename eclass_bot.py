import undetected_chromedriver as uc
import google.generativeai as genai
import time
import os
import re
from bs4 import BeautifulSoup
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
    
    # --- FIX ANTI-STUCK ---
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-gpu")
    
    url_index = "https://eclass.ukdw.ac.id/e-class/id/kelas/index"
    driver = None
    try:
        driver = uc.Chrome(options=options, version_main=145)
        # Tambahan agar driver tidak menggantung jika page load lambat
        driver.set_page_load_timeout(30)
        driver.get(url_index)
        
        # Memaksa fokus ke window agar tidak stuck di background
        driver.switch_to.window(driver.window_handles[0])
        
        time.sleep(5)

        # --- LOGIKA AUTO-LOGIN ---
        if "login" in driver.current_url.lower() or len(driver.find_elements(By.NAME, "id")) > 0:
            try:
                submit_button = driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
                submit_button.click()
                time.sleep(5)
                if driver.current_url != url_index: driver.get(url_index)
            except: pass

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        if opsi == 1:
            container = soup.find('div', id='content-right')
            if not container: return "Konten kelas tidak ditemukan."
            kelas_boxes = container.find_all('div', class_='kelas_box')
            hasil = ["[" + " ".join(box.find('h2').get_text().split()) + "]" for box in kelas_boxes]
            return "\n".join(hasil) if hasil else "Tidak ada kelas terdaftar."

        elif opsi == 2:
            container = soup.find('div', id='content-left')
            links = container.find_all('a', class_='menu mc')
            hasil = []
            for link in links:
                if 'pengumuman/baca' in link.get('href', ''):
                    parts = [p.strip() for p in link.get_text(separator="|").split('|') if p.strip()]
                    tgl = parts[0] if len(parts) > 0 else "No Date"
                    title = link.get('title', 'No Title')
                    isi = next((p.replace('>', '') for p in parts if '>' in p), "Tidak ada detail")
                    hasil.append(f"📣 [{tgl}] {title} - {isi}")
            return "\n".join(hasil) if hasil else "Tidak ada pengumuman."

        elif opsi == 3:
            container = soup.find('div', id='content-left')
            if not container: return "Konten tugas tidak ditemukan."
            links = container.find_all('a', class_='menu mc')
            hasil = []
            for link in links:
                if 'detail_tugas' in link.get('href', ''):
                    raw_parts = link.get_text(separator="|", strip=True).split('|')
                    deadline = raw_parts[0] if raw_parts else "-"
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
    match = re.search(r'[a-z]{2}\d{4}|[a-z]{3}\d{3}', p)
    kode = match.group(0).upper() if match else None
    
    if any(keyword in p for keyword in ["absen", "presensi", "alpha", "masuk", "hadir"]):
        kategori = "presensi"
    elif any(keyword in p for keyword in ["umum", "pengumuman", "info"]):
        kategori = "pengumuman"
    elif any(keyword in p for keyword in ["nilai", "skor", "grade", "nilai akhir"]):
        kategori = "nilai"
    elif any(keyword in p for keyword in ["materi", "slide", "pdf", "ppt", "excel", "word", "docx", "download"]):
        kategori = "materi"
    else:
        kategori = "tugas"
    return kode, kategori

def get_data_eclass(url, prompt):
    options = uc.ChromeOptions()
    current_dir = os.getcwd()
    bot_profile_path = os.path.join(current_dir, "profil_bot")
    options.add_argument(f"--user-data-dir={bot_profile_path}")
    options.add_argument("--window-position=-2000,0") 

    # --- FIX ANTI-STUCK ---
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-gpu")

    download_path = os.path.join(current_dir, "downloads")
    if not os.path.exists(download_path): os.makedirs(download_path)

    prefs = {
        "download.default_directory": download_path,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True 
    }
    options.add_experimental_option("prefs", prefs)

    driver = None
    try:
        driver = uc.Chrome(options=options, version_main=145)
        driver.set_page_load_timeout(30)
        driver.get(url)
        driver.switch_to.window(driver.window_handles[0])
        time.sleep(7) 

        if "login" in driver.current_url.lower() or len(driver.find_elements(By.NAME, "id")) > 0:
            try:
                submit_button = driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
                submit_button.click()
                time.sleep(5)
                if driver.current_url != url: driver.get(url)
            except: pass

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        if "presensi" in url:
            target_aksi = prompt.lower()
            if any(k in target_aksi for k in ["absenkan", "presensikan"]):
                try:
                    tombol_hadir = driver.find_elements(By.NAME, "presensi_hadir")
                    if tombol_hadir:
                        tombol_hadir[0].click()
                        time.sleep(5)
                        return "Sistem telah menekan tombol HADIR. Silakan cek status kehadiranmu."
                    else:
                        return "Mungkin waktu presensi sudah berakhir/belum dimulai."
                except Exception as e:
                    return f"Gagal melakukan presensi otomatis: {e}"
            
            presensi_results = []
            table = soup.find('table', class_='data')
            if not table: return "Tabel presensi tidak ditemukan."
            rows = table.find_all('tr')[1:]
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 5:
                    tanggal = cols[1].get_text(strip=True)
                    pertemuan = cols[2].get_text(strip=True)
                    status_cell = cols[4]
                    font_tag = status_cell.find('font')
                    status_bold = font_tag.find('b') if font_tag else None
                    status_code = status_bold.get_text(strip=True) if status_bold else "?"
                    status = "HADIR" if status_code == "H" else ("ALPHA" if status_code == "A" else f"Status: {status_code}")
                    presensi_results.append(f"Pertemuan {pertemuan} ({tanggal}): {status}")
            return "\n".join(presensi_results)

        elif "tugas" in url:
            table_utama = soup.find('table', class_='data')
            if not table_utama: return "Tabel daftar tugas tidak ditemukan."
            rows = table_utama.find_all('tr')[1:]
            hasil_tugas = []
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 5:
                    judul_tugas = cols[1].get_text(strip=True).replace('\xa0', ' ')
                    link_tag = cols[4].find('a', href=True)
                    if not link_tag: continue
                    driver.get(link_tag['href'])
                    time.sleep(2)
                    soup_detail = BeautifulSoup(driver.page_source, 'html.parser')
                    isithread_text = "".join([r.get_text().lower() for r in soup_detail.find_all('tr', class_='isithread')])
                    is_softcopy = "jawaban anda:" in isithread_text
                    is_hardcopy = "hardcopy" in soup_detail.get_text().lower() or "hard copy" in soup_detail.get_text().lower()
                    status = "SUDAH DIKUMPUL (Softcopy)" if is_softcopy else ("SELESAI (Metode Hardcopy)" if is_hardcopy else "BELUM DIKUMPUL")
                    hasil_tugas.append(f"- {judul_tugas}: {status}")
            return "\n".join(hasil_tugas)
        
        elif "pengumuman" in url:
            pengumuman_results = []
            table_pengumuman = soup.find('table', class_='diskusi')
            if not table_pengumuman: return "Tabel pengumuman tidak ditemukan."
            threads = table_pengumuman.find_all('tr', class_='thread')
            for thread in threads:
                judul_full = thread.find('td').get_text(strip=True)
                tgl_text = thread.find('span', class_='tgl').get_text(strip=True) if thread.find('span', class_='tgl') else ""
                judul_bersih = judul_full.replace(tgl_text, "").strip()
                isi_id = thread.get('id').replace('th', 'isi')
                isi_row = table_pengumuman.find('tr', id=isi_id)
                isi_text = " ".join(isi_row.find('td').get_text(separator=" ", strip=True).split()) if isi_row else "Isi tidak ditemukan."
                pengumuman_results.append(f"JUDUL: {judul_bersih}\nTANGGAL: {tgl_text}\nISI: {isi_text}\n---")
            return "\n".join(pengumuman_results)
        
        elif "nilai" in url:
            nilai_results = []
            all_tables = soup.find_all('table', class_='data')
            if not all_tables: return "Tabel nilai tidak ditemukan."
            target_table = all_tables[1] if len(all_tables) > 1 else all_tables[0]
            rows = target_table.find_all('tr')
            for row in rows[1:-3]:
                cols = row.find_all('td')
                if len(cols) >= 3:
                    nilai_results.append(f"DATA_NILAI >> {cols[0].get_text(strip=True)} ({cols[1].get_text(strip=True)}): {cols[2].get_text(strip=True)}")
            for row in rows[-2:]:
                cols = row.find_all('td')
                if len(cols) >= 4:
                    label = "Nilai Sementara" if "Sementara" in row.get_text() else "Capaian Maksimal"
                    nilai_results.append(f"{label}: {cols[2].get_text(strip=True)} | {cols[3].get_text(strip=True).replace('Huruf:', '').strip()}")
            return "\n".join(nilai_results)

        elif "materi" in url:
            tables = soup.find_all('table', class_='data')
            if len(tables) < 2: return "Tabel materi belum tersedia."
            rows = tables[1].find_all('tr')[1:] 
            daftar_download = []
            materi_results = []
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 4:
                    nomor = cols[0].get_text(strip=True)
                    judul = cols[1].find('b').get_text(strip=True) if cols[1].find('b') else cols[1].get_text(strip=True)
                    url_download = cols[3].find('a', href=True)['href'] if cols[3].find('a', href=True) else None
                    materi_results.append(f"{nomor}. {judul}")
                    daftar_download.append({"nomor": nomor, "judul": judul.lower(), "href": url_download})

            target_download = prompt.lower() 
            if "download" in target_download:
                angka_di_prompt = re.findall(r'\d+', target_download) 
                for item in daftar_download:
                    if item["nomor"] in angka_di_prompt or (item["judul"] in target_download and len(item["judul"]) > 5):
                        if item["href"]:
                            element_klik = driver.find_element(By.CSS_SELECTOR, f'a[href="{item["href"]}"]')
                            driver.execute_script("arguments[0].scrollIntoView();", element_klik)
                            time.sleep(1); element_klik.click(); time.sleep(10)
                            return f"Berhasil mengunduh Materi {item['nomor']}: {item['judul']}"
            return "\n".join(materi_results)

    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        if driver: driver.quit()

def main():
    print("=== ASISTEN ECLASS UKDW ===")
    while True:
        print("\n[ MENU UTAMA ]\n1. Melihat Daftar Kelas\n2. Melihat Daftar Pengumuman Terbaru\n3. Melihat Daftar Tugas Terbaru\n4. Exit")
        try:
            opsi = int(input("\nSilahkan pilih opsi aksi (1-4): "))
        except ValueError:
            print("[!] Masukkan angka 1 sampai 4."); continue

        if opsi == 4: break

        print(f"[*] Menghubungkan ke dashboard e-class...")
        data_awal = get_dashboard_data(opsi)
        print("\n" + "="*30 + "\n" + data_awal + "\n" + "="*30)

        while True:
            print("\nTips: Ketik perintah detail (contoh: 'cek nilai TI0323') atau ketik 'menu' untuk kembali.")
            perintah = input("Perintah: ")
            
            if perintah.lower() in ['menu', 'kembali', 'back']:
                break # Keluar dari loop detail dan kembali ke Menu Utama
            
            if perintah.lower() in ['exit', 'keluar']:
                print("Sampai jumpa!")
                return # Menutup seluruh program

            kode_matkul, kategori = tentukan_kategori_dan_matkul(perintah)
            if not kode_matkul:
                print("[!] Perintah tidak spesifik. Mohon sertakan kode matkul (contoh: TI0323)")
                continue

            target_url = f"https://eclass.ukdw.ac.id/e-class/id/materi/index/{kode_matkul}" if kategori == "materi" \
                         else f"https://eclass.ukdw.ac.id/e-class/id/kelas/{kategori}/{kode_matkul}"

            print(f"[*] Mengambil detail {kategori} {kode_matkul}...")
            raw_data = get_data_eclass(target_url, perintah)

            try:
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
                print(f"\n[Error Gemini]: {e}")

if __name__ == "__main__":
    main()