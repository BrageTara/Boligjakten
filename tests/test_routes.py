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


def test_kart_returns_200(seeded_client):
    response = seeded_client.get("/kart")
    assert response.status_code == 200
    assert b"map" in response.data


def test_kart_markers_returns_json(seeded_client):
    response = seeded_client.post("/kart/markers", data={})
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    finnkoder = {row["finnkode"] for row in data}
    # 333 has NULL coords so it's excluded
    assert "333" not in finnkoder
    assert {"111", "222"}.issubset(finnkoder)


def test_kart_markers_applies_filter(seeded_client):
    response = seeded_client.post(
        "/kart/markers", data={"prisantydning_maks": "3 000 000"}
    )
    assert response.status_code == 200
    finnkoder = {row["finnkode"] for row in response.get_json()}
    assert finnkoder == {"111"}
