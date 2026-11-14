import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { PesananPapan, Ringkasan } from "../lib/api";
import { AppProvider } from "../lib/store";
import { PapanPesanan, RingkasanKeseluruhan } from "./PapanPesanan";

function pesanan(p: Partial<PesananPapan> & Pick<PesananPapan, "id" | "nama">): PesananPapan {
  return {
    status: "dikonfirmasi",
    status_papan: "diproses",
    bayar: "belum",
    total: 34000,
    jam_kirim: "11:30",
    alamat: "Perum Melati 3",
    items: [{ nama: "Nasi Ayam Bawang Putih", qty: 2 }],
    tanda: [],
    saran: [],
    ...p,
  };
}

const data: Ringkasan = {
  keseluruhan: { perlu_cek: 1, diproses: 1, selesai: 1, batal: 0, omzet: 68000, belum_bayar: 34000, jumlah_belum_bayar: 1 },
  hari: [
    {
      tanggal: "2026-11-15",
      batch_id: "b1",
      nama: "Minggu, 15 Nov",
      jam: [
        {
          jam: "11:30",
          pesanan: [
            pesanan({
              id: "o1",
              nama: "Bu Wulan",
              status: "perlu_cek",
              status_papan: "perlu_cek",
              tanda: ["alamat_kosong"],
              alamat: null,
              saran: [{ jenis: "sudah_bayar", teks: "Pembeli bilang sudah bayar", kutipan: "udah transfer ya kak" }],
            }),
            pesanan({
              id: "o2",
              nama: "Pak Anton",
              saran: [{ jenis: "sudah_bayar", teks: "Pembeli bilang sudah bayar", kutipan: "sudah tf" }],
            }),
          ],
        },
        { jam: null, pesanan: [pesanan({ id: "o3", nama: "Mbak Sari", status: "dikirim", status_papan: "selesai", bayar: "lunas" })] },
      ],
    },
  ],
};

let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  fetchMock = vi.fn(async () => ({ ok: true, status: 200, json: async () => ({}) }));
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
});

function tampil(saatBerubah = vi.fn()) {
  render(
    <AppProvider>
      <RingkasanKeseluruhan data={data.keseluruhan} />
      <PapanPesanan data={data} saatBerubah={saatBerubah} />
    </AppProvider>,
  );
  return saatBerubah;
}

const kartu = (nama: string) => screen.getByRole("article", { name: `Pesanan ${nama}` });
const panggilan = () =>
  fetchMock.mock.calls.map(([u, init]) => `${(init as RequestInit | undefined)?.method ?? "GET"} ${String(u)}`);

describe("papan pesanan", () => {
  it("menampilkan lencana status dan bayar sebagai teks, tanda kuning, dan grup jam", () => {
    tampil();
    expect(screen.getByText("Minggu, 15 Nov")).toBeTruthy();
    expect(screen.getByText("Kirim 11:30")).toBeTruthy();
    const wulan = within(kartu("Bu Wulan"));
    expect(wulan.getByText("Perlu dicek")).toBeTruthy();
    expect(wulan.getByText("Belum bayar")).toBeTruthy();
    expect(wulan.getByText("Alamat belum ada", { selector: "strong" })).toBeTruthy();
    fireEvent.click(screen.getByRole("tab", { name: /Riwayat/ }));
    const sari = within(kartu("Mbak Sari"));
    expect(sari.getByText("Selesai")).toBeTruthy();
    expect(sari.getByText("Lunas")).toBeTruthy();
    expect(screen.getByText("Rp68.000")).toBeTruthy();
  });

  it("pesanan perlu dicek hanya bisa disetujui dulu, saran tidak jadi tombol", async () => {
    const berubah = tampil();
    const wulan = within(kartu("Bu Wulan"));
    expect(wulan.queryByRole("button", { name: "Tandai lunas" })).toBeNull();
    expect(wulan.queryByRole("button", { name: "Tandai selesai" })).toBeNull();
    expect(wulan.queryByRole("button", { name: "Pembeli bilang sudah bayar" })).toBeNull();
    await act(async () => {
      fireEvent.click(wulan.getByRole("button", { name: "Setujui" }));
    });
    await waitFor(() => expect(panggilan()).toContain("POST /api/orders/o1/approve"));
    expect(berubah).toHaveBeenCalled();
  });

  it("saran sudah bayar memanggil payment-confirm hanya setelah konfirmasi", async () => {
    tampil();
    const anton = within(kartu("Pak Anton"));
    fireEvent.click(anton.getByRole("button", { name: "Pembeli bilang sudah bayar" }));
    expect(fetchMock).not.toHaveBeenCalled();
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Ya, tandai lunas" }));
    });
    await waitFor(() => expect(panggilan()).toContain("POST /api/orders/o2/payment-confirm"));
  });

  it("tandai selesai mengirim PATCH status dikirim", async () => {
    tampil();
    fireEvent.click(within(kartu("Pak Anton")).getByRole("button", { name: "Tandai selesai" }));
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Ya, tandai selesai" }));
    });
    await waitFor(() => expect(panggilan()).toContain("PATCH /api/orders/o2"));
    const patch = fetchMock.mock.calls.find(([u, init]) => String(u).endsWith("/orders/o2") && init?.method === "PATCH");
    expect(JSON.parse(String(patch?.[1]?.body))).toEqual({ status: "dikirim" });
  });
});

describe("tab papan", () => {
  it("memisahkan Perlu diproses dan Riwayat dengan jumlah di label", () => {
    tampil();
    const proses = screen.getByRole("tab", { name: /Perlu diproses \(2\)/ });
    expect(proses.getAttribute("aria-selected")).toBe("true");
    expect(screen.queryByRole("article", { name: "Pesanan Mbak Sari" })).toBeNull();
    // Jam null hanya berisi pesanan selesai+lunas, jadi tersembunyi di tab Perlu diproses.
    expect(screen.queryByText("Jam belum ada")).toBeNull();
    fireEvent.click(screen.getByRole("tab", { name: /Riwayat \(1\)/ }));
    expect(kartu("Mbak Sari")).toBeTruthy();
    expect(screen.queryByRole("article", { name: "Pesanan Bu Wulan" })).toBeNull();
    expect(screen.getByText("Jam belum ada")).toBeTruthy();
  });
});
