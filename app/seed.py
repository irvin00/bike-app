import aiosqlite
from app.db import DB_PATH, init_db

SEED_SQL = """
-- Pills
INSERT OR IGNORE INTO pills (id, label, color) VALUES (1, 'Carbon Frame', '#1e40af');
INSERT OR IGNORE INTO pills (id, label, color) VALUES (2, 'Titanium', '#9ca3af');
INSERT OR IGNORE INTO pills (id, label, color) VALUES (3, 'Singlespeed', '#d97706');
INSERT OR IGNORE INTO pills (id, label, color) VALUES (4, 'Disc Brakes', '#dc2626');
INSERT OR IGNORE INTO pills (id, label, color) VALUES (5, 'Gravel Bike', '#059669');

-- Bikes
INSERT OR IGNORE INTO bikes (id, name, description, full_story, status, acquired_on)
VALUES (
    1,
    'S-Works Tarmac SL8',
    'Carbon race bike — my main road rig.',
    'Built this up from a frameset in spring 2024. SRAM Red AXS group, Roval CLX II wheels, 6.8 kg ready to ride. Used for weekend group rides and the occasional crit.',
    'active',
    '2024-03-15'
);

INSERT OR IGNORE INTO bikes (id, name, description, full_story, status, acquired_on, retired_on)
VALUES (
    2,
    'Surly Steamroller',
    'Fixed-gear commuter. Bombproof.',
    'Bought used in 2020. Put thousands of city miles on this thing. Stripped it down to just a front brake. Retired it when I moved out of the city — kept the frame for nostalgia.',
    'former',
    '2020-06-01',
    '2025-01-10'
);

-- Bike <-> Pill joins
INSERT OR IGNORE INTO bike_pills (bike_id, pill_id) VALUES (1, 1);
INSERT OR IGNORE INTO bike_pills (bike_id, pill_id) VALUES (1, 4);
INSERT OR IGNORE INTO bike_pills (bike_id, pill_id) VALUES (2, 3);

-- Maintenance records
INSERT OR IGNORE INTO maintenance_records (id, bike_id, date, description, cost)
VALUES (1, 1, '2024-06-15', 'Full drivetrain clean and wax', 0);

INSERT OR IGNORE INTO maintenance_records (id, bike_id, date, description, cost)
VALUES (2, 1, '2025-01-03', 'New brake pads (front + rear)', 85.00);

INSERT OR IGNORE INTO maintenance_records (id, bike_id, date, description, cost)
VALUES (3, 2, '2022-08-20', 'Replaced chain', 25.00);

INSERT OR IGNORE INTO maintenance_records (id, bike_id, date, description, cost)
VALUES (4, 2, '2023-05-10', 'New front tire after glass puncture', 60.00);

-- Images
INSERT OR IGNORE INTO images (id, bike_id, filename, original_name, is_primary, sort_order)
VALUES (1, 1, 'carbon-race-bike.jpg', 'carbon-race-bike.jpg', 1, 0);

INSERT OR IGNORE INTO images (id, bike_id, filename, original_name, is_primary, sort_order)
VALUES (2, 2, 'fixie-bike.jpg', 'fixie-bike.jpg', 1, 0);
"""


async def run_seed(db: aiosqlite.Connection) -> None:
    await db.executescript(SEED_SQL)
    await db.commit()


async def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await init_db(db)
        await run_seed(db)
    print(f"Seeded database at {DB_PATH}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
