import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Order } from "../lib/api";
import { simpanToken } from "../lib/api";
import { bacaRute } from "../lib/router";
import { AppProvider } from "../lib/store";
import Review from "./Review";

const batch = { id: "b1", nama: "PO Jumat", tanggal_kirim: "2026-11-13", tanggal_mulai: null, dibuat_pada: "2026-11-12T08:00:00" };
const menu = { id: "p1", nama: "Ayam Bakar", alias: ["aybak"], harga: 18000, stok_harian: 30, aktif: true, resep: [] };

function pesanan(id: string, nama: string, tanda: Order["tanda"]): Order {
  return {
    id,
    batch_id: "b1",
    customer: { id: `c-${id}`, nama_tampil: nama },
    status: "perlu_cek",
    jam_kirim: tanda.includes("jam_kosong") ? null : "12:00",
    alamat: "Blok C",
    catatan: null,
    items: [{ id: `i-${id}`, product_id: "p1", teks_asli: "ayam bakar 2", qty: 2, harga_satuan: 18000, catatan_item: null }],
    total: 36000,
    tanda,
    perubahan: { sebelum: null, sesudah: null },
    pesan_sumber: [{ id: `m-${id}`, waktu: "2026-11-12T09:15:00", pengirim: nama, isi: "ayam bakar 2 ya" }],
  };
}

let pesananServer: Order[];
let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  simpanToken("t");
  localStorage.setItem("rekapesan.batch", "b1");
  pesananServer = [pesanan("o1", "Bu Rina", []), pesanan("o2", "Mas Budi", ["jam_kosong"])];
  fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    const ok = (body: unknown) => ({ ok: true, status: 200, json: async () => body });
    if (url.endsWith("/api/batches")) return ok([batch]);
    if (url.endsWith("/api/products")) return ok([menu]);
    if (url.endsWith("/orders/approve-clean") && init?.method === "POST") {
      pesananServer = pesananServer.map((o) => (o.tanda.length ? o : { ...o, status: "dikonfirmasi" }));
      return ok({ disetujui: 1, masih_bertanda: 1 });
    }
    if (url.includes("/api/batches/b1/orders")) return ok(pesananServer);
    throw new Error(`tak terduga: ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);
  HTMLDialogElement.prototype.showModal ??= function (this: HTMLDialogElement) {
    this.open = true;
  };
  HTMLDialogElement.prototype.close ??= function (this: HTMLDialogElement) {
    this.open = false;
  };
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  simpanToken(null);
  localStorage.clear();
});

describe("layar Cek pesanan", () => {
  it("menampilkan tanda kuning dengan teks (tidak hanya warna) dan mendahulukan yang bertanda", async () => {
    render(
      <AppProvider>
        <Review rute={bacaRute("#/cek")} />
      </AppProvider>,
    );
    const kartu = await screen.findAllByRole("article");
    expect(kartu[0].textContent).toContain("Mas Budi");
    expect(kartu[0].textContent).toContain("Jam kirim belum ada");
    expect(screen.getByText("1 pesanan tanpa tanda kuning")).toBeTruthy();
  });

  it("setujui semua yang bersih hanya lewat konfirmasi dan memanggil endpoint approve-clean", async () => {
    render(
      <AppProvider>
        <Review rute={bacaRute("#/cek")} />
      </AppProvider>,
    );
    await screen.findAllByRole("article");
    fireEvent.click(screen.getByRole("button", { name: "Setujui semua yang bersih" }));
    expect(fetchMock.mock.calls.some(([u]) => String(u).endsWith("approve-clean"))).toBe(false);
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Ya, setujui" }));
    });
    await waitFor(() => expect(fetchMock.mock.calls.some(([u]) => String(u).endsWith("approve-clean"))).toBe(true));
    await waitFor(() => expect(screen.getAllByRole("article")).toHaveLength(1));
  });
});
