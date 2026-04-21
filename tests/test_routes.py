def test_index_returns_200(seeded_client):
    response = seeded_client.get("/")
    assert response.status_code == 200


def test_index_shows_listing_count(seeded_client):
    response = seeded_client.get("/")
    assert b"3" in response.data


def test_annonser_post_returns_200(seeded_client):
    response = seeded_client.post("/annonser", data={})
    assert response.status_code == 200


def test_detalj_returns_200_for_known(seeded_client):
    response = seeded_client.get("/annonse/111")
    assert response.status_code == 200
    assert "Møllenberggata".encode() in response.data


def test_detalj_returns_404_for_unknown(seeded_client):
    response = seeded_client.get("/annonse/does-not-exist")
    assert response.status_code == 404


def test_solgte_returns_200(seeded_client):
    response = seeded_client.get("/solgte")
    assert response.status_code == 200


def test_prishistorikk_returns_200(seeded_client):
    response = seeded_client.get("/prishistorikk")
    assert response.status_code == 200
