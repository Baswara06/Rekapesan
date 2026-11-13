from tests.api.conftest import id_pesanan


def test_daftar_detail_dan_saring_status(client, pesanan_contoh):
    semua = client.get("/api/batches/b-1/orders").json()
    assert sorted(o["customer"]["nama_tampil"] for o in semua) == ["Bu Rina", "Mas Budi", "Pak Anton"]
    assert {o["status"] for o in semua} == {"perlu_cek"}
    assert client.get("/api/batches/b-1/orders", params={"status": "dibayar"}).json() == []

    rina = client.get(f"/api/orders/{id_pesanan(client, 'Bu Rina')}").json()
    assert rina["total"] == 54000 and rina["tanda"] == ["jam_kosong"] and rina["alamat"] == "Blok C no 4"
    assert rina["items"][0]["harga_satuan"] == 18000 and rina["items"][0]["qty"] == 3
    assert [m["pengirim"] for m in rina["pesan_sumber"]] == ["Bu Rina", "Bu Rina"]


def test_galat_daftar_dan_detail(client, pesanan_contoh):
    assert client.get("/api/batches/tidak-ada/orders").json()["error"]["kode"] == "tidak_ditemukan"
    assert client.get("/api/orders/tidak-ada").status_code == 404
    res = client.get("/api/batches/b-1/orders", params={"status": "ngawur"})
    assert res.status_code == 422 and res.json()["error"]["kode"] == "validasi_gagal"


def test_ubah_item_harga_dan_total_dihitung_server_bukan_klien(client, pesanan_contoh):
    oid = id_pesanan(client, "Bu Rina")
    res = client.patch(
        f"/api/orders/{oid}",
        json={"items": [{"product_id": "p-lodeh", "teks_asli": "lodeh", "qty": 2, "harga_satuan": 1}], "total": 1},
    )
    assert res.status_code == 200
    o = res.json()
    assert o["items"][0]["harga_satuan"] == 15000  # harga dari katalog, kiriman klien diabaikan
    assert o["total"] == 30000
    assert o["tanda"] == ["jam_kosong"]  # jam masih kosong, item sudah beres


def test_ubah_item_tak_dikenal_atau_jumlah_kosong_diberi_tanda(client, pesanan_contoh):
    oid = id_pesanan(client, "Bu Rina")
    o = client.patch(
        f"/api/orders/{oid}",
        json={
            "items": [
                {"product_id": "id-karangan", "teks_asli": "rendang", "qty": 1},
                {"product_id": "p-teh", "teks_asli": "es teh"},
            ]
        },
    ).json()
    assert o["items"][0]["product_id"] is None and o["items"][0]["harga_satuan"] is None
    assert "item_tidak_dikenal" in o["tanda"] and "jumlah_kosong" in o["tanda"]
    assert o["total"] == 0


def test_ubah_jam_alamat_catatan_membersihkan_tanda(client, pesanan_contoh):
    client.post(f"/api/orders/{id_pesanan(client, 'Mas Budi')}/reject")  # 500 ayam menghabiskan stok semua orang
    oid = id_pesanan(client, "Bu Rina")
    o = client.patch(f"/api/orders/{oid}", json={"jam_kirim": "jam 11.30", "catatan": " tanpa sambal "}).json()
    assert o["jam_kirim"] == "11:30" and o["catatan"] == "tanpa sambal" and o["tanda"] == []

    o = client.patch(f"/api/orders/{oid}", json={"jam_kirim": "", "alamat": None}).json()
    assert o["jam_kirim"] is None and o["alamat"] is None
    assert o["tanda"] == ["jam_kosong", "alamat_kosong"]

    res = client.patch(f"/api/orders/{oid}", json={"jam_kirim": "bukan jam"})
    assert res.status_code == 422 and res.json()["error"]["kode"] == "validasi_gagal"


def test_stok_dihitung_dari_pesanan_lain_saat_penjual_mengubah(client, pesanan_contoh):
    # Mas Budi sudah memesan 500 ayam bakar (stok 30). Menambah ayam ke Bu Rina tetap kena stok_kurang.
    oid = id_pesanan(client, "Bu Rina")
    o = client.patch(f"/api/orders/{oid}", json={"items": [{"product_id": "p-ayam", "teks_asli": "ayam", "qty": 1}]}).json()
    assert "stok_kurang" in o["tanda"]
    # Setelah Budi ditolak, stok tersedia lagi.
    client.post(f"/api/orders/{id_pesanan(client, 'Mas Budi')}/reject")
    o = client.patch(f"/api/orders/{oid}", json={"alamat": "Blok C"}).json()  # memicu hitung ulang
    assert "stok_kurang" not in o["tanda"]


def test_setujui_tolak_dan_aturan_status(client, pesanan_contoh):
    oid = id_pesanan(client, "Bu Rina")
    assert client.post(f"/api/orders/{oid}/approve").json()["status"] == "dikonfirmasi"
    assert client.post(f"/api/orders/{oid}/approve").json()["status"] == "dikonfirmasi"  # idempoten

    budi = id_pesanan(client, "Mas Budi")
    res = client.post(f"/api/orders/{budi}/reject")
    assert res.json()["status"] == "batal" and res.json()["tanda"] == []
    res = client.post(f"/api/orders/{budi}/approve")
    assert res.status_code == 409 and res.json()["error"]["kode"] == "validasi_gagal"

    client.post(f"/api/orders/{oid}/payment-confirm")
    res = client.post(f"/api/orders/{oid}/reject")
    assert res.status_code == 409  # sudah dibayar tidak bisa ditolak


def test_setujui_semua_yang_bersih_melewati_yang_bertanda(client, pesanan_contoh):
    client.post(f"/api/orders/{id_pesanan(client, 'Mas Budi')}/reject")
    rina = id_pesanan(client, "Bu Rina")
    client.patch(f"/api/orders/{rina}", json={"jam_kirim": "12:00"})  # Rina jadi tanpa tanda
    res = client.post("/api/batches/b-1/orders/approve-clean")
    assert res.json() == {"disetujui": 1, "masih_bertanda": 1}  # Pak Anton masih alamat_kosong
    status = {o["customer"]["nama_tampil"]: o["status"] for o in client.get("/api/batches/b-1/orders").json()}
    assert status == {"Bu Rina": "dikonfirmasi", "Pak Anton": "perlu_cek", "Mas Budi": "batal"}
    assert client.post("/api/batches/tidak-ada/orders/approve-clean").status_code == 404


def test_balasan_konfirmasi_hanya_setelah_disetujui(client, pesanan_contoh):
    oid = id_pesanan(client, "Bu Rina")
    res = client.get(f"/api/orders/{oid}/reply")
    assert res.status_code == 409 and res.json()["error"]["kode"] == "validasi_gagal"

    client.patch(f"/api/orders/{oid}", json={"jam_kirim": "12:00"})
    client.post(f"/api/orders/{oid}/approve")
    teks = client.get(f"/api/orders/{oid}/reply").json()["teks"]
    assert teks.splitlines() == [
        "Halo Bu Rina, pesanan kamu sudah kami catat ya:",
        "- 3 x Ayam Bakar = Rp54.000",
        "Total: Rp54.000",
        "Dikirim pukul 12.00 ke Blok C no 4.",
        "Terima kasih!",
    ]


def test_semua_endpoint_wajib_login(tamu, pesanan_contoh):
    for metode, url in [
        ("get", "/api/batches/b-1/orders"),
        ("get", "/api/orders/x"),
        ("patch", "/api/orders/x"),
        ("post", "/api/orders/x/approve"),
        ("post", "/api/orders/x/reject"),
        ("post", "/api/batches/b-1/orders/approve-clean"),
        ("get", "/api/orders/x/reply"),
        ("get", "/api/batches/b-1/recap"),
        ("get", "/api/batches/b-1/shopping-list"),
        ("post", "/api/orders/x/payment-confirm"),
        ("post", "/api/agent/ask"),
        ("delete", "/api/batches/b-1"),
        ("post", "/api/batches/b-1/import"),
        ("get", "/api/products"),
        ("get", "/api/batches"),
    ]:
        assert getattr(tamu, metode)(url).status_code == 401, (metode, url)
