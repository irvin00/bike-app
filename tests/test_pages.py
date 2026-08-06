"""Page-route smoke tests: every page renders 200 with its key content."""

from fixtures import (
    client,
    image_bytes,
    seeded_client,
    tmp_db_path,
    uploads_dir,
)


async def test_home_empty(client):
    r = await client.get("/")
    assert r.status_code == 200
    assert "No bikes yet" in r.text


async def test_home_seeded(seeded_client):
    r = await seeded_client.get("/")
    assert r.status_code == 200
    assert "S-Works Tarmac SL8" in r.text
    assert "Surly Steamroller" in r.text


async def test_pills_page(seeded_client):
    r = await seeded_client.get("/pills")
    assert r.status_code == 200
    assert "Carbon Frame" in r.text


async def test_bike_new(client):
    r = await client.get("/bikes/new")
    assert r.status_code == 200
    assert "Add New Bike" in r.text
    assert 'data-bike-id' not in r.text  # create mode, no bike id


async def test_bike_detail(seeded_client):
    r = await seeded_client.get("/bikes/1")
    assert r.status_code == 200
    assert "S-Works Tarmac SL8" in r.text
    assert "Maintenance History" in r.text


async def test_bike_edit(seeded_client):
    r = await seeded_client.get("/bikes/1/edit")
    assert r.status_code == 200
    assert "Save Changes" in r.text
    assert 'data-bike-id="1"' in r.text


async def test_bike_detail_404(client):
    r = await client.get("/bikes/999")
    assert r.status_code == 404


async def test_settings_data_page(client):
    r = await client.get("/settings/data")
    assert r.status_code == 200
    assert "Import" in r.text
    assert 'href="/api/export"' in r.text
    assert "settings-data.js" in r.text


async def test_settings_drawer_present(client):
    # Base-level inclusion: the gear button + drawer + its script are on
    # every page that extends base.html.j2.
    for path in ("/", "/pills"):
        r = await client.get(path)
        assert r.status_code == 200
        assert 'id="settings-drawer"' in r.text
        assert 'id="settings-open-btn"' in r.text
        assert "settings-drawer.js" in r.text
        assert "image-fallback.js" in r.text

