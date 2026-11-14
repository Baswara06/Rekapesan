import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AppProvider } from "../lib/store";
import MasukkanChat from "./MasukkanChat";

const pratinjau = {
  penjual: "Ratri",
  tanggal_awal: "2026-11-14",
  tanggal_akhir: "2026-11-15",
  jumlah_pesan: 19,
  hari: [
    { tanggal: "2026-11-14", jumlah_pesan: 15 },
    { tanggal: "2026-11-15", jumlah_pesan: 4 },
  ],
  menu: [
    { nama: "Nasi Ayam Bawang Putih", harga: 17000, sudah_ada: false, product_id: null },
    { nama: "Es Teh", harga: 5000, sudah_ada: true, product_id: "p-es" },
  ],
};

const hasilImpor = {
  hari: [
    { tanggal: "2026-11-14", batch_id: "b1", nama: "Sabtu, 14 Nov", pesan_baru: 15, pesan_dilewati: 0, pesanan_dibuat: 7, pesanan_diubah: 0, perlu_cek: 3 },
  ],
  total: { pesan_baru: 15, pesan_dilewati: 0, pesanan_dibuat: 7, pesanan_diubah: 0, perlu_cek: 3 },
};

let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    const ok = (body: unknown) => ({ ok: true, status: 200, json: async () => body });
    const metode = init?.method ?? "GET";
    if (url.endsWith("/api/impor/pratinjau") && metode === "POST") return ok(pratinjau);
    if (url.endsWith("/api/impor") && metode === "POST") return ok(hasilImpor);
    if (url.endsWith("/api/products") && metode === "POST") return ok({ id: "p-baru", ...JSON.parse(String(init?.body)) });
    if (url.endsWith("/api/products")) return ok([]);
    if (url.endsWith("/api/batches")) return ok([]);
    return { ok: false, status: 404, json: async () => null };
  });
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const panggilan = (metode: string, akhir: string) =>
  fetchMock.mock.calls.filter(([u, init]) => (init?.method ?? "GET") === metode && String(u).endsWith(akhir));

describe("wizard Masukkan chat", () => {
  it("pratinjau, lalu simpan menu hanya untuk menu baru, lalu proses impor harian", async () => {
    render(
      <AppProvider>
        <MasukkanChat />
      </AppProvider>,
    );
    expect(screen.getByText("Langkah 1 dari 3: Masukkan chat")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Tempel chat grup di sini"), {
      target: { value: "14/11/26 09.15 - Bu Rina: nasi ayam 2" },
    });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Lanjut" }));
    });

    await screen.findByText("Yang terbaca dari chat");
    expect(screen.getByText("Ratri")).toBeTruthy();
    expect(screen.getByText("Sudah di Katalog")).toBeTruthy();
    const pratinjauBody = JSON.parse(String(panggilan("POST", "/api/impor/pratinjau")[0][1].body));
    expect(pratinjauBody).toEqual({ text: "14/11/26 09.15 - Bu Rina: nasi ayam 2" });

    // Penjual mengoreksi harga menu baru sebelum disimpan.
    fireEvent.change(screen.getByLabelText("Harga (Rp) untuk Nasi Ayam Bawang Putih"), { target: { value: "18000" } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Simpan 1 menu baru" }));
    });

    await screen.findByRole("button", { name: "Proses chat" });
    const simpan = panggilan("POST", "/api/products");
    expect(simpan).toHaveLength(1);
    expect(JSON.parse(String(simpan[0][1].body))).toMatchObject({ nama: "Nasi Ayam Bawang Putih", harga: 18000, aktif: true });

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Proses chat" }));
    });
    await screen.findByText("Chat berhasil dibaca");
    expect(panggilan("POST", "/api/impor")).toHaveLength(1);
    expect(screen.getByText("Sabtu, 14 Nov")).toBeTruthy();
    await waitFor(() => expect(screen.getByRole("button", { name: "Lihat papan pesanan" })).toBeTruthy());
  });

  it("katalog kosong saat proses menampilkan tombol Buka Katalog", async () => {
    fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
      const ok = (body: unknown) => ({ ok: true, status: 200, json: async () => body });
      if (url.endsWith("/api/impor/pratinjau")) return ok({ ...pratinjau, menu: [] });
      if (url.endsWith("/api/impor") && init?.method === "POST")
        return { ok: false, status: 409, json: async () => ({ error: { kode: "katalog_kosong", pesan: "Isi menu dulu." } }) };
      return ok([]);
    });
    render(
      <AppProvider>
        <MasukkanChat />
      </AppProvider>,
    );
    fireEvent.change(screen.getByLabelText("Tempel chat grup di sini"), { target: { value: "chat" } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Lanjut" }));
    });
    // Menu kosong tidak membuat buntu: penjual bisa menambah menu atau lanjut.
    expect(await screen.findByRole("button", { name: "Tambah menu" })).toBeTruthy();
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Menu sudah benar, lanjut" }));
    });
    expect(panggilan("POST", "/api/products")).toHaveLength(0);
    await act(async () => {
      fireEvent.click(await screen.findByRole("button", { name: "Proses chat" }));
    });
    expect(await screen.findByRole("link", { name: "Buka Katalog" })).toBeTruthy();
  });
});
