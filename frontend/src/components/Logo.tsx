// Logo Rekapesan.
// Tanda: gelembung chat yang isinya sudah tersusun jadi daftar ("chat jadi rekap"), dengan lencana centang
// karena tidak ada pesanan yang final sebelum disetujui penjual.
// Wordmark: huruf "p" diberi warna karena di situlah "rekap" dan "pesan" bertemu.

export function TandaLogo({ ukuran = 32, className }: { ukuran?: number; className?: string }) {
  return (
    <svg className={className} width={ukuran} height={ukuran} viewBox="0 0 512 512" aria-hidden="true" focusable="false">
      <rect width="512" height="512" rx="116" fill="#1c6b41" />
      <path
        fill="#fff"
        d="M168 116H344A64 64 0 0 1 408 180V284A64 64 0 0 1 344 348H226L140 408L164 348A64 64 0 0 1 104 284V180A64 64 0 0 1 168 116Z"
      />
      <g fill="#1c6b41">
        <circle cx="170" cy="186" r="13" />
        <rect x="198" y="174" width="130" height="24" rx="12" />
        <circle cx="170" cy="232" r="13" />
        <rect x="198" y="220" width="104" height="24" rx="12" />
        <circle cx="170" cy="278" r="13" />
        <rect x="198" y="266" width="74" height="24" rx="12" />
      </g>
      <circle cx="396" cy="128" r="62" fill="#f4b740" stroke="#1c6b41" strokeWidth="18" />
      <path d="M370 128l18 18 34-36" fill="none" stroke="#1d1b16" strokeWidth="18" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function TeksLogo({ className }: { className?: string }) {
  return (
    <span className={`teks-logo ${className ?? ""}`}>
      Reka<span className="teks-logo-p">p</span>esan
    </span>
  );
}

export function Logo({ ukuran = 32 }: { ukuran?: number }) {
  return (
    <span className="logo-rekapesan">
      <TandaLogo ukuran={ukuran} />
      <TeksLogo />
    </span>
  );
}
