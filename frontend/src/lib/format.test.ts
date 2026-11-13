import { describe, expect, it } from "vitest";
import type { KodeTanda } from "./api";
import { inisial, namaMenu, PINDAH_STATUS, pisahAlias, rupiah, sapaan, TANDA } from "./format";

describe("format", () => {
  it("rupiah tanpa spasi dan tanpa desimal", () => {
    expect(rupiah(36000)).toBe("Rp36.000");
    expect(rupiah(null)).toBe("-");
  });

  it("inisial melewati sapaan Bu/Pak/Mbak", () => {
    expect(inisial("Bu Rina")).toBe("R");
    expect(inisial("Pak Anton Wijaya")).toBe("AW");
    expect(inisial("Dewi")).toBe("D");
  });

  it("alias dipisah koma dan dibersihkan", () => {
    expect(pisahAlias(" aybak, ayam bkr ,, ")).toEqual(["aybak", "ayam bkr"]);
  });

  it("nama menu tak dikenal memakai tulisan pembeli", () => {
    expect(namaMenu(null, "rendang", new Map())).toBe("rendang");
  });

  it("sapaan mengikuti jam", () => {
    expect(sapaan(7)).toBe("Selamat pagi");
    expect(sapaan(20)).toBe("Selamat malam");
  });

  it("setiap kode tanda kuning punya judul dan saran", () => {
    const kode: KodeTanda[] = [
      "item_tidak_dikenal", "jumlah_kosong", "jumlah_tidak_wajar", "alamat_kosong",
      "jam_kosong", "stok_kurang", "mungkin_dobel", "gagal_diekstrak",
    ];
    for (const k of kode) {
      expect(TANDA[k].judul).toBeTruthy();
      expect(TANDA[k].saran).toBeTruthy();
    }
  });

  it("perpindahan status sama dengan tabel kontrak dan tidak pernah ke dibayar", () => {
    expect(PINDAH_STATUS.perlu_cek).toEqual(["dikonfirmasi", "batal"]);
    expect(PINDAH_STATUS.dikirim).toEqual([]);
    for (const tujuan of Object.values(PINDAH_STATUS)) expect(tujuan).not.toContain("dibayar");
  });
});
