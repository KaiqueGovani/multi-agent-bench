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

## Published experiment

Run `npm ci` and `npm run dev` from `apps/web`, then open
[the v4.4 comparison](http://localhost:3000/research/comparison-v44).
The page reads the 600 sanitized records and summary tables from
`research-data/results/architectural-comparison-v44` in the repository.
The published comparison runs with only the frontend.

## Current scope

- Create a web chat conversation.
- Send text messages to `POST /messages`.
- Upload images and PDFs.
- Subscribe to SSE events for the active conversation.
- Render persisted messages and operational events.
- Render run-centric execution views backed by rich runtime projections.
