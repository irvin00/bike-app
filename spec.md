# Bike View — Full Implementation Spec

A personal bike directory app to track bikes you own and have owned. Includes
maintenance records, images, tags ("pills"), and full-page detail views.

---

## 1. Tech Stack

| Layer          | Choice                        | Why                                                |
| -------------- | ----------------------------- | -------------------------------------------------- |
| Framework      | Next.js 14 (App Router)       | UI + API in one app; file-based routing; RSC ready |
| Language       | TypeScript (strict)           | Catch mistakes early on a personal project         |
| Styling        | Tailwind CSS                  | Rapid UI with consistent design tokens             |
| Database       | SQLite via `better-sqlite3`   | Zero-setup, single-file DB; perfect for single-user|
| ORM            | Drizzle ORM                   | Lightweight, type-safe, good SQLite support        |
| Image storage  | Local `/uploads` folder       | Simple today; swap in S3/GCS later (see §6)        |
| Image serving  | Next.js static serving + API  | Serves local files; API route for protected paths  |
| Forms          | React Hook Form + Zod         | Validation and ergonomics                          |
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

### 3.1 Bikes

| Method | Path              | Body / Query                  | Notes                        |
| ------ | ----------------- | ----------------------------- | ---------------------------- |
| GET    | `/api/bikes`      | `?status=active` (optional)   | List all bikes (card data)   |
| GET    | `/api/bikes/:id`  |                               | Single bike + pills + images |
| POST   | `/api/bikes`      | `{ name, description, ... }`  | Create a bike                |
| PATCH  | `/api/bikes/:id`  | partial bike fields            | Update bike                  |
| DELETE | `/api/bikes/:id`  |                               | Delete bike + cascade        |

### 3.2 Pills

| Method | Path             | Body              | Notes          |
| ------ | ---------------- | ----------------- | -------------- |
| GET    | `/api/pills`     |                   | List all pills |
| POST   | `/api/pills`     | `{ label, color }`| Create pill   |
| DELETE | `/api/pills/:id` |                   | Delete pill    |

### 3.3 Bike ↔ Pill attachments

| Method | Path                              | Notes              |
| ------ | --------------------------------- | ------------------ |
| PUT    | `/api/bikes/:id/pills`            | `{ pillIds: [] }` — sets full set of attached pills |

### 3.4 Maintenance Records

| Method | Path                                      | Body                         | Notes                 |
| ------ | ----------------------------------------- | ---------------------------- | --------------------- |
| GET    | `/api/bikes/:id/maintenance`              |                              | All records for bike  |
| POST   | `/api/bikes/:id/maintenance`              | `{ date, description, cost }`| Add record            |
| PATCH  | `/api/bikes/:id/maintenance/:recordId`    | partial fields               | Edit record           |
| DELETE | `/api/bikes/:id/maintenance/:recordId`    |                              | Delete record         |

### 3.5 Images

| Method | Path                              | Notes                          |
| ------ | --------------------------------- | ------------------------------ |
| POST   | `/api/bikes/:id/images`           | Multipart upload (one or many) |
| DELETE | `/api/bikes/:id/images/:imageId`  | Deletes file + DB row          |
| PATCH  | `/api/bikes/:id/images/:imageId`  | `{ is_primary, sort_order }`   |

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
- A Next.js API route serves images: `/api/images/<bike-id>/<filename>`.
  This lets us add auth or access control later without changing URLs.
- Image processing on upload: resize to max 2000px wide via `sharp`, generate a
  400px thumbnail for cards.

### Phase 2 — Cloud (future)

- Abstract behind an `ImageStore` interface with `put()`, `get()`, `delete()`.
- Implement `LocalImageStore` now, swap in `S3ImageStore` later.
- The API route hides the storage backend — frontend never touches files directly.

---

## 6. Implementation Phases

### Phase 1 — Skeleton & DB (day 1)
- Scaffold Next.js project with TypeScript + Tailwind
- Set up Drizzle ORM + SQLite schema
- Create DB migration
- Seed one or two bikes for development
- Build API routes for bikes (GET, POST)

### Phase 2 — Home Page & Cards (day 2)
- Build Layout shell
- Build BikeCard components with static data
- Wire to `/api/bikes`
- Implement inline headline editing
- Build pill display on cards

### Phase 3 — Bike Detail Page (day 3)
- Build `/bikes/:id` page
- Image gallery component
- Full bike info display
- Maintenance records list + inline add form

### Phase 4 — Pills Management (day 3-4)
- Pill CRUD API
- Pill management page
- Pill selector on bike edit form

### Phase 5 — Image Upload (day 4)
- Multipart upload endpoint
- Image resizing with `sharp`
- Drag-and-drop upload zone
- Primary image selection
- Reorder / delete images

### Phase 6 — Polish (day 5)
- Responsive grid (1 col mobile, 2 tablet, 3+ desktop)
- Transitions and hover states
- Empty states and error boundaries
- Confirm dialogs for destructive actions
- Loading skeletons

---

## 7. Project File Structure

```
bike_view/
├── spec.md                          ← this file
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── next.config.ts
├── drizzle.config.ts
├── data/
│   └── bike_view.db                ← SQLite database (gitignored)
├── uploads/                         ← local image storage (gitignored)
│   └── bikes/
│       └── <bike-id>/
│           └── <uuid>-<name>.jpg
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                ← home page (bike grid)
│   │   ├── bikes/
│   │   │   ├── [id]/
│   │   │   │   ├── page.tsx        ← bike detail
│   │   │   │   └── edit/
│   │   │   │       └── page.tsx    ← edit form
│   │   │   └── new/
│   │   │       └── page.tsx        ← create form
│   │   └── pills/
│   │       └── page.tsx            ← pill management
│   ├── api/
│   │   ├── bikes/
│   │   │   ├── route.ts            ← GET (list), POST (create)
│   │   │   └── [id]/
│   │   │       ├── route.ts        ← GET, PATCH, DELETE
│   │   │       ├── pills/
│   │   │       │   └── route.ts    ← PUT (set pills)
│   │   │       ├── maintenance/
│   │   │       │   ├── route.ts    ← GET, POST
│   │   │       │   └── [recordId]/
│   │   │       │       └── route.ts ← PATCH, DELETE
│   │   │       └── images/
│   │   │           ├── route.ts    ← POST (upload)
│   │   │           └── [imageId]/
│   │   │               └── route.ts ← DELETE, PATCH
│   │   ├── images/
│   │   │   └── [...path]/
│   │   │       └── route.ts        ← serves uploaded images
│   │   └── pills/
│   │       ├── route.ts            ← GET, POST
│   │       └── [id]/
│   │           └── route.ts        ← DELETE
│   ├── db/
│   │   ├── schema.ts               ← Drizzle table definitions
│   │   ├── index.ts                ← DB connection + client
│   │   └── seed.ts                 ← dev seed data
│   ├── lib/
│   │   ├── image-store.ts          ← ImageStore interface + local impl
│   │   └── utils.ts
│   └── components/
│       ├── ui/                     ← shared primitives
│       │   ├── button.tsx
│       │   ├── input.tsx
│       │   ├── dialog.tsx
│       │   └── skeleton.tsx
│       ├── BikeCard.tsx
│       ├── BikeCardGrid.tsx
│       ├── BikeForm.tsx
│       ├── PillBadge.tsx
│       ├── PillSelector.tsx
│       ├── ImageGallery.tsx
│       ├── ImageUploadZone.tsx
│       ├── MaintenanceTimeline.tsx
│       ├── MaintenanceForm.tsx
│       └── ConfirmDialog.tsx
└── public/
    └── placeholder-bike.svg        ← fallback image
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

1. **JSON export** — One-click "export all data" as JSON. (SQLite makes the DB
   file easy to copy manually, but a structured JSON export would be more
   portable.)

2. **Search & text/pill filter** — Full-text search across bike names and
   descriptions, plus filtering by attached pills on the home page.

3. **Maintenance reminders** — Surface upcoming or past-due maintenance based on
   mileage or time intervals (e.g. "chain lube due in 100 miles"). Requires
   mileage tracking and interval configuration.

4. **Authentication** — Basic Auth or NextAuth single-user provider, needed
   only if the app is later exposed to the internet.
