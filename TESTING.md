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

## Stop the server

Press `Ctrl+C` in the server terminal.
