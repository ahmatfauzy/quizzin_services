# Quizzin API Documentation

Dokumentasi ini berisi daftar endpoint API yang tersedia di Quizzin backend. Karena menggunakan FastAPI, kamu juga dapat melihat dokumentasi interaktif secara langsung dengan mengakses `/docs` (Swagger UI) atau `/redoc` pada browser ketika server berjalan.

---

## 1. General

### Health Check
Endpoint dasar untuk memastikan server berjalan dengan baik.

- **URL:** `/`
- **Method:** `GET`
- **Auth Required:** No

#### Success Response
- **Code:** `200 OK`
- **Content:**
  ```json
  {
    "message": "Welcome to Quizzin API"
  }
  ```

---

## 2. Authentication (Google OAuth)

### Google OAuth - Mobile Login
Endpoint ini digunakan oleh aplikasi Mobile (Flutter) setelah mendapatkan `id_token` dari SDK Google Sign-In di sisi client.

- **URL:** `/auth/google/mobile`
- **Method:** `POST`

#### Request Body
```json
{
  "token": "string"
}
```

#### Success Response (200 OK)
```json
{
  "access_token": "eyJhbG...",
  "token_type": "bearer",
  "user": {
    "email": "user@gmail.com",
    "full_name": "Nama User",
    "picture": "https://url-foto...",
    "id": 1,
    "is_active": true,
    "is_verified": true,
    "created_at": "2026-04-29T16:00:00.000",
    "updated_at": null
  }
}
```

---

### Google OAuth - Web Login
Endpoint ini digunakan oleh aplikasi Web (React/Next.js) menggunakan Implicit / Authorization Code Flow.

- **URL:** `/auth/google/web`
- **Method:** `POST`

#### Request Body
```json
{
  "token": "string (Optional)",
  "code": "string (Optional)"
}
```

---

## 3. Authentication (Credentials - Form Login)

### Register User Baru
Endpoint untuk mendaftarkan user baru dengan email dan password.

- **URL:** `/auth/register`
- **Method:** `POST`

#### Request Body
```json
{
  "full_name": "John Doe",
  "email": "johndoe@example.com",
  "password": "strongpassword123"
}
```

#### Success Response (200 OK)
```json
{
  "message": "User registered successfully. Please verify your email.",
  "verification_token": "eyJhbG... (hanya untuk testing)"
}
```

#### Error Response (400 Bad Request)
```json
{
  "detail": "Email already registered"
}
```

---

### Login Email & Password
Endpoint untuk login bagi pengguna yang sudah mendaftar menggunakan email & password dan telah memverifikasi emailnya.

- **URL:** `/auth/login`
- **Method:** `POST`

#### Request Body
```json
{
  "email": "johndoe@example.com",
  "password": "strongpassword123"
}
```

#### Success Response (200 OK)
Sama seperti Google Login, mengembalikan `access_token` dan data `user`.

#### Error Response
- **401 Unauthorized:** Invalid email or password
- **403 Forbidden:** Please verify your email first

---

### Resend Email Verification
Endpoint untuk meminta ulang token verifikasi jika yang sebelumnya kedaluwarsa atau hilang.

- **URL:** `/auth/resend-verification`
- **Method:** `POST`

#### Request Body
```json
{
  "email": "johndoe@example.com"
}
```

#### Success Response (200 OK)
```json
{
  "message": "Verification email resent",
  "verification_token": "eyJhbG... (hanya untuk testing)"
}
```

---

### Verify Email Token
Endpoint untuk memvalidasi token verifikasi dari email user. Biasanya berupa Link yang diklik user dari kotak masuk emailnya.

- **URL:** `/auth/verify-email?token={token}`
- **Method:** `GET`

#### Query Parameters
- `token`: String (Diambil dari link email)

#### Success Response (200 OK)
```json
{
  "message": "Email verified successfully. You can now login."
}
```

---

## 4. Document Processing

### Upload Document (PDF)
Endpoint untuk mengunggah file PDF. File akan divalidasi, diupload ke Cloudinary, kemudian teksnya diekstrak menggunakan PyMuPDF dan disimpan ke database.

- **URL:** `/documents/upload`
- **Method:** `POST`
- **Auth Required:** Yes (Bearer Token)
- **Content-Type:** `multipart/form-data`

#### Request Body (Form Data)
| Field   | Type   | Required | Description                       |
|---------|--------|----------|-----------------------------------|
| `title` | string | ✅       | Judul dokumen                     |
| `file`  | file   | ✅       | File PDF (maks. 10MB)             |

#### Headers
```
Authorization: Bearer <access_token>
```

#### Success Response (200 OK)
```json
{
  "id": 1,
  "user_id": 1,
  "title": "Modul Basis Data",
  "file_url": "https://res.cloudinary.com/.../quizzin/documents/modul.pdf",
  "file_type": "application/pdf",
  "file_size": 2048576,
  "preview_text": "BAB 1 - Pengantar Basis Data\nBasis data adalah kumpulan data yang...",
  "created_at": "2026-05-01T12:00:00.000",
  "updated_at": null
}
```

#### Error Responses

**400 Bad Request — Tipe file tidak valid:**
```json
{
  "detail": "Only PDF files are supported"
}
```

**400 Bad Request — File terlalu besar:**
```json
{
  "detail": "File too large. Max size is 10MB"
}
```

**401 Unauthorized — Token tidak valid/missing:**
```json
{
  "detail": "Could not validate credentials"
}
```

**500 Internal Server Error — Gagal upload ke Cloudinary:**
```json
{
  "detail": "Error uploading to storage: ..."
}
```

**500 Internal Server Error — Gagal ekstraksi teks:**
```json
{
  "detail": "Error extracting text from PDF: ..."
}
```

#### Catatan
- Hanya file PDF yang diterima (`application/pdf`).
- Maksimal ukuran file: **10MB**.
- Teks diekstrak otomatis dari semua halaman PDF menggunakan PyMuPDF.
- `preview_text` berisi **500 karakter pertama** dari teks yang diekstrak.
- `extracted_text` (teks lengkap) disimpan di database tetapi **tidak dikembalikan** di response untuk efisiensi.
