from fastapi import FastAPI
import eclass_bot  # Mengimpor file aslimu

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Server E-Class Ivan Aktif!"}

@app.get("/menu/{opsi}")
def get_menu(opsi: int):
    # Menjalankan fungsi scraping dari eclass_bot.py
    data = eclass_bot.get_dashboard_data(opsi)
    return {"status": "success", "data": data}

@app.get("/detail")
def get_detail(perintah: str):
    # Logika penentuan kategori
    kode_matkul, kategori = eclass_bot.tentukan_kategori_dan_matkul(perintah)
    
    if not kode_matkul:
        return {"status": "error", "message": "Kode matkul tidak ditemukan"}

    target_url = f"https://eclass.ukdw.ac.id/e-class/id/kelas/{kategori}/{kode_matkul}"
    raw_data = eclass_bot.get_data_eclass(target_url, perintah)
    
    # Kamu bisa memanggil Gemini di sini sebelum mengirim jawaban ke HP
    # Atau kirim data mentah agar HP yang memprosesnya
    return {
        "matkul": kode_matkul,
        "kategori": kategori,
        "raw_content": raw_data
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)