# POC web

Next.js frontend for the pharmacy multi-agent POC.

## Local run

Install dependencies from `apps/web`:

```bash
npm install
```

Run the frontend:

```bash
npm run dev
```

Default URL:

```txt
http://localhost:3000
```

The frontend expects the API at:

```txt
http://127.0.0.1:8000
```

Override with:

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

## Current scope

- Create a web chat conversation.
- Send text messages to `POST /messages`.
- Upload images and PDFs.
- Subscribe to SSE events for the active conversation.
- Render persisted messages and operational events.
- Render run-centric execution views backed by rich runtime projections.
