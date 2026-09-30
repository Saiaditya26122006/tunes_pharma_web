# Tunes Pharma API v1

Base URL: `/api/v1`

All API endpoints require JWT authentication unless noted otherwise.

## Authentication

### POST /api/v1/auth/login

Authenticate a doctor and receive JWT tokens.

**Public** — no token required.

**Request body:**
```json
{
  "username": "dr_smith",
  "password": "secret"
}
```

**Success (200):**
```json
{
  "success": true,
  "data": {
    "tokens": {
      "access_token": "eyJ...",
      "refresh_token": "eyJ...",
      "expires_in": 900,
      "token_type": "Bearer"
    },
    "doctor": {
      "id": "uuid",
      "name": "Dr. Smith",
      "specialty": "Cardiology"
    }
  }
}
```

**Errors:**
- `400 BAD_REQUEST` — missing username or password
- `401 UNAUTHORIZED` — invalid credentials
- `429 RATE_LIMITED` — too many login attempts (5 per 5 minutes per IP)

---

### POST /api/v1/auth/refresh

Exchange a refresh token for a new access + refresh token pair (rotation).

**Public** — no access token required (uses refresh token in body).

**Request body:**
```json
{
  "refresh_token": "eyJ..."
}
```

**Success (200):**
```json
{
  "success": true,
  "data": {
    "tokens": {
      "access_token": "eyJ...",
      "refresh_token": "eyJ...",
      "expires_in": 900,
      "token_type": "Bearer"
    }
  }
}
```

**Errors:**
- `400 BAD_REQUEST` — missing refresh_token
- `401 UNAUTHORIZED` — expired, invalid, or already-used token

---

### POST /api/v1/auth/logout

Revoke the refresh token (invalidates the session).

**Requires:** Bearer token in `Authorization` header.

**Request body:**
```json
{
  "refresh_token": "eyJ..."
}
```

**Success (200):**
```json
{
  "success": true,
  "data": { "message": "Logged out." }
}
```

---

### GET /api/v1/auth/me

Get the current doctor's profile.

**Requires:** Bearer token in `Authorization` header.

**Success (200):**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "name": "Dr. Smith",
    "specialty": "Cardiology",
    "hospital": "City Hospital",
    "email": "dr.smith@example.com",
    "phone": "+91 9876543210",
    "username": "dr_smith"
  }
}
```

---

## Articles

All article endpoints only return **published** articles.

### GET /api/v1/articles

List published articles with pagination and filters.

**Requires:** Bearer token.

**Query parameters:**
| Param | Type | Default | Description |
|---|---|---|---|
| `page` | int | 1 | Page number |
| `limit` | int | 20 | Items per page (max 100) |
| `therapy_area` | string | — | Filter by therapy area (diabetes, neuropathy, gastro, general, all) |
| `category` | string | — | Filter by category |
| `content_type` | string | — | Filter by type (pdf, doc, link) |
| `search` | string | — | Search in title and description |

**Success (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "title": "New Diabetes Research",
      "description": "...",
      "content_type": "pdf",
      "file_url": "https://...",
      "therapy_area": "diabetes",
      "author": "Dr. Johnson",
      "category": "Research",
      "thumbnail_url": "https://...",
      "published_at": "2024-01-15T10:30:00Z",
      "created_at": "2024-01-14T08:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 42,
    "has_next": true
  }
}
```

---

### GET /api/v1/articles/:id

Get a single published article by ID.

**Requires:** Bearer token.

**Success (200):**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "title": "New Diabetes Research",
    "description": "...",
    "content_type": "pdf",
    "file_url": "https://...",
    "therapy_area": "diabetes",
    "author": "Dr. Johnson",
    "category": "Research",
    "thumbnail_url": "https://...",
    "published_at": "2024-01-15T10:30:00Z",
    "created_at": "2024-01-14T08:00:00Z"
  }
}
```

**Errors:**
- `404 NOT_FOUND` — article does not exist or is not published

---

---

## Bookmarks

### GET /api/v1/bookmarks

List the authenticated doctor's bookmarked articles.

**Requires:** Bearer token.

**Query parameters:**
| Param | Type | Default | Description |
|---|---|---|---|
| `page` | int | 1 | Page number |
| `limit` | int | 20 | Items per page (max 100) |

**Success (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": "bookmark-uuid",
      "paper_id": "article-uuid",
      "created_at": "2024-01-15T10:30:00Z",
      "article": {
        "id": "article-uuid",
        "title": "...",
        "description": "...",
        "content_type": "pdf",
        "file_url": "https://...",
        "therapy_area": "diabetes",
        "author": "Dr. Johnson",
        "category": "Research",
        "thumbnail_url": "https://...",
        "published_at": "2024-01-15T10:30:00Z"
      }
    }
  ],
  "pagination": { "page": 1, "limit": 20, "total": 5, "has_next": false }
}
```

---

### POST /api/v1/bookmarks/:article_id

Bookmark a published article. Idempotent — returns 200 if already bookmarked.

**Requires:** Bearer token.

**Success (201):**
```json
{
  "success": true,
  "data": { "id": "bookmark-uuid", "article_id": "article-uuid" }
}
```

**Already bookmarked (200):**
```json
{
  "success": true,
  "data": { "id": "bookmark-uuid", "article_id": "article-uuid" }
}
```

**Errors:**
- `404 NOT_FOUND` — article does not exist or is not published

---

### DELETE /api/v1/bookmarks/:article_id

Remove a bookmark. Only the authenticated doctor's bookmark is affected.

**Requires:** Bearer token.

**Success (200):**
```json
{
  "success": true,
  "data": { "message": "Bookmark removed." }
}
```

**Errors:**
- `404 NOT_FOUND` — bookmark not found

---

## Profile

### GET /api/v1/profile

Get the authenticated doctor's profile.

**Requires:** Bearer token.

**Success (200):**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "name": "Dr. Smith",
    "username": "dr_smith",
    "email": "dr.smith@example.com",
    "phone": "+91 9876543210",
    "hospital": "City Hospital",
    "specialty": "Cardiology",
    "whatsapp_number": "+91 9876543210",
    "whatsapp_consent": true,
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

---

### PATCH /api/v1/profile

Update the authenticated doctor's profile.

**Requires:** Bearer token.

**Updatable fields:** `name`, `specialty`, `hospital`, `email`, `phone`, `whatsapp_number`

**Request body:**
```json
{
  "name": "Dr. Smith Jr.",
  "hospital": "New Hospital"
}
```

**Success (200):**
```json
{
  "success": true,
  "data": { "id": "uuid", "name": "Dr. Smith Jr.", "hospital": "New Hospital", "..." : "..." }
}
```

**Errors:**
- `400 BAD_REQUEST` — no valid fields or JSON body missing

---

## Notification Preferences

### GET /api/v1/profile/notifications

Get the authenticated doctor's notification preferences.

**Requires:** Bearer token.

**Success (200):**
```json
{
  "success": true,
  "data": {
    "email_preference": true,
    "push_preference": true,
    "sms_preference": false
  }
}
```

---

### PATCH /api/v1/profile/notifications

Update notification preferences.

**Requires:** Bearer token.

**Request body:**
```json
{
  "email_preference": false,
  "push_preference": true
}
```

All values must be booleans.

**Success (200):**
```json
{
  "success": true,
  "data": {
    "email_preference": false,
    "push_preference": true,
    "sms_preference": false
  }
}
```

**Errors:**
- `400 BAD_REQUEST` — non-boolean values or no valid fields

---

## Notifications

### GET /api/v1/notifications

List the authenticated doctor's in-app notifications.

**Requires:** Bearer token.

**Query parameters:**
| Param | Type | Default | Description |
|---|---|---|---|
| `page` | int | 1 | Page number |
| `limit` | int | 20 | Items per page (max 100) |

**Success (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": "notification-uuid",
      "paper_id": "article-uuid",
      "is_read": false,
      "created_at": "2024-01-15T10:30:00Z",
      "article": {
        "id": "article-uuid",
        "title": "New Diabetes Research",
        "therapy_area": "diabetes",
        "content_type": "pdf",
        "thumbnail_url": "https://...",
        "published_at": "2024-01-15T10:30:00Z"
      }
    }
  ],
  "pagination": { "page": 1, "limit": 20, "total": 10, "has_next": false }
}
```

---

### PATCH /api/v1/notifications/:id/read

Mark a single notification as read. Only the authenticated doctor's notifications can be marked.

**Requires:** Bearer token.

**Success (200):**
```json
{
  "success": true,
  "data": { "message": "Marked as read." }
}
```

**Errors:**
- `404 NOT_FOUND` — notification not found or belongs to another doctor

---

### POST /api/v1/notifications/read-all

Mark all of the authenticated doctor's unread notifications as read.

**Requires:** Bearer token.

**Success (200):**
```json
{
  "success": true,
  "data": { "marked": 5 }
}
```

---

## Push Token Registration

### POST /api/v1/push/subscribe

Register an Expo push token for the authenticated doctor's device.

**Requires:** Bearer token.

**Request body:**
```json
{
  "expo_token": "ExponentPushToken[abc123xyz]",
  "platform": "ios"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `expo_token` | string | yes | Must match `ExponentPushToken[...]` format |
| `platform` | string | no | `ios`, `android`, or `web` |

**Success (201):**
```json
{
  "success": true,
  "data": { "message": "Push token registered." }
}
```

**Already registered (200):**
```json
{
  "success": true,
  "data": { "message": "Token already registered." }
}
```

**Errors:**
- `400 BAD_REQUEST` — missing or invalid token format, invalid platform

---

### DELETE /api/v1/push/subscribe

Remove an Expo push token.

**Requires:** Bearer token.

**Request body:**
```json
{
  "expo_token": "ExponentPushToken[abc123xyz]"
}
```

**Success (200):**
```json
{
  "success": true,
  "data": { "message": "Token removed." }
}
```

**Errors:**
- `400 BAD_REQUEST` — missing token
- `404 NOT_FOUND` — token not found for this doctor

---

## Feed

### GET /api/v1/feed

Personalized article feed for the authenticated doctor. Articles matching the doctor's specialty therapy area are prioritized. Falls back to latest published content.

**Requires:** Bearer token.

**Query parameters:**
| Param | Type | Default | Description |
|---|---|---|---|
| `page` | int | 1 | Page number |
| `limit` | int | 20 | Items per page (max 100) |

**Success (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "title": "New Diabetes Research",
      "description": "...",
      "content_type": "pdf",
      "file_url": "https://...",
      "therapy_area": "diabetes",
      "author": "Dr. Johnson",
      "category": "Research",
      "thumbnail_url": "https://...",
      "published_at": "2024-01-15T10:30:00Z",
      "created_at": "2024-01-14T08:00:00Z"
    }
  ],
  "pagination": { "page": 1, "limit": 20, "total": 42, "has_next": true }
}
```

---

## Error Format

All errors follow the same structure:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description."
  }
}
```

## Authentication Flow

1. Doctor logs in via `POST /auth/login` → receives `access_token` + `refresh_token`
2. Use `access_token` in `Authorization: Bearer <token>` header for all requests
3. Access token expires in 15 minutes — use `POST /auth/refresh` to get a new pair
4. Refresh tokens are single-use (rotation) — each refresh gives a new pair
5. Refresh tokens expire in 30 days
6. On logout, call `POST /auth/logout` to revoke the refresh token
