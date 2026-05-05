# Camera API + GraphQL Live TV

This project now includes:
- Existing REST camera CRUD: `/api/cameras/`
- GraphQL endpoint: `/graphql`
- User registration/login with JWT-style access/refresh tokens
- Email OTP verification
- Verified-user-only channel and playback access
- Tokenized playback URLs for m3u8 streaming

## Environment variables

Database (kept unchanged):
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`

SMTP:
- `EMAIL_HOST`
- `EMAIL_PORT` (default: `587`)
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `EMAIL_USE_TLS` (default: `true`)
- `DEFAULT_FROM_EMAIL`

Token/OTP settings (optional):
- `GRAPHQL_JWT_SECRET`
- `GRAPHQL_ACCESS_TOKEN_TTL_MINUTES` (default: `30`)
- `GRAPHQL_REFRESH_TOKEN_TTL_DAYS` (default: `7`)
- `STREAM_TOKEN_TTL_SECONDS` (default: `300`)
- `OTP_TTL_MINUTES` (default: `10`)
- `OTP_MAX_ATTEMPTS` (default: `5`)

## Setup

1. Install dependencies:
   - `pip install -r requirements.txt`
2. Run migrations:
   - `python manage.py migrate`
3. Seed channel list:
   - `python manage.py seed_channels`
4. Start API:
   - `python manage.py runserver 0.0.0.0:8000`

## GraphQL examples

Register:
```graphql
mutation {
  registerUser(username: "alice", email: "alice@example.com", password: "StrongPass123!") {
    success
    message
    accessToken
    refreshToken
    user { id username email emailVerified }
  }
}
```

Verify OTP:
```graphql
mutation {
  verifyEmailOtp(email: "alice@example.com", otp: "123456") {
    success
    message
    errors { code message }
  }
}
```

Login:
```graphql
mutation {
  login(usernameOrEmail: "alice@example.com", password: "StrongPass123!") {
    success
    accessToken
    refreshToken
    user { id email emailVerified }
  }
}
```

Get channels (requires `Authorization: Bearer <access_token>` and verified email):
```graphql
query {
  channels {
    id
    name
    channelNumber
    logoUrl
  }
}
```

Get playback URL:
```graphql
query {
  getPlaybackUrl(channelId: 1) {
    success
    playbackUrl
    expiresInSeconds
  }
}
```

## Frontend player recommendation

Use `hls.js` in web frontend for `.m3u8` playback. VLC can play many streams that browsers block because of CORS, mixed content, or codec limitations.

Example flow:
1. Login via GraphQL and keep access token.
2. Query `channels`.
3. Query `getPlaybackUrl(channelId)`.
4. Pass `playbackUrl` to `hls.js`.
