# Tunes Pharma — Doctor Mobile App

React Native + Expo + TypeScript mobile application for doctors registered in the Tunes Pharma platform.

## Architecture

```
React Native App  →  Flask API (/api/v1)  →  Supabase PostgreSQL
```

The mobile app never connects directly to Supabase. All data flows through the existing Flask backend via JWT-authenticated REST endpoints.

### Authentication Flow

1. Doctor enters username + password on the login screen
2. App calls `POST /api/v1/auth/login` on the Flask backend
3. Backend validates credentials against the `doctors` table and returns JWT access + refresh tokens
4. Tokens are stored in device secure storage (Keychain on iOS, EncryptedSharedPreferences on Android)
5. All subsequent API calls include `Authorization: Bearer <access_token>`
6. When the access token expires (15 min), the API client automatically refreshes using the refresh token
7. If the refresh token is also expired or revoked, the user is returned to the login screen

### Project Structure

```
mobile/
├── app/                    # Expo Router screens
│   ├── _layout.tsx         # Root layout (AuthProvider wrapper)
│   ├── index.tsx           # Entry redirect (auth check)
│   ├── (auth)/             # Unauthenticated routes
│   │   ├── _layout.tsx     # Auth guard (redirects if logged in)
│   │   └── login.tsx       # Login screen
│   └── (app)/              # Authenticated routes
│       ├── _layout.tsx     # App guard (redirects if not logged in)
│       └── index.tsx       # Home placeholder
├── src/
│   ├── api/
│   │   ├── client.ts       # HTTP client with auto-refresh
│   │   ├── auth.ts         # Auth endpoint wrappers
│   │   └── types.ts        # TypeScript types for API
│   ├── auth/
│   │   ├── AuthProvider.tsx # React context for auth state
│   │   └── tokenStorage.ts # Secure token persistence
│   └── config/
│       └── index.ts        # Environment-based configuration
└── src/__tests__/          # Unit tests
```

## Prerequisites

- Node.js 22+
- npm 10+
- Android Studio with Android SDK (for Android development)
- Expo Go app on a physical device (alternative to emulator)

## Installation

```bash
cd mobile
npm install
```

## Environment Variables

Copy the example file and configure:

```bash
cp .env.example .env
```

| Variable | Description | Example |
|---|---|---|
| `EXPO_PUBLIC_API_URL` | Flask backend base URL | `http://10.0.2.2:5000` |

**Android emulator**: Use `http://10.0.2.2:5000` to reach the host machine's localhost.

**Physical device**: Use your computer's LAN IP (e.g., `http://192.168.1.100:5000`).

**Production**: Set to your production API URL (e.g., `https://tunespharma.org`).

## Development

Start the Expo dev server:

```bash
npx expo start
```

### Android

With Android emulator running or device connected:

```bash
npx expo start --android
```

Or press `a` in the Expo dev server terminal.

### Type Checking

```bash
npm run typecheck
```

### Tests

```bash
npm test
```

## API Configuration

The app communicates with these Flask API endpoints:

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/v1/auth/login` | POST | Authenticate doctor |
| `/api/v1/auth/refresh` | POST | Refresh access token |
| `/api/v1/auth/logout` | POST | Revoke refresh token |
| `/api/v1/auth/me` | GET | Get current doctor profile |

Full API documentation: `docs/API_V1.md` in the backend repository.

## Security

- JWT tokens stored in OS-level secure storage (not AsyncStorage)
- No Supabase credentials in the mobile app
- Automatic token refresh with race condition prevention
- Failed refresh clears all tokens and forces re-login
- Passwords never logged or stored locally
- No hardcoded credentials anywhere in source
