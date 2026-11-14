import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { TraceLangkah } from "../lib/api";
import { TraceAgen } from "./TraceAgen";

afterEach(cleanup);

const belumBayar: TraceLangkah = {
  tool: "daftar_belum_bayar",
  argumen: { batch_id: "b1" },
  hasil_ringkas: '{"jumlah": 2, "total_tagihan": 102000, "pesanan": [{"nama": "Pak Hendra", "total": 85000, "jam_kirim": "12:00"}, {"nama": "+62 812-0000-1111", "total": 17000, "jam_kirim": nul…',
  hasil: {
    jumlah: 2,
    total_tagihan: 102000,
    pesanan: [
      { nama: "Pak Hendra", total: 85000, jam_kirim: "12:00" },
      { nama: "Mas Rizky", total: 17000, jam_kirim: null },
    ],
  },
};

const pembeli: TraceLangkah = {
  tool: "cek_pesanan_pelanggan",
  argumen: { batch_id: "b1", nama: "Mas Rizky" },
  hasil_ringkas: "…",
  hasil: {
    cocok: 1,
    pesanan: [
      {
        nama: "Mas Rizky",
        status: "dikonfirmasi",
        jam_kirim: null,
        alamat: null,
        catatan: "buat acara kantor",
        total: 2550000,
        perlu_diperhatikan: ["jumlah porsi tidak wajar (terlalu banyak)", "alamat belum ada"],
        item: [{ menu: "Nasi Ayam Bawang Putih", porsi: 150 }],
      },
    ],
  },
};

describe("trace agen", () => {
  it("menampilkan langkah sebagai kalimat dan daftar, bukan JSON mentah", () => {
    render(<TraceAgen trace={[belumBayar, pembeli]} />);
    expect(screen.getByText("Membaca daftar yang belum bayar")).toBeTruthy();
    expect(screen.getByText(/2 pesanan belum bayar/)).toBeTruthy();
    expect(screen.getByText("Rp102.000")).toBeTruthy();
    expect(screen.getByText("Pak Hendra")).toBeTruthy();
    expect(screen.getAllByText(/jam belum ada/).length).toBeGreaterThan(0);

    expect(screen.getByText("Mencari pesanan “Mas Rizky”")).toBeTruthy();
    expect(screen.getByText("150× Nasi Ayam Bawang Putih")).toBeTruthy();
    expect(screen.getByText("Disetujui")).toBeTruthy();
    expect(screen.getByText(/jumlah porsi tidak wajar/, { ignore: "pre" })).toBeTruthy();
    // Nama alat teknis hanya ada di bagian "Data mentah".
    expect(screen.getByText("daftar_belum_bayar").closest(".data-mentah")).toBeTruthy();
  });

  it("memakai hasil_ringkas bila server lama belum mengirim hasil utuh", () => {
    render(<TraceAgen trace={[{ tool: "rekap_produksi", argumen: {}, hasil_ringkas: "ringkasan lama" }]} />);
    expect(screen.getByText("Menghitung porsi yang harus dimasak")).toBeTruthy();
    expect(screen.getAllByText("ringkasan lama").length).toBeGreaterThan(0);
  });

  it("menampilkan galat alat sebagai peringatan", () => {
    render(<TraceAgen trace={[{ tool: "rekap_produksi", argumen: { jam: "25" }, hasil_ringkas: "", hasil: { galat: "Jam '25' tidak dikenali." } }]} />);
    expect(screen.getByText(/Jam '25' tidak dikenali/, { ignore: "pre" })).toBeTruthy();
  });
});
