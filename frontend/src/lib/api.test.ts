import { describe, expect, it, vi } from "vitest";
import { cekKesehatan } from "./api";

describe("cekKesehatan", () => {
  it("mengembalikan status ok dari backend", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ status: "ok" }) }));
    await expect(cekKesehatan()).resolves.toEqual({ status: "ok" });
  });

  it("melempar error bila backend gagal", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 500 }));
    await expect(cekKesehatan()).rejects.toThrow();
  });
});
