# Bike View — API Test Instructions

## Prerequisites

```bash
cd /Users/irvinsamuel/Desktop/bike_view
```

## Reset the database (optional — for a clean slate)

```bash
rm data/bike_view.db
uv run python -m app.seed
```

## Start the server

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal window, run the tests below.

---

## 1. List all bikes

```bash
curl -s http://127.0.0.1:8000/api/bikes```

**Expected:** 2 bikes returned, each with a `pills` array.

---

## 2. Filter by status

```bash
# Active only
curl -s "http://127.0.0.1:8000/api/bikes?status=active"
# Former only
curl -s "http://127.0.0.1:8000/api/bikes?status=former"```

**Expected:** Active returns 1 bike (S-Works Tarmac). Former returns 1 bike (Surly Steamroller).

---

## 3. Get a single bike

```bash
curl -s http://127.0.0.1:8000/api/bikes/1```

**Expected:** Full bike object with pills attached (Carbon Frame, Disc Brakes).

---

## 4. Create a bike

```bash
curl -s -X POST http://127.0.0.1:8000/api/bikes \
  -H "Content-Type: application/json" \
  -d '{"name":"Bianchi Pista","description":"Track bike","full_story":"Built for the velodrome.","status":"active"}' \
 ```

**Expected:** 201 Created. Bike returned with a new `id` and empty `pills` array.

---

## 5. Update a bike (partial)

```bash
curl -s -X PATCH http://127.0.0.1:8000/api/bikes/1 \
  -H "Content-Type: application/json" \
  -d '{"description":"Updated description"}' \
 ```

**Expected:** 200 OK. Bike returned with updated `description`, all other fields unchanged.

---

## 6. Delete a bike

```bash
# Delete the bike we just created (check its id first)
curl -s -X DELETE http://127.0.0.1:8000/api/bikes/3 -w "\nHTTP %{http_code}\n"
```

**Expected:** HTTP 204 (no body). If the bike doesn't exist, HTTP 404 with `{"detail":"Bike not found"}`.

---

## 7. Verify deletion

```bash
curl -s http://127.0.0.1:8000/api/bikes/3
```

**Expected:** HTTP 404 — `{"detail":"Bike not found"}`.

---

## 8. Error: missing required field

```bash
curl -s -X POST http://127.0.0.1:8000/api/bikes \
  -H "Content-Type: application/json" \
  -d '{"description":"Forgot the name"}' \
 ```

**Expected:** 422 Unprocessable Entity with validation error for `name`.

---

## 9. List all pills

```bash
curl -s http://127.0.0.1:8000/api/pills
```

**Expected:** 5 seeded pills, each with `id`, `label`, `color`, ordered by label.

---

## 10. Create a pill

```bash
curl -s -X POST http://127.0.0.1:8000/api/pills \
  -H "Content-Type: application/json" \
  -d '{"label":"Steel Frame","color":"#b45309"}' \
  -w "\nHTTP %{http_code}\n"
```

**Expected:** HTTP 201. Pill returned with `id`, `label: "Steel Frame"`, `color: "#b45309"`.
(Note the new pill's id — e.g. 6 — for section 12.)

---

## 11. Error: duplicate label

```bash
curl -s -X POST http://127.0.0.1:8000/api/pills \
  -H "Content-Type: application/json" \
  -d '{"label":"Steel Frame","color":"#b45309"}' \
  -w "\nHTTP %{http_code}\n"
```

**Expected:** HTTP 409 with `{"detail":"A pill with this label already exists"}`.

---

## 12. Delete a pill (and verify cascade)

```bash
# Attach the pill to bike 1, then delete the pill
curl -s -X PUT http://127.0.0.1:8000/api/bikes/1/pills \
  -H "Content-Type: application/json" \
  -d '{"pill_ids":[1,4,6]}'
curl -s -X DELETE http://127.0.0.1:8000/api/pills/6 -w "\nHTTP %{http_code}\n"
curl -s http://127.0.0.1:8000/api/bikes/1
# Delete it again (should be gone)
curl -s -X DELETE http://127.0.0.1:8000/api/pills/6 -w "\nHTTP %{http_code}\n"
```

**Expected:** PUT returns 3 pills. DELETE returns HTTP 204 (no body). Bike 1's `pills` array is back to Carbon Frame + Disc Brakes — the cascade removed the attachment. Deleting again returns HTTP 404 with `{"detail":"Pill not found"}`.

---

## 13. Error: empty label

```bash
curl -s -X POST http://127.0.0.1:8000/api/pills \
  -H "Content-Type: application/json" \
  -d '{"label":"   "}' \
  -w "\nHTTP %{http_code}\n"
```

**Expected:** HTTP 422 with `{"detail":"Label is required"}`.

---

## 14. Pills page (UI)

```bash
open http://127.0.0.1:8000/pills
```

1. The nav bar "Pills" button loads the page; all 5 seeded pills are listed with color swatches.
2. Add a pill via the form (e.g. "Steel Frame", pick a color) — it appears in the list in alphabetical position, and the form clears.
3. Add the same label again — an alert appears (client-side guard or server 409 message); nothing is added.
4. Click Delete on a row — a confirm dialog appears; the row disappears; deleting an attached pill also removes its badge from bikes.

---

## 15. Home page status filter (UI)

```bash
# All (no filter) — shows both bikes
curl -s http://127.0.0.1:8000/
# Active only
curl -s "http://127.0.0.1:8000/?status=active"
# Former only
curl -s "http://127.0.0.1:8000/?status=former"
# Invalid status — falls back to showing all
curl -s "http://127.0.0.1:8000/?status=bogus"
```

**Expected:** `/` lists both S-Works Tarmac SL8 and Surly Steamroller; `?status=active` lists only S-Works Tarmac SL8; `?status=former` lists only Surly Steamroller; `?status=bogus` lists both (invalid value ignored, like `/api/bikes`).

```bash
curl -s http://127.0.0.1:8000/ | grep -c 'class="bike-card"'
curl -s "http://127.0.0.1:8000/?status=active" | grep -c 'class="bike-card"'
curl -s "http://127.0.0.1:8000/?status=former" | grep -c 'class="bike-card"'
```

**Expected:** `2`, `1`, `1` (one `<article class="bike-card" ...>` per grid card).

```bash
curl -s http://127.0.0.1:8000/ | grep 'status-filter__btn'
curl -s "http://127.0.0.1:8000/?status=active" | grep 'status-filter__btn'
curl -s "http://127.0.0.1:8000/?status=former" | grep 'status-filter__btn'
```

**Expected:** exactly one link carries `active` in each output — "All", "Active", "Former" respectively.

```bash
# Filter is hidden on non-home pages
curl -s http://127.0.0.1:8000/pills | grep -c 'status-filter'
curl -s http://127.0.0.1:8000/bikes/new | grep -c 'status-filter'
```

**Expected:** `0`, `0`.

```bash
open http://127.0.0.1:8000/
```

1. Both bikes shown; "All" is highlighted; "Active" and "Former" are not.
2. Click "Active" — grid shows only S-Works Tarmac SL8; "Active" highlighted.
3. Click "Former" — grid shows only Surly Steamroller; "Former" highlighted.
4. Browser Back returns to active-only, then to all (state lives in the URL).
5. With an empty DB: unfiltered shows "No bikes yet. Add your first one."; Active shows "No active bikes."; Former shows "No former bikes."

---

## 16. Image upload, primary, reorder, delete

```bash
# Upload an image to bike 1 (seed bike — already has the seeded
# carbon-race-bike.jpg as primary, so the new one is NOT primary)
curl -s -X POST http://127.0.0.1:8000/api/bikes/1/images \
  -F "files=@static/img/fixie-bike.jpg" \
  -w "\nHTTP %{http_code}\n"
```

**Expected:** HTTP 201 with an array containing one image object — `id`, `filename` (UUID-prefixed), `original_name: "fixie-bike.jpg"`, `is_primary: 0`, `sort_order: 1`, plus `url` and `thumb_url`. Note the `id` and `filename` for later steps.

```bash
# First upload to a bike with no images becomes primary
curl -s -X POST http://127.0.0.1:8000/api/bikes \
  -H "Content-Type: application/json" \
  -d '{"name":"Fresh Bike"}'   # note the new id
curl -s -X POST http://127.0.0.1:8000/api/bikes/<new_id>/images \
  -F "files=@static/img/fixie-bike.jpg"
```

**Expected:** 201; the new bike's first image has `is_primary: 1` and `sort_order: 0`.

```bash
# The stored files: full-size + thumbnail
ls uploads/bikes/1/
```

**Expected:** two files — `<uuid>-fixie-bike.jpg` and `<uuid>-fixie-bike.thumb.jpg`.

```bash
# Thumbnail is ≤400px on the long edge
sips -g pixelWidth -g pixelHeight uploads/bikes/1/<uuid>-fixie-bike.thumb.jpg
```

**Expected:** both dimensions ≤ 400.

```bash
# Upload a second image — sort_order increments, primary unchanged
curl -s -X POST http://127.0.0.1:8000/api/bikes/1/images \
  -F "files=@static/img/carbon-race-bike.jpg"
```

**Expected:** new image with `is_primary: 0` and `sort_order: 1`.

```bash
# Non-image file is rejected (nothing written)
curl -s -X POST http://127.0.0.1:8000/api/bikes/1/images \
  -F "files=@pyproject.toml" -w "\nHTTP %{http_code}\n"
```

**Expected:** HTTP 400 with `{"detail":"pyproject.toml: not an image file"}`.

```bash
# Unknown bike → 404
curl -s -X POST http://127.0.0.1:8000/api/bikes/999/images \
  -F "files=@static/img/fixie-bike.jpg" -w "\nHTTP %{http_code}\n"
```

**Expected:** HTTP 404 `{"detail":"Bike not found"}`.

```bash
# Swap primary to the second image (replace <id2> with its id)
curl -s -X PATCH http://127.0.0.1:8000/api/bikes/1/images/<id2> \
  -H "Content-Type: application/json" \
  -d '{"is_primary":true}'
# Verify exactly one primary per bike
curl -s http://127.0.0.1:8000/api/bikes/1 | grep -o '"is_primary":1' | wc -l
```

**Expected:** PATCH returns the updated image with `is_primary: 1`; the count of `"is_primary":1` in the bike JSON is `1`.

```bash
# Reorder: set image 1's sort_order to 5, verify ordering reflects it
curl -s -X PATCH http://127.0.0.1:8000/api/bikes/1/images/<id1> \
  -H "Content-Type: application/json" \
  -d '{"sort_order":5}'
curl -s http://127.0.0.1:8000/api/bikes/1 | grep -o '"sort_order":[0-9]*'
```

**Expected:** PATCH returns `sort_order: 5`; the bike's `images` array lists `sort_order` 0 (image 2) before 5 (image 1).

```bash
# Delete an image — 204, files removed, primary promoted if needed
curl -s -X DELETE http://127.0.0.1:8000/api/bikes/1/images/<id> -w "\nHTTP %{http_code}\n"
ls uploads/bikes/1/
curl -s http://127.0.0.1:8000/api/bikes/1
```

**Expected:** HTTP 204 (no body). If the deleted image was primary, the remaining image now has `is_primary: 1`. Both files (`<name>.jpg` and `<name>.thumb.jpg`) are gone from `uploads/bikes/1/`.

```bash
# 404s: unknown image
curl -s -X DELETE http://127.0.0.1:8000/api/bikes/1/images/9999 -w "\nHTTP %{http_code}\n"
curl -s -X PATCH http://127.0.0.1:8000/api/bikes/1/images/9999 \
  -H "Content-Type: application/json" -d '{"is_primary":true}' -w "\nHTTP %{http_code}\n"
```

**Expected:** both HTTP 404 with `{"detail":"Image not found"}`.

```bash
# Thumb fallback: seed bike 1 has no .thumb.jpg on disk — still serves
curl -s -o /dev/null -w "%{http_code}\n" \
  http://127.0.0.1:8000/api/images/1/carbon-race-bike.thumb.jpg
```

**Expected:** `200` (serves the full-size `carbon-race-bike.jpg` as a fallback). Note: use GET, not `curl -I` — the route doesn't support HEAD.

```bash
# Traversal attempts are rejected
curl -s http://127.0.0.1:8000/api/images/1/..%2F..%2Fapp%2Fmain.py -w "\nHTTP %{http_code}\n"
curl -s http://127.0.0.1:8000/api/images/1/..%2Fdb.py -w "\nHTTP %{http_code}\n"
```

**Expected:** HTTP 404 for both.

```bash
# API responses now carry images
curl -s http://127.0.0.1:8000/api/bikes/1 | grep -o '"images":\['
curl -s http://127.0.0.1:8000/api/bikes | grep -o '"primary_thumb":"[^"]*"' | head -1
```

**Expected:** `GET /api/bikes/1` includes an `images` array (with `url`/`thumb_url` per image); `GET /api/bikes` items include `primary_image` and `primary_thumb`.

```bash
# Deleting a bike removes its upload directory
# Create a temp bike, note its id, upload an image to it, then:
curl -s -X DELETE http://127.0.0.1:8000/api/bikes/<new_id> -w "\nHTTP %{http_code}\n"
ls uploads/bikes/
```

**Expected:** HTTP 204; `uploads/bikes/<new_id>/` no longer exists.

**Browser steps:**

```bash
open http://127.0.0.1:8000/bikes/1/edit
```

1. The Images field shows the upload zone ("Drag & drop images here, or click to browse") above a list of existing rows.
2. Drag an image file onto the zone — the border highlights while hovering; on drop a new row appears (thumb, star, delete) with no page reload.
3. Click the zone — a file picker opens (multiple); picking files uploads them the same way.
4. Click the ☆ on a row — it becomes a gold ★ and the previous primary's star resets to ☆.
5. Drag a row by its ⇕ handle to reorder — the order sticks after reloading the page.
6. Click × on a row — confirm dialog; the row disappears; if it was primary, the first remaining row gets starred.
7. `open http://127.0.0.1:8000/bikes/new` — the create form shows "Add photos after saving — use Edit on the bike's page." instead of the upload zone.
8. Home page + bike detail: seed bikes render their images (thumb fallback); the home card uses the thumbnail, the gallery opens full-size on click.

---

## 17. Delete a bike (home grid + detail page)

```bash
open http://127.0.0.1:8000/
```

1. Click the × on a bike card — a confirm dialog appears naming the bike and noting that photos + maintenance history are removed too.
2. Confirm — the card disappears from the grid with no page reload. Cancel — the card stays.
3. Delete the last bike — the empty state appears ("No bikes yet. Add your first one." on `/`; the matching copy under `?status=active` / `?status=former`).
4. On the detail page (`/bikes/<id>`): "Edit Bike" is now joined by a red "Delete Bike" button. Click it — confirm dialog → redirected to `/` and the bike is gone from the grid.

```bash
# Cascade + file cleanup: create a temp bike, upload a photo, delete it
curl -s -X POST http://127.0.0.1:8000/api/bikes \
  -H "Content-Type: application/json" \
  -d '{"name":"Temp Bike"}'   # note the id
curl -s -X POST http://127.0.0.1:8000/api/bikes/<id>/images \
  -F "files=@static/img/fixie-bike.jpg"
ls uploads/bikes/<id>/
curl -s -X DELETE http://127.0.0.1:8000/api/bikes/<id> -w "\nHTTP %{http_code}\n"
curl -s http://127.0.0.1:8000/api/bikes/<id>
ls uploads/bikes/<id>/
```

**Expected:** images upload (files on disk under `uploads/bikes/<id>/`); DELETE returns HTTP 204; GET returns 404 `{"detail":"Bike not found"}`; `uploads/bikes/<id>/` no longer exists (Phase 6 cleanup).

```bash
# Error path: delete an id that no longer exists
curl -s -X DELETE http://127.0.0.1:8000/api/bikes/999 -w "\nHTTP %{http_code}\n"
```

**Expected:** HTTP 404 `{"detail":"Bike not found"}` — the UI surfaces this in the alert if a bike was already deleted in another tab.

---

## Stop the server

Press `Ctrl+C` in the server terminal.
