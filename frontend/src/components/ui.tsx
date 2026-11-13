import { useEffect, useId, useRef, useState, type ButtonHTMLAttributes, type ReactNode } from "react";
import type { ApiError, KodeTanda, StatusPesanan } from "../lib/api";
import { STATUS, TANDA } from "../lib/format";
import { useApp } from "../lib/store";
import { Icon, type NamaIkon } from "./Icon";

/** Kartu kaca. Kilau mengikuti jari/kursor diatur oleh pendengar global di main.tsx. */
export function Kaca({
  as: Tag = "section",
  className = "",
  children,
  ...rest
}: { as?: "section" | "article" | "div" | "li"; className?: string; children: ReactNode } & Record<string, unknown>) {
  return (
    <Tag className={`kaca ${className}`} {...rest}>
      {children}
    </Tag>
  );
}

type Varian = "utama" | "kedua" | "bahaya" | "hantu" | "sukses";

export function Tombol({
  varian = "kedua",
  ikon,
  memuat,
  besar,
  penuh,
  children,
  className = "",
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  varian?: Varian;
  ikon?: NamaIkon;
  memuat?: boolean;
  besar?: boolean;
  penuh?: boolean;
}) {
  return (
    <button
      type="button"
      className={`tombol tombol-${varian} ${besar ? "tombol-besar" : ""} ${penuh ? "tombol-penuh" : ""} ${className}`}
      disabled={memuat || rest.disabled}
      aria-busy={memuat || undefined}
      {...rest}
    >
      {memuat ? <span className="putar" aria-hidden="true" /> : ikon ? <Icon nama={ikon} /> : null}
      <span>{children}</span>
    </button>
  );
}

export function ChipTanda({ kode, rinci }: { kode: KodeTanda; rinci?: boolean }) {
  const t = TANDA[kode];
  return (
    <span className="chip-tanda" title={t.saran}>
      <Icon nama="peringatan" ukuran={18} />
      <span>
        <strong>{t.judul}</strong>
        {rinci && <span className="chip-saran">{t.saran}</span>}
      </span>
    </span>
  );
}

const IKON_STATUS: Record<StatusPesanan, NamaIkon> = {
  perlu_cek: "peringatan",
  dikonfirmasi: "centang",
  dibayar: "dompet",
  dikirim: "truk",
  batal: "tutup",
};

export function LencanaStatus({ status }: { status: StatusPesanan }) {
  const s = STATUS[status];
  return (
    <span className={`lencana nada-${s.nada}`}>
      <Icon nama={IKON_STATUS[status]} ukuran={16} />
      {s.label}
    </span>
  );
}

export function Kepala({ judul, sub, aksi, kembali }: { judul: string; sub?: ReactNode; aksi?: ReactNode; kembali?: string }) {
  return (
    <header className="kepala">
      {kembali && (
        <a className="tombol tombol-hantu tombol-ikon" href={kembali} aria-label="Kembali">
          <Icon nama="kiri" />
        </a>
      )}
      <div className="kepala-teks">
        <h1>{judul}</h1>
        {sub && <p className="redup">{sub}</p>}
      </div>
      {aksi}
    </header>
  );
}

export function Kosong({ ikon, judul, children }: { ikon: NamaIkon; judul: string; children?: ReactNode }) {
  return (
    <div className="kosong">
      <div className="kosong-ikon">
        <Icon nama={ikon} ukuran={34} />
      </div>
      <h2>{judul}</h2>
      {children}
    </div>
  );
}

export function Memuat({ baris = 3, label = "Memuat data" }: { baris?: number; label?: string }) {
  return (
    <div role="status" aria-label={label} className="kerangka-grup">
      {Array.from({ length: baris }, (_, i) => (
        <div key={i} className="kaca kerangka" />
      ))}
      <span className="sr">{label}…</span>
    </div>
  );
}

export function Galat({ galat, ulang }: { galat: ApiError | Error; ulang?: () => void }) {
  const kode = "kode" in galat ? (galat as ApiError).kode : "";
  const kuota = kode === "kuota_llm_habis";
  return (
    <div className="kotak-galat" role="alert">
      <Icon nama={kuota ? "info" : "peringatan"} ukuran={26} />
      <div>
        <strong>{kuota ? "Kuota AI sedang habis" : "Ada kendala"}</strong>
        <p>{galat.message}</p>
        {ulang && (
          <Tombol ikon="ulang" onClick={ulang}>
            Coba lagi
          </Tombol>
        )}
      </div>
    </div>
  );
}

/** Dialog modal memakai <dialog> bawaan: fokus terkunci, Esc menutup, dan dibaca pembaca layar. */
export function Dialog({
  buka,
  tutup,
  judul,
  children,
  lembar,
}: {
  buka: boolean;
  tutup: () => void;
  judul: string;
  children: ReactNode;
  lembar?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const id = useId();
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (buka && !d.open) d.showModal?.();
    if (!buka && d.open) d.close?.();
  }, [buka]);
  return (
    <dialog
      ref={ref}
      className={`dialog ${lembar ? "dialog-lembar" : ""}`}
      aria-labelledby={id}
      onClose={tutup}
      onClick={(e) => {
        if (e.target === ref.current) tutup();
      }}
    >
      {buka && (
        <div className="dialog-isi">
          <div className="dialog-kepala">
            <h2 id={id}>{judul}</h2>
            <button type="button" className="tombol tombol-hantu tombol-ikon" onClick={tutup} aria-label="Tutup">
              <Icon nama="tutup" />
            </button>
          </div>
          {children}
        </div>
      )}
    </dialog>
  );
}

export function Konfirmasi({
  buka,
  tutup,
  judul,
  pesan,
  labelYa,
  bahaya,
  aksi,
}: {
  buka: boolean;
  tutup: () => void;
  judul: string;
  pesan: ReactNode;
  labelYa: string;
  bahaya?: boolean;
  aksi: () => Promise<void> | void;
}) {
  const [jalan, setJalan] = useState(false);
  return (
    <Dialog buka={buka} tutup={tutup} judul={judul}>
      <div className="dialog-pesan">{pesan}</div>
      <div className="baris-tombol">
        <Tombol onClick={tutup} disabled={jalan}>
          Tidak, kembali
        </Tombol>
        <Tombol
          varian={bahaya ? "bahaya" : "utama"}
          memuat={jalan}
          onClick={async () => {
            setJalan(true);
            try {
              await aksi();
              tutup();
            } finally {
              setJalan(false);
            }
          }}
        >
          {labelYa}
        </Tombol>
      </div>
    </Dialog>
  );
}

export function Toasts() {
  const { toasts, tutupToast } = useApp();
  return (
    <div className="toasts" aria-live="polite" aria-atomic="false">
      {toasts.map((t) => (
        <div key={t.id} className={`toast toast-${t.jenis}`} role={t.jenis === "galat" ? "alert" : "status"}>
          <Icon nama={t.jenis === "galat" ? "peringatan" : t.jenis === "info" ? "info" : "centang"} />
          <span>{t.teks}</span>
          <button type="button" className="toast-tutup" onClick={() => tutupToast(t.id)} aria-label="Tutup pemberitahuan">
            <Icon nama="tutup" ukuran={18} />
          </button>
        </div>
      ))}
    </div>
  );
}

export function Stepper({
  nilai,
  ubah,
  label,
}: {
  nilai: number | null;
  ubah: (n: number | null) => void;
  label: string;
}) {
  const n = nilai ?? 0;
  return (
    <div className="stepper" role="group" aria-label={label}>
      <button type="button" className="stepper-tombol" onClick={() => ubah(Math.max(0, n - 1))} aria-label={`Kurangi ${label}`}>
        <Icon nama="kurang" />
      </button>
      <input
        inputMode="numeric"
        pattern="[0-9]*"
        aria-label={label}
        value={nilai ?? ""}
        placeholder="?"
        onChange={(e) => {
          const v = e.target.value.replace(/\D/g, "");
          ubah(v === "" ? null : Number(v));
        }}
      />
      <button type="button" className="stepper-tombol" onClick={() => ubah(n + 1)} aria-label={`Tambah ${label}`}>
        <Icon nama="tambah" />
      </button>
    </div>
  );
}

export async function salinTeks(teks: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(teks);
    return true;
  } catch {
    // Cadangan untuk browser lama / konteks tidak aman (http di jaringan lokal).
    const ta = document.createElement("textarea");
    ta.value = teks;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand("copy");
    ta.remove();
    return ok;
  }
}

export function tautanWhatsApp(teks: string): string {
  return `https://wa.me/?text=${encodeURIComponent(teks)}`;
}
