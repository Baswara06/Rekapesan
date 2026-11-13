import { PilihBatch } from "../components/Batch";
import { Icon } from "../components/Icon";
import { Galat, Kaca, Kepala, Kosong, Memuat, salinTeks, tautanWhatsApp, Tombol } from "../components/ui";
import { api, type Order, type Recap, type ShoppingList } from "../lib/api";
import { angka, namaMenu, rupiah, tanggalPanjang } from "../lib/format";
import { useApp, useMuat } from "../lib/store";

export default function Rekap() {
  const { batchAktif, batches, versiData, katalogMap, toast } = useApp();
  const data = useMuat(
    batchAktif
      ? async () => {
          const [rekap, belanja, pesanan] = await Promise.all([
            api.rekap(batchAktif.id),
            api.daftarBelanja(batchAktif.id),
            api.daftarPesanan(batchAktif.id),
          ]);
          return { rekap, belanja, pesanan };
        }
      : null,
    [batchAktif?.id, versiData],
  );

  if (batches.length === 0)
    return (
      <div className="tumpuk">
        <Kepala judul="Rekap" />
        <PilihBatch />
      </div>
    );

  const d = data.data;
  const pesananMap = new Map<string, Order>((d?.pesanan ?? []).map((o) => [o.id, o]));

  function teksRekap(r: Recap, belanja: ShoppingList): string {
    const baris = [`*Rekap ${batchAktif?.nama ?? "PO"}*`, `Kirim: ${tanggalPanjang(batchAktif?.tanggal_kirim)}`, "", "*Masak:*"];
    r.produksi.forEach((p) => baris.push(`- ${p.nama}: ${p.qty} porsi`));
    baris.push("", "*Urutan kirim:*");
    r.urutan_kirim.forEach((u) => {
      baris.push(`${u.jam ?? "Jam belum ada"}:`);
      u.order_ids.forEach((id) => {
        const o = pesananMap.get(id);
        if (!o) return;
        const isi = o.items.map((it) => `${it.qty ?? "?"} ${namaMenu(it.product_id, it.teks_asli, katalogMap)}`).join(", ");
        baris.push(`  - ${o.customer.nama_tampil}: ${isi}${o.alamat ? ` (${o.alamat})` : ""}`);
      });
    });
    if (belanja.length) {
      baris.push("", "*Belanja:*");
      belanja.forEach((b) => baris.push(`- ${b.bahan}: ${angka(b.jumlah)} ${b.satuan}`));
    }
    baris.push("", `Omzet: ${rupiah(r.omzet)}`);
    return baris.join("\n");
  }

  return (
    <div className="tumpuk">
      <Kepala judul="Rekap" sub="Langkah 3 dari 3. Hanya pesanan yang sudah disetujui." />
      <PilihBatch ringkas />

      {data.memuat && !d ? (
        <Memuat baris={4} label="Memuat rekap" />
      ) : data.galat ? (
        <Galat galat={data.galat} ulang={data.muatUlang} />
      ) : d ? (
        <>
          {d.rekap.menunggu_persetujuan > 0 && (
            <a href="#/cek" className="kaca kartu peringatan-rekap">
              <Icon nama="peringatan" ukuran={26} />
              <span>
                <strong>Rekap belum lengkap.</strong> {d.rekap.menunggu_persetujuan} pesanan masih menunggu dicek dan belum dihitung di sini.
              </span>
              <Icon nama="kanan" />
            </a>
          )}

          <section className="kartu-hero">
            <span className="label-kecil">Omzet pesanan disetujui</span>
            <strong className="total-besar">{rupiah(d.rekap.omzet)}</strong>
            <div className="baris-tombol">
              <Tombol
                ikon="salin"
                onClick={async () => toast((await salinTeks(teksRekap(d.rekap, d.belanja))) ? "Rekap disalin." : "Gagal menyalin.", "info")}
              >
                Salin rekap
              </Tombol>
              <a className="tombol tombol-kedua" href={tautanWhatsApp(teksRekap(d.rekap, d.belanja))} target="_blank" rel="noopener noreferrer">
                <Icon nama="kirim" />
                <span>Bagikan</span>
              </a>
            </div>
          </section>

          <div className="kisi-rekap">
          <Kaca className="kartu">
            <h2 className="judul-kartu">
              <Icon nama="katalog" /> Yang harus dimasak
            </h2>
            {d.rekap.produksi.length === 0 ? (
              <Kosong ikon="katalog" judul="Belum ada yang disetujui">
                <p>Setujui pesanan di layar Cek, jumlahnya muncul di sini.</p>
              </Kosong>
            ) : (
              <ul className="daftar-produksi">
                {d.rekap.produksi.map((p) => {
                  const stok = katalogMap.get(p.product_id)?.stok_harian ?? null;
                  const persen = stok ? Math.min(100, Math.round((p.qty / stok) * 100)) : null;
                  const habis = p.stok_sisa !== null && p.stok_sisa < 0;
                  return (
                    <li key={p.product_id}>
                      <div className="produksi-baris">
                        <span className="produksi-nama">{p.nama}</span>
                        <span className="produksi-qty">
                          {p.qty} <small>porsi</small>
                        </span>
                      </div>
                      {persen !== null && (
                        <>
                          <div className={`batang ${habis ? "lebih" : ""}`} aria-hidden="true">
                            <span style={{ width: `${persen}%` }} />
                          </div>
                          <p className={`kecil ${habis ? "teks-bahaya" : "redup"}`}>
                            {habis ? (
                              <>
                                <Icon nama="peringatan" ukuran={14} /> Melebihi stok {Math.abs(p.stok_sisa!)} porsi
                              </>
                            ) : (
                              `Sisa stok ${p.stok_sisa} dari ${stok}`
                            )}
                          </p>
                        </>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </Kaca>

          <Kaca className="kartu">
            <h2 className="judul-kartu">
              <Icon nama="truk" /> Urutan kirim
            </h2>
            {d.rekap.urutan_kirim.length === 0 ? (
              <p className="redup">Belum ada pesanan disetujui.</p>
            ) : (
              <ol className="linimasa">
                {d.rekap.urutan_kirim.map((u) => (
                  <li key={u.jam ?? "kosong"}>
                    <span className={`linimasa-jam ${u.jam ? "" : "kosong-isi"}`}>{u.jam ?? "Jam belum ada"}</span>
                    <ul>
                      {u.order_ids.map((id) => {
                        const o = pesananMap.get(id);
                        if (!o) return null;
                        return (
                          <li key={id}>
                            <a href={`#/pesanan/${id}`} className="linimasa-pesanan">
                              <strong>{o.customer.nama_tampil}</strong>
                              <span>{o.items.map((it) => `${it.qty ?? "?"} ${namaMenu(it.product_id, it.teks_asli, katalogMap)}`).join(", ")}</span>
                              {o.alamat && (
                                <span className="redup kecil">
                                  <Icon nama="lokasi" ukuran={14} /> {o.alamat}
                                </span>
                              )}
                            </a>
                          </li>
                        );
                      })}
                    </ul>
                  </li>
                ))}
              </ol>
            )}
          </Kaca>

          <Kaca className="kartu">
            <h2 className="judul-kartu">
              <Icon nama="dompet" /> Belum bayar
            </h2>
            {d.rekap.belum_bayar.length === 0 ? (
              <p className="baris-ikon">
                <Icon nama="centang" /> Semua pesanan disetujui sudah bayar.
              </p>
            ) : (
              <ul className="daftar-baris">
                {d.rekap.belum_bayar.map((b) => (
                  <li key={b.order_id}>
                    <a href={`#/pesanan/${b.order_id}`}>
                      <span>{b.nama}</span>
                      <strong>{rupiah(b.total)}</strong>
                      <Icon nama="kanan" ukuran={18} />
                    </a>
                  </li>
                ))}
              </ul>
            )}
          </Kaca>

          <Kaca className="kartu">
            <h2 className="judul-kartu">
              <Icon nama="belanja" /> Daftar belanja
            </h2>
            {d.belanja.length === 0 ? (
              <p className="redup">
                Isi resep tiap menu di <a href="#/katalog">Katalog</a> supaya daftar belanja terhitung otomatis.
              </p>
            ) : (
              <ul className="daftar-centang">
                {d.belanja.map((b) => (
                  <li key={`${b.bahan}-${b.satuan}`}>
                    <label>
                      <input type="checkbox" />
                      <span className="daftar-centang-nama">{b.bahan}</span>
                      <strong>
                        {angka(b.jumlah)} {b.satuan}
                      </strong>
                    </label>
                  </li>
                ))}
              </ul>
            )}
          </Kaca>
          </div>
        </>
      ) : null}
    </div>
  );
}
