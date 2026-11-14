import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const keluar = vi.fn();
vi.mock("../lib/store", () => ({
  useApp: () => ({ akun: { username: "ratrifa", nama_toko: "Dapur Ratri" }, keluar }),
}));

import { MenuAkun } from "./MenuAkun";

afterEach(cleanup);

describe("menu akun", () => {
  it("nama toko terlihat, sekali ketuk membuka profil, katalog, dan keluar", () => {
    render(<MenuAkun />);
    const tombol = screen.getByRole("button", { name: /Akun: Dapur Ratri/ });
    expect(tombol.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(tombol);
    expect(tombol.getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByText("Masuk sebagai ratrifa")).toBeTruthy();
    expect(screen.getByRole("link", { name: /Profil toko/ }).getAttribute("href")).toBe("#/pengaturan");
    expect(screen.getByRole("link", { name: /Katalog menu/ }).getAttribute("href")).toBe("#/katalog");
  });

  it("keluar lewat konfirmasi dulu", () => {
    HTMLDialogElement.prototype.showModal ??= function (this: HTMLDialogElement) {
      this.open = true;
    };
    HTMLDialogElement.prototype.close ??= function (this: HTMLDialogElement) {
      this.open = false;
    };
    render(<MenuAkun />);
    fireEvent.click(screen.getByRole("button", { name: /Akun:/ }));
    fireEvent.click(screen.getByRole("button", { name: "Keluar" }));
    expect(keluar).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Ya, keluar" }));
    expect(keluar).toHaveBeenCalledOnce();
  });
});
