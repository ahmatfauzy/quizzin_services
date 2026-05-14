## Installation

1. Buat virtual environment dan aktifkan

Linux: 
```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows: 
```bash
python -m venv .venv
.venv\Scripts\activate
```
 
2. Install dependencies

```bash
pip install -r requirement.txt
```

3. Salin `.env.example` ke `.env` dan sesuaikan isinya

```bash
cp .env.example .env
```

4. Jalankan server

```bash
fastapi dev
```

Server akan berjalan di `http://127.0.0.1:8000`

Halaman documentasi bisa diakses di `http://127.0.0.1:8000/docs`
