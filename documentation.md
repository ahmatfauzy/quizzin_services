# Dokumentasi Proyek — Quizzin Backend

> **Target SDG:** SDG 4 — Pendidikan Bermutu

---

## 1. Pengenalan Aplikasi

**Quizzin** adalah platform edukasi cerdas berbasis AI (*Smart Tutor*) yang memungkinkan siswa mengunggah dokumen PDF/e-book. Sistem secara otomatis melakukan:

1. **Ekstraksi konten** per chapter menggunakan PyMuPDF
2. **Generasi ringkasan & knowledge graph** per chapter menggunakan Groq AI (LLM)
3. **Generasi kuis otomatis** berdasarkan materi dengan tiga tingkat kesulitan (*easy, medium, hots*)
4. **Evaluasi semantik** jawaban esai menggunakan AI (bukan sekadar exact-match)
5. **Analitik pembelajaran** adaptif: mastery tracking, XP, streak, recommended focus areas

Backend dibangun sebagai **REST API** (format JSON) yang dikonsumsi oleh aplikasi mobile Flutter.

---

## 2. Tech Stack

| Komponen | Teknologi |
|---|---|
| **Framework Backend** | FastAPI |
| **Database** | PostgreSQL |
| **ORM** | SQLAlchemy |
| **Migration** | Alembic |
| **Authentication** | JWT (pyjwt) + itsdangerous |
| **Email Service** | Resend (SMTP) |
| **File Storage** | Cloudinary |
| **PDF Parsing** | PyMuPDF (fitz) |
| **NLP / AI** | Groq API (LLM) |
| **Password Hashing** | passlib (bcrypt) |

### 2.1 Alasan Pemilihan FastAPI

| Faktor | Penjelasan |
|---|---|
| **Async Native** | FastAPI dibangun di atas Starlette dan mendukung `async/await` secara native. Ini krusial untuk operasi I/O seperti upload file, panggilan ke Groq API, dan pengiriman email — semuanya berjalan non-blocking tanpa mengorbankan thread pool. |
| **Auto-dokumentasi** | FastAPI otomatis menghasilkan OpenAPI/Swagger UI (`/docs`) dari type hints dan Pydantic schema. Ini mempercepat development, testing, dan kolaborasi tim. |
| **Validasi Otomatis** | Setiap request/response tervalidasi otomatis oleh Pydantic, mencegah data invalid masuk ke database tanpa perlu boilerplate validasi manual. |
| **Background Tasks** | Fitur `BackgroundTasks` bawaan memungkinkan operasi berat (seperti pemrosesan PDF + panggilan Groq untuk summarization & knowledge graph) dijalankan setelah response dikirim ke client, tanpa perlu message queue tambahan seperti Celery atau Redis. |
| **Dependency Injection** | FastAPI punya sistem DI yang powerful dan eksplisit untuk inject database session, current user, dan shared service ke setiap endpoint — menghasilkan kode yang clean, testable, dan modular. |
| **Ekosistem Python** | Integrasi langsung dengan pustaka AI/NLP Python (Groq SDK, PyMuPDF), ekosistem data science, dan tooling Python standar — tidak perlu polyfill atau wrapper tambahan. |
| **Performa** | FastAPI adalah salah satu framework Python tercepat (setara dengan NodeJS/Go untuk I/O-bound workloads), cocok untuk API yang melayani mobile app dengan banyak concurrent request. |

### 2.2 Alasan Pemilihan PostgreSQL

| Faktor | Penjelasan |
|---|---|
| **JSONB Support** | PostgreSQL mendukung tipe data `JSONB` yang memungkinkan penyimpanan data semi-terstruktur (knowledge graph, opsi kuis, jawaban user, reference facts) dengan indexing dan query yang efisien — sangat cocok untuk aplikasi berbasis AI yang output-nya dinamis. |
| **ACID Compliance** | Transaksi atomik memastikan konsistensi data saat operasi kompleks seperti: generate kuis → simpan questions → simpan attempt → update mastery → update XP, semuanya dalam satu transaksi yang konsisten. |
| **Enum Types** | Tipe `ENUM` native untuk status dokumen (`processing`, `ready`, `failed`), tipe kuis (`easy`, `medium`, `hots`), dan tipe pertanyaan (`multiple_choice`, `essay`, `short_answer`) — mencegah invalid state di level database. |
| **Relational Integrity** | Foreign key constraints dengan `ON DELETE CASCADE` memastikan integritas relasi antar tabel (user → documents → chapters → questions → quiz_attempts) tanpa orphan data. |
| **Scalability** | PostgreSQL mendukung koneksi concurrent tinggi, full-text search, dan extension — siap untuk skala produksi dengan ribuan user dan dokumen. |
| **Hosting Ready** | Didukung oleh semua cloud provider (Neon, Supabase, AWS RDS, Railway) dengan free tier yang cukup untuk development dan testing. |

---

## 3. Struktur Proyek

```
quizzin_be/
├── config/settings.py              # Pydantic Settings (load .env)
├── database/database.py            # SQLAlchemy engine & session
├── migration/                      # Alembic migrations
│   ├── env.py
│   └── versions/
├── models/                         # SQLAlchemy ORM models
│   ├── user.py                     # User + profile + XP/streak
│   ├── document.py                 # Document upload & processing status
│   ├── chapter.py                  # Extracted chapters with AI summaries
│   ├── question.py                 # Generated quiz questions
│   ├── quiz_attempt.py             # User quiz attempts & scores
│   ├── chapter_mastery.py          # Per-user per-chapter mastery tracking
│   └── notification.py             # In-app notifications
├── routes/                         # API route handlers (8 modules)
│   ├── auth.py                     # Register, login, email verification, password reset
│   ├── profile.py                  # User profile, avatar, change password
│   ├── dashboard.py                # Home dashboard with analytics
│   ├── document.py                 # PDF upload, list, detail, status polling, delete
│   ├── chapter.py                  # Chapter detail with knowledge graph
│   ├── quiz.py                     # Generate quiz, submit answers, history
│   ├── analytics.py                # Learning analytics, knowledge gap, performance
│   └── notifications.py            # Notification CRUD
├── schemas/                        # Pydantic request/response schemas (7 modules)
├── utils/                          # Service modules
│   ├── security.py                 # JWT, password hashing, itsdangerous tokens
│   ├── dependencies.py             # get_current_user, get_db
│   ├── email.py                    # Resend integration
│   ├── cloudinary_service.py       # Cloudinary upload (PDF & avatar)
│   ├── pdf_service.py              # PyMuPDF chapter extraction
│   ├── nlp_service.py              # Groq AI (summarize, knowledge graph, question gen, tutor)
│   ├── semantic.py                 # AI-based essay scoring
│   ├── adaptive.py                 # Adaptive difficulty, XP calculation, streak
│   └── logger.py                   # Activity logging
├── main.py                         # FastAPI entry point
├── passenger_wsgi.py               # WSGI adapter for cPanel Passenger
├── activity.log                    # User activity logs (auto-generated)
└── requirements.txt
```

---

## 4. Database Schema (ERD)

### 4.1 Tabel & Relasi

```
users (1) ──────< documents (N)
  │                  │
  │                  └──< chapters (N)
  │                        │
  │                        ├──< questions (N)
  │                        ├──< quiz_attempts (N)
  │                        └──< chapter_mastery (N)
  │
  ├──< quiz_attempts (N)
  ├──< chapter_mastery (N)
  └──< notifications (N)
```

### 4.2 Detail Tabel

#### `users` — Data pengguna
| Kolom | Tipe | Keterangan |
|---|---|---|
| `id` | INT PK | Primary key |
| `email` | VARCHAR UNIQUE | Email pengguna |
| `full_name` | VARCHAR | Nama lengkap |
| `avatar_url` | VARCHAR | URL foto profil (Cloudinary) |
| `hashed_password` | VARCHAR | Password ter-hash (bcrypt) |
| `academic_level` | VARCHAR | Jenjang pendidikan (e.g. "Graduate") |
| `major` | VARCHAR | Jurusan |
| `xp_points` | INT | Experience points |
| `streak_days` | INT | Hari berturut-turut aktif |
| `subjects_mastered` | INT | Jumlah subject dikuasai (mastery 100%) |
| `last_active_date` | DATE | Tanggal terakhir aktif |
| `is_verified` | BOOLEAN | Status verifikasi email |
| `is_active` | BOOLEAN | Status akun |
| `created_at` | TIMESTAMP | Waktu pendaftaran |
| `updated_at` | TIMESTAMP | Waktu update terakhir |

#### `documents` — Dokumen PDF yang diunggah
| Kolom | Tipe | Keterangan |
|---|---|---|
| `id` | INT PK | Primary key |
| `user_id` | INT FK → users | Pemilik dokumen |
| `title` | VARCHAR | Judul dokumen |
| `original_filename` | VARCHAR | Nama file asli |
| `cloudinary_url` | VARCHAR | URL file di Cloudinary |
| `cloudinary_public_id` | VARCHAR | Public ID untuk delete |
| `total_pages` | INT | Jumlah halaman PDF |
| `status` | ENUM | `processing`, `ready`, `failed` |
| `created_at` | TIMESTAMP | Waktu upload |

#### `chapters` — Chapter hasil ekstraksi AI
| Kolom | Tipe | Keterangan |
|---|---|---|
| `id` | INT PK | Primary key |
| `document_id` | INT FK → documents | Dokumen induk |
| `chapter_number` | INT | Urutan chapter |
| `title` | VARCHAR | Judul (deteksi AI) |
| `raw_text` | TEXT | Teks mentah hasil PyMuPDF |
| `summary` | TEXT | Ringkasan hasil Groq AI |
| `knowledge_graph` | JSONB | Graph pengetahuan (core_concept, modules, entities, relations) |
| `page_start` | INT | Halaman awal |
| `page_end` | INT | Halaman akhir |
| `created_at` | TIMESTAMP | Waktu dibuat |

#### `questions` — Soal kuis hasil generasi AI
| Kolom | Tipe | Keterangan |
|---|---|---|
| `id` | INT PK | Primary key |
| `chapter_id` | INT FK → chapters | Chapter sumber |
| `subject_tag` | VARCHAR | Tag topik |
| `question_text` | TEXT | Kalimat pertanyaan |
| `question_description` | TEXT | Konteks tambahan |
| `hint` | TEXT | Hint (untuk MCQ) |
| `question_type` | ENUM | `multiple_choice`, `essay`, `short_answer` |
| `difficulty` | ENUM | `easy`, `medium`, `hots` |
| `options` | JSONB | `[{key, text}]` — pilihan MCQ |
| `correct_answer` | VARCHAR | Jawaban benar (key untuk MCQ, null untuk esai) |
| `reference_facts` | JSONB | Fakta kunci untuk scoring semantik |
| `created_at` | TIMESTAMP | Waktu dibuat |

#### `quiz_attempts` — Attempt kuis pengguna
| Kolom | Tipe | Keterangan |
|---|---|---|
| `id` | INT PK | Primary key |
| `user_id` | INT FK → users | Pengguna |
| `chapter_id` | INT FK → chapters | Chapter |
| `difficulty` | ENUM | Tingkat kesulitan |
| `total_score` | FLOAT | Skor total (0-100) |
| `xp_gained` | INT | XP yang didapat |
| `answers` | JSONB | `[{question_id, answer, score, is_correct, feedback, missing_concepts}]` |
| `time_taken_seconds` | INT | Waktu pengerjaan |
| `completed_at` | TIMESTAMP | Waktu selesai |

#### `chapter_mastery` — Mastery per user per chapter
| Kolom | Tipe | Keterangan |
|---|---|---|
| `id` | INT PK | Primary key |
| `user_id` | INT FK → users | Pengguna |
| `chapter_id` | INT FK → chapters | Chapter |
| `mastery_percentage` | FLOAT | Persentase penguasaan (0-100) |
| `updated_at` | TIMESTAMP | Waktu update terakhir |

#### `notifications` — Notifikasi in-app
| Kolom | Tipe | Keterangan |
|---|---|---|
| `id` | INT PK | Primary key |
| `user_id` | INT FK → users | Pengguna |
| `title` | VARCHAR | Judul notifikasi |
| `body` | VARCHAR | Isi notifikasi |
| `is_read` | BOOLEAN | Status baca |
| `created_at` | TIMESTAMP | Waktu dibuat |

---

## 5. API Endpoints (28 endpoint)

### 5.1 Authentication (`/auth`) — 7 endpoint

| Method | Endpoint | Deskripsi | Auth |
|---|---|---|---|
| `POST` | `/auth/register` | Registrasi akun baru; kirim email verifikasi via Resend | ✗ |
| `POST` | `/auth/login` | Login dengan email & password; return JWT access token | ✗ |
| `POST` | `/auth/verify-email` | Verifikasi email via token dari link email; auto-login | ✗ |
| `POST` | `/auth/resend-verification` | Kirim ulang email verifikasi | ✗ |
| `POST` | `/auth/forgot-password` | Kirim email reset password (selalu return 200) | ✗ |
| `POST` | `/auth/reset-password` | Reset password dengan token dari email | ✗ |
| `GET` | `/auth/me` | Profil pengguna yang sedang login | ✓ |

### 5.2 Profile (`/profile`) — 4 endpoint

| Method | Endpoint | Deskripsi | Auth |
|---|---|---|---|
| `GET` | `/profile` | Lihat profil lengkap (nama, jurusan, XP, streak, dll) | ✓ |
| `PUT` | `/profile` | Update full_name, academic_level, major | ✓ |
| `PUT` | `/profile/avatar` | Upload/update foto profil (max 5MB, JPEG/PNG) | ✓ |
| `PUT` | `/profile/change-password` | Ganti password (perlu password lama) | ✓ |

### 5.3 Dashboard (`/dashboard`) — 1 endpoint

| Method | Endpoint | Deskripsi | Auth |
|---|---|---|---|
| `GET` | `/dashboard` | Home screen: greeting, overall progress, weekly activity, recent documents, AI tutor suggestion | ✓ |

### 5.4 Documents (`/documents`) — 5 endpoint

| Method | Endpoint | Deskripsi | Auth |
|---|---|---|---|
| `POST` | `/documents/upload` | Upload PDF → Cloudinary → background processing (ekstraksi chapter + ringkasan AI) | ✓ |
| `GET` | `/documents/` | List semua dokumen milik user | ✓ |
| `GET` | `/documents/{id}` | Detail dokumen + daftar chapter (dengan mastery, lock status, action label) | ✓ |
| `GET` | `/documents/{id}/status` | Polling status pemrosesan dokumen | ✓ |
| `DELETE` | `/documents/{id}` | Hapus dokumen + file di Cloudinary | ✓ |

### 5.5 Chapters (`/chapters`) — 1 endpoint

| Method | Endpoint | Deskripsi | Auth |
|---|---|---|---|
| `GET` | `/chapters/{id}` | Detail chapter: summary (AI), knowledge graph (AI), mastery | ✓ |

### 5.6 Quizzes (`/quizzes`) — 4 endpoint

| Method | Endpoint | Deskripsi | Auth |
|---|---|---|---|
| `POST` | `/quizzes/generate` | Generate soal kuis per chapter per difficulty (AI) | ✓ |
| `POST` | `/quizzes/{id}/submit` | Submit jawaban; scoring MCQ + AI scoring esai; update XP & mastery | ✓ |
| `GET` | `/quizzes/history` | Riwayat kuis user | ✓ |
| `GET` | `/quizzes/attempt/{id}` | Detail satu attempt (skor per soal + feedback AI) | ✓ |

### 5.7 Analytics (`/analytics`) — 3 endpoint

| Method | Endpoint | Deskripsi | Auth |
|---|---|---|---|
| `GET` | `/analytics/learning` | Analitik lengkap: summary, AI readiness, recommended focus, incorrect answers | ✓ |
| `GET` | `/analytics/knowledge-gap?document_id=` | Gap pengetahuan per chapter dalam satu dokumen | ✓ |
| `GET` | `/analytics/performance?document_id=` | Performa: overall mastery, total attempts, XP | ✓ |

### 5.8 Notifications (`/notifications`) — 3 endpoint

| Method | Endpoint | Deskripsi | Auth |
|---|---|---|---|
| `GET` | `/notifications` | List notifikasi (maks 50) + unread count | ✓ |
| `PUT` | `/notifications/{id}/read` | Tandai satu notifikasi sebagai telah dibaca | ✓ |
| `PUT` | `/notifications/read-all` | Tandai semua notifikasi sebagai telah dibaca | ✓ |

---

## 6. Fitur Unggulan

### 6.1 AI-Powered PDF Processing Flow

```
POST /documents/upload (PDF)
  │
  ├─ Upload ke Cloudinary (resource_type="raw")
  ├─ Simpan record dengan status "processing"
  └─ Background Task:
       ├─ PyMuPDF: ekstrak teks per halaman + deteksi batas chapter
       ├─ Groq AI: generate ringkasan per chapter
       ├─ Groq AI: extract knowledge graph (core_concept, modules, entities, relations)
       └─ Set status = "ready"
```

### 6.2 AI-Powered Quiz Generation

```
POST /quizzes/generate { chapter_id, difficulty }
  │
  ├─ Groq AI: generate N soal (5 untuk easy, 10 untuk medium/hots)
  │   ├─ Multiple choice: 4 opsi (A/B/C/D) dengan hint
  │   ├─ Essay: pertanyaan + deskripsi konteks
  │   └─ Setiap soal punya reference_facts untuk scoring semantik
  ├─ Simpan questions ke DB
  └─ Return attempt_id + daftar soal (tanpa jawaban)
```

### 6.3 AI Semantic Scoring (Essay)

```
POST /quizzes/{id}/submit { answers }
  │
  ├─ MCQ: exact match (score 100 atau 0)
  ├─ Essay/Short Answer: Groq AI bandingkan jawaban vs reference_facts
  │   └─ Return: { score, missing_concepts, feedback }
  ├─ Update mastery per chapter (rata-rata progresif)
  ├─ Update XP points + streak days
  ├─ Suggest next difficulty (adaptive)
  └─ Return hasil lengkap dengan feedback per soal
```

### 6.4 Adaptive Learning System

| Komponen | Logic |
|---|---|
| **Difficulty Suggestion** | `easy` → avg < 60; `medium` → 60-79; `hots` → 80+ |
| **XP Calculation** | `base[difficulty] * (score / 100)` — easy=5, medium=10, hots=20 |
| **Streak** | +1 jika aktif hari berturut-turut, reset jika skip 1 hari |
| **Chapter Lock** | Chapter berikutnya terkunci sampai mastery chapter sebelumnya ≥ 60% |
| **Action Label** | `Review Concepts` (100%), `Continue Exploring` (>0%), `Explore Concepts` (0%) |

### 6.5 Knowledge Graph & Mind Map

Setiap chapter memiliki knowledge graph hasil ekstraksi AI:
- **Core Concept:** konsep utama chapter
- **Modules:** sub-topik dengan icon type (`trending_up`, `cycle`, `atom`, `function`, `book`, `diagram`)
- **Entities:** daftar konsep kunci
- **Relations:** relasi antar entitas beserta labelnya

Data ini digunakan oleh mobile Flutter untuk menampilkan **mind-map visual** per chapter.

---

## 7. Keamanan

| Aspek | Implementasi |
|---|---|
| **Password Hashing** | bcrypt via passlib — tidak menyimpan plain text |
| **JWT Auth** | Access token 24 jam, payload minimal (`sub` saja, tanpa email) |
| **Email Token** | itsdangerous URLSafeTimedSerializer dengan salt berbeda per flow |
| **Token Expiry** | Verifikasi email: 24 jam, Reset password: 24 jam |
| **Rate Limiting** | Groq API: text di-truncate ke 5000-6000 char untuk sesuai limit free tier |
| **File Validation** | PDF: `application/pdf` only, max 10MB. Avatar: image only, max 5MB |
| **Database** | Parameterized queries via SQLAlchemy ORM (anti SQL injection) |
| **CORS** | Tidak membatasi origin (untuk mobile app — request bukan dari browser) |
| **Production** | Swagger `/docs` auto-disable saat `APP_ENV=production` |

---

## 8. Dependencies

| Package | Kegunaan |
|---|---|
| `fastapi[standard]` | Core framework + Uvicorn server |
| `sqlalchemy`  | ORM (Object-Relational Mapping) |
| `alembic` | Database migration |
| `pydantic-settings` | Load environment variables |
| `pyjwt` | JWT encode/decode |
| `passlib[bcrypt]` | Password hashing |
| `itsdangerous` |  Email token signing |
| `cloudinary` |  Cloud file storage |
| `pymupdf` |  PDF text extraction |
| `python-multipart` |  File upload parsing |
| `resend` |  Transactional email |
| `groq` | AI/NLP API client |
| `email-validator` | Email format validation |
| `psycopg2-binary`| PostgreSQL driver |
| `requests` | Sync HTTP client |
| `a2wsgi` | WSGI adapter |

---

## 9. Kesimpulan

Quizzin API adalah REST API yang mengintegrasikan **FastAPI**, **PostgreSQL**, **Cloudinary**, dan **Groq AI (LLM)** untuk membangun platform Smart Tutor berbasis AI. Sistem mampu:

- Menerima upload PDF dan mengekstrak konten secara otomatis
- Menggunakan AI untuk meringkas materi dan membangun knowledge graph
- Men-generate kuis adaptif dengan tiga tingkat kesulitan
- Mengevaluasi jawaban esai secara semantik (bukan sekadar keyword matching)
- Melacak mastery, XP, dan streak pengguna untuk pembelajaran adaptif
- Menyajikan analitik pembelajaran yang komprehensif

Dengan **28 endpoint**, 7 tabel database, dan arsitektur modular, sistem ini siap dikonsumsi oleh aplikasi mobile Flutter dan dapat di-deploy ke production via cPanel shared hosting.
