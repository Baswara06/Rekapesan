import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, aturSaatTidakTerautentikasi, cekKesehatan, simpanToken } from "./api";

function balas(status: number, body: unknown) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

afterEach(() => {
  simpanToken(null);
  vi.unstubAllGlobals();
});

describe("klien API", () => {
  it("mengembalikan status ok dari backend", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(balas(200, { status: "ok" })));
    await expect(cekKesehatan()).resolves.toEqual({ status: "ok" });
  });

  it("mengirim token Bearer setelah login", async () => {
    const fetch = vi.fn().mockResolvedValue(balas(200, []));
    vi.stubGlobal("fetch", fetch);
    simpanToken("abc");
    await api.daftarBatch();
    const headers = fetch.mock.calls[0][1].headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer abc");
  });

  it("membaca galat seragam dari server", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(balas(429, { error: { kode: "kuota_llm_habis", pesan: "Kuota model habis." } })),
    );
    const err = await api.imporTeks("b1", "x").catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.kode).toBe("kuota_llm_habis");
    expect(err.status).toBe(429);
    expect(err.message).toBe("Kuota model habis.");
  });

  it("token kedaluwarsa menghapus token dan memanggil penangan 401", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(balas(401, { error: { kode: "tidak_terautentikasi", pesan: "x" } })));
    const penangan = vi.fn();
    aturSaatTidakTerautentikasi(penangan);
    simpanToken("lama");
    await api.daftarBatch().catch(() => undefined);
    expect(penangan).toHaveBeenCalledOnce();
    expect(localStorage.getItem("rekapesan.token")).toBeNull();
  });

  it("login gagal tidak memicu penangan sesi berakhir", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(balas(401, { error: { kode: "tidak_terautentikasi", pesan: "Salah." } })));
    const penangan = vi.fn();
    aturSaatTidakTerautentikasi(penangan);
    await expect(api.login("demo", "salah")).rejects.toThrow("Salah.");
    expect(penangan).not.toHaveBeenCalled();
  });

  it("jaringan putus menjadi galat yang bisa dibaca penjual", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    const err = await api.daftarBatch().catch((e) => e);
    expect(err.kode).toBe("jaringan");
    expect(err.message).toMatch(/Tidak tersambung/);
  });

  it("hapus batch menerima 204 tanpa isi", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 204, json: async () => { throw new Error("tanpa isi"); } }));
    await expect(api.hapusBatch("b1")).resolves.toBeUndefined();
  });

  it("impor teks dikirim sebagai JSON {text}", async () => {
    const fetch = vi.fn().mockResolvedValue(balas(200, { pesan_baru: 1, pesan_dilewati: 0, pesanan_dibuat: 1, pesanan_diubah: 0, perlu_cek: 0 }));
    vi.stubGlobal("fetch", fetch);
    await api.imporTeks("b1", "halo");
    const [url, init] = fetch.mock.calls[0];
    expect(url).toBe("/api/batches/b1/import");
    expect(JSON.parse(init.body)).toEqual({ text: "halo" });
  });
});
