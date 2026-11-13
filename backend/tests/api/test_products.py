def test_buat_dan_daftar_menu_dengan_alias_dibersihkan(client):
    res = client.post(
        "/api/products",
        json={
            "nama": "  Nasi Lodeh ",
            "alias": ["lodeh", " Lodeh ", "", "nasilodeh"],
            "harga": 15000,
            "stok_harian": 10,
            "resep": [{"bahan": "beras", "jumlah": 0.1, "satuan": "kg"}],
        },
    )
    assert res.status_code == 201
    p = res.json()
    assert p["nama"] == "Nasi Lodeh" and p["alias"] == ["lodeh", "nasilodeh"] and p["aktif"] is True
    assert p["resep"] == [{"bahan": "beras", "jumlah": 0.1, "satuan": "kg"}]
    assert [x["id"] for x in client.get("/api/products").json()] == [p["id"]]


def test_ubah_sebagian_stok_null_berarti_tak_terbatas_dan_resep_diganti(client, katalog):
    res = client.patch("/api/products/p-ayam", json={"harga": 20000, "stok_harian": None})
    assert res.status_code == 200
    p = res.json()
    assert p["harga"] == 20000 and p["stok_harian"] is None and p["nama"] == "Ayam Bakar"
    assert len(p["resep"]) == 2  # resep tidak disentuh bila tidak dikirim

    p = client.patch("/api/products/p-ayam", json={"resep": [{"bahan": "ayam", "jumlah": 0.3, "satuan": "kg"}]}).json()
    assert p["resep"] == [{"bahan": "ayam", "jumlah": 0.3, "satuan": "kg"}]
    assert p["stok_harian"] is None  # tidak ikut berubah


def test_nonaktifkan_tidak_menghapus_dan_bisa_disaring(client, katalog):
    res = client.delete("/api/products/p-teh")
    assert res.status_code == 200 and res.json()["aktif"] is False
    aktif = {p["id"] for p in client.get("/api/products", params={"aktif": "true"}).json()}
    assert aktif == {"p-ayam", "p-lodeh"}
    assert len(client.get("/api/products").json()) == 3


def test_galat_seragam_menu(client):
    res = client.patch("/api/products/tidak-ada", json={"harga": 1})
    assert res.status_code == 404 and res.json()["error"]["kode"] == "tidak_ditemukan"
    res = client.post("/api/products", json={"nama": "X", "harga": -5})
    assert res.status_code == 422 and res.json()["error"]["kode"] == "validasi_gagal"
    res = client.post("/api/products", json={"harga": 5})
    assert res.status_code == 422 and "nama" in res.json()["error"]["pesan"]
