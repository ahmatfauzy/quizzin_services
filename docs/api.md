# Smart Tutor API Documentation

Dokumentasi ini berisi daftar endpoint API yang tersedia di Smart Tutor backend. Karena menggunakan FastAPI, kamu juga dapat melihat dokumentasi interaktif secara langsung dengan mengakses `/docs` (Swagger UI) atau `/redoc` pada browser ketika server berjalan.

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
    "message": "Welcome to Smart Tutor API"
  }
  ```

---

## 2. Authentication

### Google OAuth - Mobile Login
Endpoint ini digunakan oleh aplikasi Mobile (Flutter) setelah mendapatkan `id_token` dari SDK Google Sign-In di sisi client.

- **URL:** `/auth/google/mobile`
- **Method:** `POST`
- **Auth Required:** No

#### Request Body
- **Content-Type:** `application/json`
```json
{
  "token": "string (Google ID Token dari Frontend Mobile)"
}
```

#### Success Response
- **Code:** `200 OK`
- **Content:**
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
    "created_at": "2026-04-29T16:00:00.000",
    "updated_at": null
  }
}
```

#### Error Response
- **Code:** `401 Unauthorized`
- **Content:**
```json
{
  "detail": "Invalid Google token"
}
```

---

### Google OAuth - Web Login Flow
Endpoint ini memulai alur OAuth 2.0 untuk aplikasi Web. Akan me-redirect browser pengguna langsung ke halaman Login Google.

- **URL:** `/auth/google/web/login`
- **Method:** `GET`
- **Auth Required:** No

#### Success Response
- **Code:** `302 Found` (Redirect)
- **Description:** Browser akan diarahkan secara otomatis ke URL Google Authorization.

---

### Google OAuth - Web Callback
Endpoint ini adalah tujuan *callback* (Redirect URI) yang diakses oleh Google setelah pengguna berhasil login di halaman Web Google. Backend akan secara otomatis menukar *Authorization Code* dengan *Access Token*, mendaftarkan/mencari user di database, lalu mengembalikan token aplikasi (JWT).

- **URL:** `/auth/google/web/callback`
- **Method:** `GET`
- **Auth Required:** No

#### Query Parameters
- `code` : `string` (Otomatis dikirim oleh Google)
- `state` : `string` (Otomatis dikirim oleh Google)

#### Success Response
- **Code:** `200 OK`
- **Content:**
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
    "created_at": "2026-04-29T16:00:00.000",
    "updated_at": null
  }
}
```

#### Error Response
- **Code:** `400 Bad Request`
- **Content:**
```json
{
  "detail": "No user info found"
}
```
