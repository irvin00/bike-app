# Bike View — Full Implementation Spec

A personal bike directory app to track bikes you own and have owned. Includes
maintenance records, images, tags ("pills"), and full-page detail views.

---

## 1. Tech Stack

| Layer          | Choice                        | Why                                                |
| -------------- | ----------------------------- | -------------------------------------------------- |
| Framework      | FastAPI + Jinja2              | Python API + server-rendered templates; dead simple |
| Language       | Python 3.14+                  | Clean, readable, no build step                     |
| Package mgmt   | uv                            | Fast, deterministic lockfile, single binary        |
| Styling        | Plain CSS + CSS variables     | No build step, design tokens via custom properties  |
| Client JS      | Vanilla JS (no framework)     | Sprinkled interactivity: inline edit, drag-and-drop |
| Database       | SQLite via `aiosqlite`        | Zero-setup, single-file DB; async for FastAPI       |
| Image processing| Pillow                        | Resize + thumbnail on upload                        |
| Image storage  | Local `/uploads` folder       | Simple today; swap in S3/GCS later (see §5)        |
| Image serving  | FastAPI route                 | `/api/images/...` serves uploaded files            |
| Forms          | Standard HTML forms + vanilla JS | No heavy form library needed for this scope     |
| Hosting        | Single-node VPS or home lab   | Personal app; no scale needed                      |

---

## 2. Data Models

### 2.1 `bikes`

| Column         | Type     | Notes                                |
| -------------- | -------- | ------------------------------------- |
| `id`           | integer  | PK, auto-increment                   |
| `name`         | text     | Headline text shown on card           |
| `description`  | text     | Short blurb on the card               |
| `full_story`   | text     | Plain text for the full-page view      |
| `status`       | text     | `'active'` or `'former'`             |
| `acquired_on`  | text     | ISO date string (optional)            |
| `retired_on`   | text     | ISO date string (optional)            |
| `created_at`   | text     | ISO timestamp                         |
| `updated_at`   | text     | ISO timestamp                         |

### 2.2 `pills` (tags)

| Column  | Type    | Notes                       |
| ------- | ------- | --------------------------- |
| `id`    | integer | PK, auto-increment          |
| `label` | text    | Unique, e.g. "Carbon Frame" |
| `color` | text    | Hex color or Tailwind class |

### 2.3 `bike_pills` (join table)

| Column    | Type    | Notes                       |
| --------- | ------- | --------------------------- |
| `bike_id` | integer | FK → bikes.id, ON DELETE CASCADE |
| `pill_id` | integer | FK → pills.id, ON DELETE CASCADE |
| PK is (`bike_id`, `pill_id`) |   |                             |

### 2.4 `maintenance_records`

| Column        | Type    | Notes                         |
| ------------- | ------- | ----------------------------- |
| `id`          | integer | PK, auto-increment            |
| `bike_id`     | integer | FK → bikes.id, ON DELETE CASCADE |
| `date`        | text    | ISO date of service           |
| `description` | text    | What was done                 |
| `cost`        | real    | Optional, nullable             |
| `created_at`  | text    | ISO timestamp                 |

### 2.5 `images`

| Column         | Type    | Notes                                  |
| -------------- | ------- | -------------------------------------- |
| `id`           | integer | PK, auto-increment                     |
| `bike_id`      | integer | FK → bikes.id, ON DELETE CASCADE       |
| `filename`     | text    | Stored filename (UUID on upload)       |
| `original_name`| text    | Original upload name                   |
| `is_primary`   | integer | Boolean; at most one per bike          |
| `sort_order`   | integer | Display ordering                       |
| `created_at`   | text    | ISO timestamp                          |

---

## 3. API Design

All routes live under `/api/`. Responses are JSON. Dates use ISO 8601.
FastAPI path parameters use `{id}` syntax.

### 3.1 Bikes

| Method | Path                        | Body / Query                  | Notes                        |
| ------ | --------------------------- | ----------------------------- | ---------------------------- |
| GET    | `/api/bikes`                | `?status=active` (optional)   | List all bikes (card data)   |
| GET    | `/api/bikes/{id}`           |                               | Single bike + pills + images |
| POST   | `/api/bikes`                | `{ name, description, ... }`  | Create a bike                |
| PATCH  | `/api/bikes/{id}`           | partial bike fields            | Update bike                  |
| DELETE | `/api/bikes/{id}`           |                               | Delete bike + cascade        |

### 3.2 Pills

| Method | Path                  | Body              | Notes          |
| ------ | --------------------- | ----------------- | -------------- |
| GET    | `/api/pills`          |                   | List all pills |
| POST   | `/api/pills`          | `{ label, color }`| Create pill   |
| DELETE | `/api/pills/{id}`     |                   | Delete pill    |

### 3.3 Bike ↔ Pill attachments

| Method | Path                                    | Notes              |
| ------ | --------------------------------------- | ------------------ |
| PUT    | `/api/bikes/{id}/pills`                 | `{ pill_ids: [] }` — sets full set of attached pills |

### 3.4 Maintenance Records

| Method | Path                                            | Body                         | Notes                 |
| ------ | ----------------------------------------------- | ---------------------------- | --------------------- |
| GET    | `/api/bikes/{id}/maintenance`                   |                              | All records for bike  |
| POST   | `/api/bikes/{id}/maintenance`                   | `{ date, description, cost }`| Add record            |
| PATCH  | `/api/bikes/{id}/maintenance/{record_id}`        | partial fields               | Edit record           |
| DELETE | `/api/bikes/{id}/maintenance/{record_id}`        |                              | Delete record         |

### 3.5 Images

| Method | Path                                    | Notes                          |
| ------ | --------------------------------------- | ------------------------------ |
| POST   | `/api/bikes/{id}/images`                | Multipart upload (one or many) |
| DELETE | `/api/bikes/{id}/images/{image_id}`     | Deletes file + DB row          |
| PATCH  | `/api/bikes/{id}/images/{image_id}`     | `{ is_primary, sort_order }`   |

---

## 4. UI Design & Component Tree

### 4.1 Routes

| Route           | Page                         |
| --------------- | ---------------------------- |
| `/`             | Home — grid of bike cards    |
| `/bikes/:id`    | Full-page bike detail        |
| `/bikes/new`    | Add-bike form                |
| `/bikes/:id/edit`| Edit-bike form              |
| `/pills`        | Manage pills (CRUD)          |

### 4.2 Component Tree

```
Layout (shell — nav bar, global actions)
├── HomePage
│   ├── BikeCard[]           ← grid of cards
│   │   ├── BikeImage        ← primary image (fallback to placeholder)
│   │   ├── BikeName         ← editable inline (click-to-edit)
│   │   ├── BikeDescription  ← truncated, expands on card hover
│   │   ├── PillBadge[]      ← colored pill/tag components
│   │   └── StatusBadge      ← "Active" / "Former" indicator
│   └── AddBikeFab           ← floating action button → /bikes/new
│
├── BikeDetailPage
│   ├── ImageGallery         ← carousel / grid of all images
│   ├── BikeInfo             ← name, description, full story, status
│   ├── PillBadge[]          ← attached pills
│   ├── MaintenanceSection
│   │   ├── MaintenanceTimeline  ← chronological list
│   │   │   └── MaintenanceRecord[]
│   │   └── MaintenanceForm      ← inline add/edit form
│   └── EditButton           ← → /bikes/:id/edit
│
├── BikeFormPage             ← shared for create & edit
│   ├── BikeForm
│   │   ├── TextFields       ← name, description, full_story
│   │   ├── StatusSelector   ← active / former radio
│   │   ├── DateFields       ← acquired_on, retired_on
│   │   ├── PillSelector     ← multi-select checkboxes from all pills
│   │   └── ImageUploadZone  ← drag-and-drop + preview + reorder
│   └── SubmitButton
│
└── PillManagePage
    ├── PillList
    │   └── PillRow[]        ← label, color swatch, delete button
    └── AddPillForm          ← label input + color picker
```

### 4.3 Card Design (Home Page)

Each card in the grid:
- **Image**: 3:2 aspect ratio, object-cover, rounded top corners. Placeholder SVG
  when no image is set.
- **Headline**: Editable inline — click text to turn it into an input; Enter or blur
  saves via `PATCH /api/bikes/:id`.
- **Description**: Two-line clamp, full text on tooltip hover.
- **Pills**: Horizontal row of small colored badges (e.g. "Carbon Frame",
  "Singlespeed"). Overflow scrolls horizontally instead of wrapping.
- **Expand**: Clicking the card (outside the editable headline) navigates to
  `/bikes/:id` for the full-page view.
- **Status indicator**: A small dot or subtle border — green for active, grey for
  former.
- **Delete**: An X or trash icon in the top-right corner that opens a confirm
  dialog.

---

## 5. Image & File Storage Strategy

### Phase 1 — Local (now)

- Images are written to `/uploads/bikes/<bike-id>/<uuid>-<original-name>`.
- Filenames are UUID-prefixed to prevent collisions.
- A FastAPI route serves images: `/api/images/{bike_id}/{filename}`.
  This lets us add auth or access control later without changing URLs.
- Image processing on upload: resize to max 2000px wide via Pillow, generate a
  1024px thumbnail for cards and the gallery.

### Phase 2 — Cloud (future)

- Abstract behind an `ImageStore` protocol with `put()`, `get()`, `delete()`.
- Implement `LocalImageStore` now, swap in `S3ImageStore` later.
- The API route hides the storage backend — frontend never touches files directly.

---

## 6. Implementation Phases

### Phase 1 — Skeleton & DB ✅
- FastAPI app scaffold (`app.py` entry point)
- SQLite schema as raw SQL or simple helper module (`db.py`)
- Create tables on startup
- Seed one or two bikes for development
- Build API routes for bikes (GET list, POST create)

### Phase 2 — Home Page & Cards ✅
- Base Jinja2 layout template (nav bar, status filter, CSS imports)
- Home page template: responsive grid of bike cards
- Bike card partial template (image, name, description, pills, status)
- Wire to `/api/bikes` + `/` route returning full HTML
- Inline headline editing via vanilla JS (click → input → fetch PATCH)
- Primary image rendering on cards (fallback to placeholder when no image)

### Phase 3 — Bike Detail, Add & Edit ✅
- `/bikes/{id}` route: full-page template
- Image gallery (CSS scroll-snap horizontal strip + full-size modal)
- Full bike info display
- Maintenance records list + inline add form (vanilla JS fetch)
- `/bikes/new` route: create bike form
- `/bikes/{id}/edit` route: edit bike form (shared template with create)
- Form fields: name, description, full story, status, dates, pills, images

### Phase 4 — Pills Management ✅
- Pill CRUD API routes
- `/pills` page: list, add form, delete buttons
- Pill selector (multi-select checkboxes) on bike create/edit forms

### Phase 5 — Home Page Status Filter ✅
- `/` route honors `?status=` query param (all / active / former), reusing the
  existing `/api/bikes?status=` filter support
- Nav "All / Active / Former" buttons switch the filter on the home grid
- Active filter button is highlighted to reflect the current selection

### Phase 6 — Image Upload ✅
- Multipart upload endpoint (FastAPI `UploadFile`)
- Image resizing + thumbnail with Pillow
- Drag-and-drop upload zone (vanilla JS `drop` event + `FormData`)
- Primary image selection, reorder, delete

### Phase 7 — Home Page Bike Delete ✅
- Wire the card X button on the home grid and a Delete button on the bike
  detail page to `DELETE /api/bikes/{id}` with a confirm dialog
- Card removed from the grid in place (no reload); detail page redirects home
- Empty state updates after the last bike is deleted

### Phase 7.5 — Image Upload on Bike Creation ✅
- `/bikes/new` gets the drag-and-drop upload zone with client-side pending
  previews (no star button — reorder order determines primary)
- Images upload to `/api/bikes/{id}/images` after the bike is created, before
  redirect; failures alert and still redirect
- Create flow guards against double-submit; pills/image failures are
  best-effort with distinct alerts

### Phase 7.6 — Gallery Nav Arrows ✅
- Prev/next arrow buttons overlaid on the bike detail image gallery; slides
  fill the gallery (one full-width image per view, no next-image preview),
  arrows render only when the bike has more than one image
- Arrows disabled at the strip's ends; state updates on scroll/resize
- Smooth scroll to the next/prev slide via target-image offsetLeft
  (lands on snap points)

### Phase 8 — Polish ✅
- Responsive grid (1 col mobile, 2 tablet, 3+ desktop) via CSS container queries ✅
- Transitions and hover states ✅
- Empty states and error banners ✅
- Confirm dialogs for delete actions (vanilla JS `<dialog>`) ✅
- Loading spinners (CSS animation on fetch calls) ✅
- Unit tests with pytest + httpx (ASGITransport) for all API routes ✅

### Phase 9 — Settings & Data Management ✅
- Settings button (gear icon) in the nav bar opens a slide-in sidebar drawer
  (vanilla JS, same overlay pattern as the confirm dialogs)
- Sidebar lists settings sections; extensible to future options (Appearance,
  About, …). "Data" navigates to `/settings/data`, a full-page settings
  template reusing `base.html.j2`
- Data settings page, two blocks:
  - **Export** — button downloads `GET /api/export` → `bike_view.json`
    (Content-Disposition attachment; nested shape: bikes with pills, images
    with url/thumb_url, maintenance records, plus the pill catalog) — shipped
  - **Import** — file picker for a `bike_view.json` export → `POST /api/import`
    (multipart upload); server validates the export shape and restores it — shipped
- Import semantics (v1): full restore — existing rows are deleted, then
  bikes, pills, bike_pills, maintenance_records, and images are inserted from
  the JSON; destructive action requires a confirm dialog; the response
  summarizes restored counts (bikes, pills, images, maintenance)
- Image files: the export holds filenames + URLs, not file bytes — restored
  image rows render only when `uploads/` is present (copy the folder alongside
  the JSON; a future zip bundle may embed images); missing files fall back to
  the placeholder instead of erroring
- Pill catalog inserts are idempotent (INSERT OR IGNORE on unique label)
- Validation is all-or-nothing: the whole file must validate (missing keys,
  wrong types) before anything is written — 422 with a clear message otherwise

### Phase 10 — PWA Push Notifications ⏳ Planned, not implemented

Design finalized 2026-08-05; nothing shipped yet. Implements V2 follow-up #3's
reminder half (below) via standard PWA Web Push.

- **What**: two notification triggers —
  - **Maintenance reminders**: a daily background check (asyncio loop started
    in the app lifespan, gated behind `PUSH_REMINDER_ENABLED=1` + VAPID keys
    present so tests never start it) that finds **active** bikes whose most
    recent `maintenance_records.date` is older than `REMINDER_DAYS` (env var,
    default 30) and pushes "Time to service the {name}". Bikes with no
    maintenance history are skipped.
  - **Test send**: a "Send test notification" button in the UI.
- **Mechanism**: browser subscribes via PushManager with the app's VAPID
  public key; the subscription is stored server-side in a new
  `push_subscriptions` table (upsert by endpoint, so the client can naively
  re-POST on every page load); `pywebpush` sends encrypted pushes with
  `ttl=86400`; expired subscriptions (404/410) are deleted. A new
  `maintenance_reminders` table (bike_id PK, `last_sent`) debounces to at
  most one reminder per window per bike — no ALTER on existing tables, both
  are plain `CREATE TABLE IF NOT EXISTS`.
- **New files** (planned): `app/push.py` (VAPID helpers, send, reminder
  check/loop), `app/routes/push.py` (`POST /api/push/subscriptions`,
  `DELETE /api/push/subscriptions?endpoint=...`, `POST /api/push/test`,
  `GET /api/push/public-key`, `POST /api/push/reminders/run`, plus `GET
  /sw.js` and `GET /manifest.webmanifest` served at root scope with explicit
  MIME types), `static/sw.js` (push-only — no fetch handler, no caching),
  `static/manifest.webmanifest`, `static/js/push.js`, and PNG icons
  (192/512 + 180px apple-touch-icon) generated once from `favicon.jpg`.
- **Constraints** (why it's blocked on infra):
  - **HTTPS required** — Web Push and service workers only work in secure
    contexts. App is plain HTTP on a LAN today. Plan: Caddy reverse proxy in
    `compose.yaml` with automatic Let's Encrypt behind a DuckDNS domain
    (a bare LAN IP cannot get a public cert; NAT hairpin must work for
    phones on the LAN). Fallback if the ISP uses CGNAT: Tailscale Serve
    (`*.ts.net` URL, no port forwarding).
  - **iOS Safari (16.4+)** only delivers Web Push to *installed* PWAs: user
    must Add to Home Screen / Dock (`display: standalone` + `apple-touch-icon`
    required), and `Notification.requestPermission()` must come from a user
    gesture — never on page load, or iOS marks it denied permanently.
  - **`TZ` env var** must be set in compose — containers default to UTC and
    reminder dates are local calendar dates.
- **Config**: env vars only — `REMINDER_DAYS` (default 30),
  `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` / `VAPID_SUBJECT` (generated once,
  kept in gitignored `.env`, template in `.env.example`),
  `PUSH_REMINDER_ENABLED`.

---

## 7. Project File Structure

```
bike_view/
├── spec.md                          ← this file
├── pyproject.toml                   ← uv project config + dependencies
├── uv.lock                          ← deterministic lockfile
├── data/
│   └── bike_view.db                ← SQLite database (gitignored)
├── uploads/                         ← local image storage (gitignored)
│   └── bikes/
│       └── <bike-id>/
│           └── <uuid>-<name>.jpg
├── app/
│   ├── __init__.py
│   ├── main.py                      ← FastAPI app entry point, lifespan, mount static
│   ├── db.py                        ← aiosqlite connection, init_db(), query helpers
│   ├── seed.py                      ← dev seed data (2 bikes, sample pills)
│   ├── image_store.py               ← ImageStore protocol + LocalImageStore + thumbnail
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── bikes.py                 ← /api/bikes and /api/bikes/{id}
│   │   ├── pills.py                 ← /api/pills and /api/pills/{id}
│   │   ├── export.py                ← GET /api/export
│   │   ├── import_data.py           ← POST /api/import (full restore)
│   │   ├── bike_pills.py            ← /api/bikes/{id}/pills
│   │   ├── maintenance.py           ← /api/bikes/{id}/maintenance/{record_id}
│   │   ├── images.py                ← /api/bikes/{id}/images/{image_id}
│   │   └── serve_images.py          ← /api/images/{bike_id}/{filename}
│   └── templates/
│       ├── base.html.j2             ← shell layout (nav, CSS, JS imports)
│       ├── index.html.j2            ← home page: bike card grid
│       ├── bike_detail.html.j2      ← full-page view + maintenance
│       ├── bike_form.html.j2        ← shared create/edit form
│       ├── pills.html.j2            ← pill management page
│       ├── settings_data.html.j2    ← export/import page
│       └── partials/
│           ├── bike_card.html.j2    ← single card (reused in grid)
│           ├── pill_badge.html.j2   ← colored pill span
│           ├── confirm_dialog.html.j2 ← reusable <dialog>
│           └── settings_drawer.html.j2 ← slide-in settings sidebar
├── static/
│   ├── css/
│   │   └── app.css                  ← all styles, CSS variables for tokens
│   ├── js/
│   │   ├── api.js                   ← tiny fetch wrapper + global in-flight spinner
│   │   ├── ui.js                    ← error banner (showError)
│   │   ├── inline-edit.js           ← click-to-edit headline
│   │   ├── image-upload.js          ← drag-and-drop + preview + FormData
│   │   ├── maintenance-form.js      ← inline add/edit via fetch
│   │   ├── bike-delete.js           ← home/detail delete flows
│   │   ├── gallery-nav.js           ← gallery prev/next arrows
│   │   ├── pills.js                 ← pill page CRUD
│   │   ├── confirm-dialog.js        ← <dialog> open/close + confirm hook
│   │   ├── settings-drawer.js       ← settings sidebar open/close
│   │   ├── settings-data.js         ← import flow on /settings/data
│   │   └── image-fallback.js        ← missing-image → placeholder swap
│   └── img/
│       └── placeholder-bike.svg     ← fallback image
├── tests/
│   ├── fixtures.py                  ← tmp DB/uploads patches + seeded ASGI client
│   ├── test_bikes.py
│   ├── test_pills.py
│   ├── test_maintenance.py
│   ├── test_bike_pills.py
│   ├── test_images.py
│   ├── test_serve_images.py
│   └── test_pages.py
```

---

## 8. Decisions

| Decision          | Choice                       | Rationale                                      |
| ----------------- | ---------------------------- | ---------------------------------------------- |
| Authentication    | None — local only            | Personal app, runs on local network            |
| Rich text         | Plain text (`<textarea>`)    | Simplest to implement and maintain             |
| Search & filter   | Status toggle only           | active / former / all; no text search or pill filter |
| Responsive design | Desktop + mobile             | Fully responsive grid and forms                |

---

## 9. V2 Follow-ups

Features explicitly deferred to a future version:

1. **JSON export** — ✅ Shipped in Phase 9.

2. **Search & text/pill filter** — Full-text search across bike names and
   descriptions, plus filtering by attached pills on the home page.

3. **Maintenance reminders** — Surface upcoming or past-due maintenance based on
   mileage or time intervals (e.g. "chain lube due in 100 miles"). Requires
   mileage tracking and interval configuration.

4. **Authentication** — Basic Auth or NextAuth single-user provider, needed
   only if the app is later exposed to the internet.
