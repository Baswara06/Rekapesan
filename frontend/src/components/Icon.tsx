// Ikon garis sederhana (gaya stroke 24px), ditulis langsung supaya tidak perlu pustaka tambahan.
// Ikon selalu dekoratif (aria-hidden): makna disampaikan oleh teks di sebelahnya.
const P: Record<string, string> = {
  beranda: "M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z",
  impor: "M12 3v12m0 0-4.5-4.5M12 15l4.5-4.5M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2",
  cek: "M9 11l2.5 2.5L16 9M12 21a9 9 0 1 1 0-18 9 9 0 0 1 0 18z",
  rekap: "M4 20V10m6 10V4m6 16v-7m4 7H2",
  tanya: "M8 4h8a5 5 0 0 1 5 5v4a5 5 0 0 1-5 5h-4.5L7 21v-3.1A5 5 0 0 1 3 13V9a5 5 0 0 1 5-5zM9.75 9.25a2.25 2.25 0 1 1 3.1 2.08c-.5.2-.85.62-.85 1.17v.25M12 15.25h.01",
  lainnya: "M4 6h16M4 12h16M4 18h16",
  pengaturan:
    "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm7.4-3a7.4 7.4 0 0 0-.1-1.3l2-1.6-2-3.4-2.4 1a7.4 7.4 0 0 0-2.2-1.3L14.3 3h-4l-.4 2.4a7.4 7.4 0 0 0-2.2 1.3l-2.4-1-2 3.4 2 1.6a7.4 7.4 0 0 0 0 2.6l-2 1.6 2 3.4 2.4-1a7.4 7.4 0 0 0 2.2 1.3l.4 2.4h4l.4-2.4a7.4 7.4 0 0 0 2.2-1.3l2.4 1 2-3.4-2-1.6c.1-.4.1-.9.1-1.3z",
  katalog: "M7 3v8a2 2 0 0 0 2 2v8M11 3v8M7 7h4M17 3c-1.7 0-3 2-3 5s1.3 4 3 4v9",
  hapus: "M4 7h16M10 11v6m4-6v6M6 7l1 13a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1l1-13M9 7V4h6v3",
  ubah: "M4 20h4L19 9l-4-4L4 16zM14 6l4 4",
  tutup: "M6 6l12 12M18 6 6 18",
  tambah: "M12 5v14M5 12h14",
  kurang: "M5 12h14",
  salin: "M9 9h10v12H9zM5 15H4V3h12v1",
  kirim: "M21 3 10 14M21 3l-7 18-4-7-7-4z",
  peringatan: "M12 9v4m0 4h.01M10.3 3.9 2.4 18a2 2 0 0 0 1.7 3h15.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z",
  jam: "M12 7v5l3 2M12 21a9 9 0 1 1 0-18 9 9 0 0 1 0 18z",
  lokasi: "M12 21s-7-6.2-7-11.5a7 7 0 0 1 14 0C19 14.8 12 21 12 21zm0-9a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z",
  chat: "M8 4h8a5 5 0 0 1 5 5v4a5 5 0 0 1-5 5h-4.5L7 21v-3.1A5 5 0 0 1 3 13V9a5 5 0 0 1 5-5z",
  kanan: "M9 5l7 7-7 7",
  bawah: "M5 9l7 7 7-7",
  kiri: "M15 5l-7 7 7 7",
  keluar: "M15 4h4a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-4M10 17l5-5-5-5M15 12H3",
  berkas: "M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8zM14 3v5h5M9 13h6M9 17h6",
  gambar: "M4 5h16v14H4zM4 16l5-5 4 4 2-2 5 5M15.5 9.5h.01",
  belanja: "M6 7h12l-1 13H7zM9 7a3 3 0 0 1 6 0",
  ulang: "M20 11a8 8 0 0 0-14.9-3M4 4v4h4M4 13a8 8 0 0 0 14.9 3M20 20v-4h-4",
  info: "M12 11v6m0-10h.01M12 21a9 9 0 1 1 0-18 9 9 0 0 1 0 18z",
  perisai: "M12 3l8 3v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6zM9 12l2 2 4-4",
  teks: "M4 7V5h10v2M9 5v14m-2 0h4M14 12v-1h6v1m-3-1v8m-1.5 0h3",
  matahari:
    "M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4",
  bulan: "M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z",
  centang: "M5 12.5l4.5 4.5L19 7",
  dompet: "M4 7h15a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1zM4 7l11-4v4M16 13.5h.01",
  truk: "M3 6h11v10H3zM14 10h4l3 3v3h-7M7.5 19a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3zm10 0a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3z",
  kalender: "M4 6h16v15H4zM4 10h16M8 3v4m8-4v4",
  orang: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21a8 8 0 0 1 16 0",
  kunci: "M6 11h12v10H6zM8.5 11V7.5a3.5 3.5 0 0 1 7 0V11",
  mata: "M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12zm10 3a3 3 0 1 0 0-6 3 3 0 0 0 0 6z",
  langkah: "M5 5h4v4H5zM15 15h4v4h-4zM9 7h4a2 2 0 0 1 2 2v6",
  hp: "M7 2h10a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1zM11 18h2",
};

export type NamaIkon = keyof typeof P;

export function Icon({ nama, ukuran = 22, className }: { nama: NamaIkon; ukuran?: number; className?: string }) {
  return (
    <svg
      className={className ? `ikon ${className}` : "ikon"}
      width={ukuran}
      height={ukuran}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d={P[nama]} />
    </svg>
  );
}
