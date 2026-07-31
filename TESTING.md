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

## Stop the server

Press `Ctrl+C` in the server terminal.
