import type { ReactNode } from "react";
import type { StatusPesanan, TraceLangkah } from "../lib/api";
import { rupiah, STATUS, tanggalPanjang } from "../lib/format";
import { Icon, type NamaIkon } from "./Icon";
import { LencanaStatus } from "./ui";

/**
 * Langkah agen tanya-jawab dalam bahasa penjual. Data yang dibaca agen ditampilkan sebagai kalimat dan daftar,
 * JSON aslinya tetap bisa dibuka di "Data mentah" supaya tetap transparan.
 */

type Data = Record<string, unknown>;

const teks = (v: unknown): string | null => (typeof v === "string" && v.trim() ? v : null);
const bil = (v: unknown): number => (typeof v === "number" ? v : 0);
const daftar = (v: unknown): Data[] => (Array.isArray(v) ? (v.filter((x) => x && typeof x === "object") as Data[]) : []);

function judulLangkah(t: TraceLangkah): { ikon: NamaIkon; judul: string } {
  const nama = teks(t.argumen.nama);
  const jam = teks(t.argumen.jam);
  const tgl = teks(t.argumen.tanggal);
  // "· Sabtu, 14 Nov" bila AI menyaring satu hari; tanpa tanggal berarti semua hari.
  const hari = tgl ? ` · ${tanggalPanjang(tgl)}` : "";
  switch (t.tool) {
    case "daftar_belum_bayar":
      return { ikon: "dompet", judul: `Membaca daftar yang belum bayar${hari}` };
    case "cek_pesanan_pelanggan":
      return { ikon: "orang", judul: (nama ? `Mencari pesanan “${nama}”` : "Mencari pesanan pembeli") + hari };
    case "rekap_produksi":
      return { ikon: "rekap", judul: (jam ? `Menghitung porsi untuk jam ${jam}` : "Menghitung porsi yang harus dimasak") + hari };
    case "cari_riwayat_tanya": {
      const kata = teks(t.argumen.kata_kunci);
      return { ikon: "langkah", judul: kata ? `Membaca riwayat percakapan soal “${kata}”` : "Membaca riwayat percakapan lain" };
    }
    default:
      return { ikon: "langkah", judul: t.tool.replace(/_/g, " ") };
  }
}

function Jam({ jam }: { jam: unknown }) {
  return <>{teks(jam) ? `jam ${jam}` : "jam belum ada"}</>;
}

function BelumBayar({ h }: { h: Data }) {
  const pesanan = daftar(h.pesanan);
  if (pesanan.length === 0) return <p className="langkah-ringkas">Semua pesanan yang disetujui sudah lunas.</p>;
  return (
    <>
      <p className="langkah-ringkas">
        {bil(h.jumlah)} pesanan belum bayar, total <strong>{rupiah(bil(h.total_tagihan))}</strong>
      </p>
      <ul className="langkah-daftar">
        {pesanan.map((p, i) => (
          <li key={i}>
            <span className="langkah-nama">{teks(p.nama) ?? "-"}</span>
            <span className="langkah-nilai">
              <strong>{rupiah(bil(p.total))}</strong> · <Jam jam={p.jam_kirim} />
            </span>
          </li>
        ))}
      </ul>
    </>
  );
}

function PesananPembeli({ h }: { h: Data }) {
  const pesanan = daftar(h.pesanan);
  if (pesanan.length === 0) return <p className="langkah-ringkas">{teks(h.pesan) ?? "Pembeli tidak ditemukan."}</p>;
  return (
    <div className="langkah-kartu-kartu">
      {pesanan.map((p, i) => {
        const status = teks(p.status) as StatusPesanan | null;
        const perhatian = (Array.isArray(p.perlu_diperhatikan) ? p.perlu_diperhatikan : []).filter(teks) as string[];
        return (
          <div key={i} className="langkah-kartu">
            <div className="langkah-kartu-kepala">
              <strong>{teks(p.nama) ?? "-"}</strong>
              {status && status in STATUS && <LencanaStatus status={status} />}
            </div>
            <ul className="langkah-item">
              {daftar(p.item).map((it, j) => (
                <li key={j}>
                  {it.porsi == null ? "?" : bil(it.porsi)}× {teks(it.menu) ?? "-"}
                </li>
              ))}
            </ul>
            <p className="langkah-meta">
              <Icon nama="jam" ukuran={14} /> <Jam jam={p.jam_kirim} />
              <span aria-hidden="true"> · </span>
              <Icon nama="lokasi" ukuran={14} /> {teks(p.alamat) ?? "alamat belum ada"}
            </p>
            <p className="langkah-total">
              Total <strong>{rupiah(bil(p.total))}</strong>
            </p>
            {perhatian.length > 0 && (
              <ul className="langkah-perhatian" aria-label="Perlu diperhatikan">
                {perhatian.map((x) => (
                  <li key={x}>
                    <Icon nama="peringatan" ukuran={14} /> {x}
                  </li>
                ))}
              </ul>
            )}
          </div>
        );
      })}
    </div>
  );
}

function RekapProduksi({ h }: { h: Data }) {
  const produksi = daftar(h.produksi);
  const menunggu = bil(h.pesanan_menunggu_persetujuan_tidak_dihitung);
  return (
    <>
      <p className="langkah-ringkas">
        <strong>{bil(h.total_porsi)} porsi</strong> dari {bil(h.pesanan_dihitung)} pesanan yang sudah disetujui
      </p>
      {produksi.length > 0 && (
        <ul className="langkah-daftar">
          {produksi.map((r, i) => (
            <li key={i}>
              <span className="langkah-nama">{teks(r.menu) ?? "-"}</span>
              <span className="langkah-nilai">
                <strong>{bil(r.porsi)}</strong> porsi
              </span>
            </li>
          ))}
        </ul>
      )}
      {menunggu > 0 && (
        <p className="langkah-catatan">
          <Icon nama="info" ukuran={14} /> {menunggu} pesanan masih menunggu persetujuan, belum ikut dihitung.
        </p>
      )}
    </>
  );
}

function RiwayatLain({ h }: { h: Data }) {
  const riwayat = daftar(h.riwayat);
  if (riwayat.length === 0) return <p className="langkah-ringkas">{teks(h.pesan) ?? "Tidak ada riwayat yang cocok."}</p>;
  return (
    <ul className="langkah-daftar">
      {riwayat.map((r, i) => (
        <li key={i}>
          <span className="langkah-nama">
            {teks(r.dari) === "penjual" ? "Anda: " : "AI: "}
            {teks(r.isi) ?? "-"}
          </span>
          <span className="langkah-nilai">{teks(r.tanggal) ?? ""}</span>
        </li>
      ))}
    </ul>
  );
}

function IsiLangkah({ t }: { t: TraceLangkah }) {
  const h = t.hasil;
  if (!h || Object.keys(h).length === 0) return <p className="langkah-ringkas">{t.hasil_ringkas}</p>;
  if (teks(h.galat)) {
    return (
      <p className="langkah-galat">
        <Icon nama="peringatan" ukuran={14} /> {teks(h.galat)}
      </p>
    );
  }
  const isi: Record<string, ReactNode> = {
    daftar_belum_bayar: <BelumBayar h={h} />,
    cek_pesanan_pelanggan: <PesananPembeli h={h} />,
    rekap_produksi: <RekapProduksi h={h} />,
    cari_riwayat_tanya: <RiwayatLain h={h} />,
  };
  return <>{isi[t.tool] ?? <p className="langkah-ringkas">{t.hasil_ringkas}</p>}</>;
}

export function TraceAgen({ trace }: { trace: TraceLangkah[] }) {
  if (trace.length === 0) return <p className="trace-kosong kecil redup">Dijawab tanpa membaca data pesanan.</p>;
  return (
    <details className="trace">
      <summary>
        <Icon nama="langkah" ukuran={16} /> Data yang dibaca AI ({trace.length} langkah)
      </summary>
      <ol className="langkah-ai">
        {trace.map((t, i) => {
          const { ikon, judul } = judulLangkah(t);
          return (
            <li key={i}>
              <p className="langkah-judul">
                <span className="langkah-nomor" aria-hidden="true">
                  <Icon nama={ikon} ukuran={14} />
                </span>
                <span>
                  <span className="sr-only">Langkah {i + 1}: </span>
                  {judul}
                </span>
              </p>
              <div className="langkah-isi">
                <IsiLangkah t={t} />
                <details className="data-mentah">
                  <summary>Data mentah</summary>
                  <p className="data-mentah-alat">
                    alat: <code>{t.tool}</code>
                  </p>
                  <pre>{t.hasil && Object.keys(t.hasil).length > 0 ? JSON.stringify(t.hasil, null, 2) : t.hasil_ringkas}</pre>
                </details>
              </div>
            </li>
          );
        })}
      </ol>
    </details>
  );
}
