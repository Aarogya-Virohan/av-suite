# Arogya Virohan Platform

Standalone platform shell and home prototype.

## Run locally

```sh
npm install
npm run dev
```

Open `http://localhost:3000/platform`.

Set `BACKEND_API_URL` in `.env.local` to the backend origin (for example,
`http://127.0.0.1:8000`). This variable is server-only; do not prefix it with
`NEXT_PUBLIC_`. Sign in at `/login` using the backend account. The access token
is held in an HttpOnly session cookie and is not exposed to browser JavaScript.