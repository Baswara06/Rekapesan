import { useState } from "react";
import { api, ApiError, type PesananPapan, type Ringkasan, type SaranPesanan, type StatusBayar, type StatusPapan } from "../lib/api";
import { rupiah, TANDA, tanggalPanjang } from "../lib/format";
import { useApp } from "../lib/store";
import { Icon, type NamaIkon } from "./Icon";
import { ChipTanda, Konfirmasi, Tombol } from "./ui";

// Papan pesanan: semua hari → per jam kirim → kartu pesanan.
// Angka (total, omzet, belum bayar) dari server. Saran dari chat TIDAK pernah mengubah status sendiri:
// penjual selalu menekan tombol dan mengonfirmasi dulu (aturan desain 5 dan 9).

const STATUS_PAPAN: Record<StatusPapan, { label: string; ikon: NamaIkon; nada: string }> = {
  perlu_cek: { label: "Perlu dicek", ikon: "peringatan", nada: "kuning" },
  diproses: { label: "Diproses", ikon: "jam", nada: "biru" },
  selesai: { label: "Selesai", ikon: "truk", nada: "hijau" },
  batal: { label: "Batal", ikon: "tutup", nada: "abu" },
};

const BAYAR: Record<StatusBayar, { label: string; ikon: NamaIkon; nada: string }> = {
  lunas: { label: "Lunas", ikon: "dompet", nada: "hijau" },
  belum: { label: "Belum bayar", ikon: "dompet", nada: "kuning" },
};

export function LencanaPapan({ status }: { status: StatusPapan }) {
  const s = STATUS_PAPAN[status] ?? STATUS_PAPAN.perlu_cek;
  return (
    <span className={`lencana nada-${s.nada}`}>
      <Icon nama={s.ikon} ukuran={16} />
      {s.label}
    </span>
  );
}

export function LencanaBayar({ bayar }: { bayar: StatusBayar }) {
  const b = BAYAR[bayar] ?? BAYAR.belum;
  return (
    <span className={`lencana nada-${b.nada}`}>
      <Icon nama={b.ikon} ukuran={16} />
      {b.label}
    </span>
  );
}

export function RingkasanKeseluruhan({ data }: { data: Ringkasan["keseluruhan"] }) {
  const kotak: { label: string; nilai: string; ikon: NamaIkon; sorot?: boolean }[] = [
    { label: "Perlu dicek", nilai: String(data.perlu_cek), ikon: "peringatan", sorot: data.perlu_cek > 0 },
    { label: "Diproses", nilai: String(data.diproses), ikon: "jam" },
    { label: "Selesai", nilai: String(data.selesai), ikon: "truk" },
    { label: "Omzet disetujui", nilai: rupiah(data.omzet), ikon: "rekap" },
    {
      label: `Belum bayar (${data.jumlah_belum_bayar} orang)`,
      nilai: rupiah(data.belum_bayar),
      ikon: "dompet",
      sorot: data.jumlah_belum_bayar > 0,
    },
  ];
  return (
    <section className="kaca papan-ringkasan" aria-labelledby="judul-papan-ringkasan">
      <h2 id="judul-papan-ringkasan">Ringkasan semua hari</h2>
      <dl className="papan-kisi">
        {kotak.map((k) => (
          <div key={k.label} className={k.sorot ? "nada-kuning" : ""}>
            <dt>
              <Icon nama={k.ikon} ukuran={16} /> {k.label}
            </dt>
            <dd>{k.nilai}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

type AksiTunda = { judul: string; pesan: string; labelYa: string; jalan: () => Promise<unknown> } | null;

export function PapanPesanan({ data, saatBerubah }: { data: Ringkasan; saatBerubah: () => void }) {
  const { toast } = useApp();
  const [tunda, setTunda] = useState<AksiTunda>(null);
  const [sibuk, setSibuk] = useState<string | null>(null);

  async function jalankan(id: string, fn: () => Promise<unknown>, sukses: string) {
    setSibuk(id);
    try {
      await fn();
      toast(sukses);
      saatBerubah();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Aksi gagal. Coba lagi.", "galat");
    } finally {
      setSibuk(null);
    }
  }

  function minta(o: PesananPapan, jenis: "selesai" | "lunas" | SaranPesanan["jenis"], kutipan?: string | null) {
    const lunas = jenis === "lunas" || jenis === "sudah_bayar";
    const dariChat = jenis === "sudah_bayar" || jenis === "sudah_terima";
    setTunda({
      judul: lunas ? "Tandai lunas?" : "Tandai selesai?",
      pesan:
        (dariChat ? `Di chat, ${o.nama} menulis: "${kutipan ?? "-"}". ` : "") +
        (lunas
          ? `Pesanan ${o.nama} (${rupiah(o.total)}) akan ditandai sudah dibayar. Pastikan uangnya memang sudah masuk.`
          : `Pesanan ${o.nama} akan ditandai sudah dikirim dan diterima.`),
      labelYa: lunas ? "Ya, tandai lunas" : "Ya, tandai selesai",
      jalan: () =>
        jalankan(
          o.id,
          () => (lunas ? api.konfirmasiBayar(o.id) : api.ubahPesanan(o.id, { status: "dikirim" })),
          lunas ? `${o.nama} ditandai lunas` : `${o.nama} ditandai selesai`,
        ),
    });
  }

  const hari = data.hari.filter((h) => h.jam.some((j) => j.pesanan.length > 0));

  return (
    <div className="tumpuk papan">
      {hari.map((h) => {
        const jumlah = h.jam.reduce((a, j) => a + j.pesanan.length, 0);
        return (
          <section key={h.batch_id} className="papan-hari" aria-labelledby={`hari-${h.batch_id}`}>
            <div className="bagian-kepala">
              <h2 id={`hari-${h.batch_id}`}>
                <Icon nama="kalender" ukuran={18} /> {h.nama || tanggalPanjang(h.tanggal)}
              </h2>
              <span className="redup kecil">{jumlah} pesanan</span>
            </div>
            {h.jam
              .filter((j) => j.pesanan.length > 0)
              .map((j) => (
                <div key={j.jam ?? "tanpa-jam"} className="papan-jam">
                  <h3 className="papan-jam-judul">
                    <Icon nama="jam" ukuran={16} /> {j.jam ? `Kirim ${j.jam}` : "Jam belum ada"}
                  </h3>
                  <ul className="papan-daftar">
                    {j.pesanan.map((o) => (
                      <li key={o.id}>
                        <KartuPapan
                          o={o}
                          sibuk={sibuk === o.id}
                          setujui={() => jalankan(o.id, () => api.setujui(o.id), `Pesanan ${o.nama} disetujui`)}
                          minta={(jenis, kutipan) => minta(o, jenis, kutipan)}
                        />
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
          </section>
        );
      })}
      <Konfirmasi
        buka={!!tunda}
        tutup={() => setTunda(null)}
        judul={tunda?.judul ?? ""}
        pesan={tunda?.pesan ?? ""}
        labelYa={tunda?.labelYa ?? "Ya"}
        aksi={async () => {
          await tunda?.jalan();
        }}
      />
    </div>
  );
}

function KartuPapan({
  o,
  sibuk,
  setujui,
  minta,
}: {
  o: PesananPapan;
  sibuk: boolean;
  setujui: () => void;
  minta: (jenis: "selesai" | "lunas" | SaranPesanan["jenis"], kutipan?: string | null) => void;
}) {
  const perluCek = o.status_papan === "perlu_cek";
  const bisaSelesai = o.status_papan === "diproses";
  const bisaLunas = (o.status_papan === "diproses" || o.status_papan === "selesai") && o.bayar === "belum";
  // Saran hanya ditawarkan bila memang masih relevan (belum lunas / belum selesai).
  // Pesanan batal tidak menawarkan saran sama sekali.
  const saran =
    o.status_papan === "batal"
      ? []
      : o.saran.filter((s) => (s.jenis === "sudah_bayar" ? o.bayar === "belum" : o.status_papan !== "selesai"));
  const tanda = o.tanda.filter((k) => k in TANDA);

  return (
    <article className="kaca kartu-papan" aria-label={`Pesanan ${o.nama}`}>
      <div className="kartu-papan-atas">
        <strong className="kartu-papan-nama">{o.nama}</strong>
        <strong className="kartu-papan-total">{rupiah(o.total)}</strong>
      </div>
      <div className="kartu-papan-lencana">
        <LencanaPapan status={o.status_papan} />
        <LencanaBayar bayar={o.bayar} />
      </div>
      {o.items.length > 0 ? (
        <ul className="kartu-papan-item">
          {o.items.map((it, i) => (
            <li key={`${it.nama}-${i}`}>
              {it.qty ?? "?"}× {it.nama}
            </li>
          ))}
        </ul>
      ) : (
        <p className="redup kecil">Belum ada item</p>
      )}
      <p className="kartu-papan-alamat kecil">
        <Icon nama="lokasi" ukuran={16} /> {o.alamat || "Alamat belum ada"}
      </p>
      {tanda.length > 0 && (
        <div className="baris-tanda">
          {tanda.map((k) => (
            <ChipTanda key={k} kode={k} />
          ))}
        </div>
      )}
      {saran.length > 0 && (
        <ul className="kartu-papan-saran" aria-label="Saran dari chat">
          {saran.map((s, i) => (
            <li key={`${s.jenis}-${i}`}>
              <p className="kecil">
                <Icon nama="chat" ukuran={16} /> <strong>{s.teks}</strong>
                {s.kutipan && <span className="redup"> "{s.kutipan}"</span>}
              </p>
              {perluCek ? (
                <p className="kecil redup">Setujui pesanan dulu sebelum menandainya.</p>
              ) : (
                <Tombol className="tombol-papan" ikon={s.jenis === "sudah_bayar" ? "dompet" : "truk"} disabled={sibuk} onClick={() => minta(s.jenis, s.kutipan)}>
                  {s.teks}
                </Tombol>
              )}
            </li>
          ))}
        </ul>
      )}
      <div className="baris-tombol kartu-papan-aksi">
        {perluCek && (
          <Tombol className="tombol-papan" varian="utama" ikon="centang" memuat={sibuk} onClick={setujui}>
            Setujui
          </Tombol>
        )}
        {bisaSelesai && (
          <Tombol className="tombol-papan" ikon="truk" disabled={sibuk} onClick={() => minta("selesai")}>
            Tandai selesai
          </Tombol>
        )}
        {bisaLunas && (
          <Tombol className="tombol-papan" ikon="dompet" disabled={sibuk} onClick={() => minta("lunas")}>
            Tandai lunas
          </Tombol>
        )}
        <a href={`#/pesanan/${o.id}`} className="tombol tombol-hantu tombol-papan">
          <Icon nama="ubah" />
          <span>{perluCek ? "Cek detail" : "Detail"}</span>
        </a>
      </div>
    </article>
  );
}
