import { useEffect, useId, useRef, useState } from "react";
import { inisial } from "../lib/format";
import { useApp } from "../lib/store";
import { Icon } from "./Icon";
import { Konfirmasi } from "./ui";

/**
 * Tombol akun di bilah atas: nama toko selalu terlihat, sekali ketuk membuka Profil toko, Katalog, dan Keluar.
 * Pola disclosure (tombol + daftar tautan), bukan role="menu", supaya mudah dibaca pembaca layar.
 */
export function MenuAkun() {
  const { akun, keluar } = useApp();
  const [buka, setBuka] = useState(false);
  const [yakinKeluar, setYakinKeluar] = useState(false);
  const wadah = useRef<HTMLDivElement>(null);
  const tombol = useRef<HTMLButtonElement>(null);
  const idPanel = useId();

  const nama = akun?.nama_toko || akun?.username || "Akun saya";

  useEffect(() => {
    if (!buka) return;
    const klikLuar = (e: PointerEvent) => {
      if (wadah.current && !wadah.current.contains(e.target as Node)) setBuka(false);
    };
    const esc = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setBuka(false);
        tombol.current?.focus();
      }
    };
    const pindah = () => setBuka(false);
    document.addEventListener("pointerdown", klikLuar);
    document.addEventListener("keydown", esc);
    window.addEventListener("hashchange", pindah);
    return () => {
      document.removeEventListener("pointerdown", klikLuar);
      document.removeEventListener("keydown", esc);
      window.removeEventListener("hashchange", pindah);
    };
  }, [buka]);

  return (
    <div className="menu-akun" ref={wadah}>
      <button
        ref={tombol}
        type="button"
        className="tombol-akun"
        aria-expanded={buka}
        aria-controls={idPanel}
        aria-label={`Akun: ${nama}. Profil toko, katalog, dan keluar`}
        onClick={() => setBuka((v) => !v)}
      >
        <span className="avatar-akun" aria-hidden="true">
          {inisial(nama)}
        </span>
        <span className="nama-akun">{nama}</span>
        <Icon nama="bawah" ukuran={16} />
      </button>

      {buka && (
        <div id={idPanel} className="kaca panel-akun">
          <div className="panel-akun-kepala">
            <span className="avatar-akun besar" aria-hidden="true">
              {inisial(nama)}
            </span>
            <span>
              <strong>{nama}</strong>
              {akun && <span className="redup kecil">Masuk sebagai {akun.username}</span>}
            </span>
          </div>
          <ul className="panel-akun-daftar">
            <li>
              <a href="#/pengaturan">
                <Icon nama="orang" ukuran={18} /> Profil toko dan pengaturan
              </a>
            </li>
            <li>
              <a href="#/katalog">
                <Icon nama="katalog" ukuran={18} /> Katalog menu
              </a>
            </li>
            <li>
              <button
                type="button"
                className="panel-akun-keluar"
                onClick={() => {
                  setBuka(false);
                  setYakinKeluar(true);
                }}
              >
                <Icon nama="keluar" ukuran={18} /> Keluar
              </button>
            </li>
          </ul>
        </div>
      )}

      <Konfirmasi
        buka={yakinKeluar}
        tutup={() => setYakinKeluar(false)}
        judul="Keluar dari Rekapesan?"
        pesan="Data pesanan tetap tersimpan. Masuk lagi dengan nama pengguna dan kata sandi yang sama."
        labelYa="Ya, keluar"
        bahaya
        aksi={() => {
          keluar();
          window.location.hash = "/";
        }}
      />
    </div>
  );
}
