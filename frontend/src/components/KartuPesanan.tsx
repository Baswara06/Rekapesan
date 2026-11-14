import { useState } from "react";
import type { Order, OrderItem, PesanSumber, PotretPesanan, Product } from "../lib/api";
import { inisial, jamPesan, namaMenu, rupiah } from "../lib/format";
import { useApp } from "../lib/store";
import { Icon } from "./Icon";
import { ChipTanda, Kaca, LencanaStatus, Tombol } from "./ui";

export function DaftarItem({ items, katalog }: { items: OrderItem[]; katalog: Map<string, Product> }) {
  if (items.length === 0) return <p className="redup miring">Belum ada item.</p>;
  return (
    <ul className="daftar-item">
      {items.map((it, i) => {
        const dikenal = !!it.product_id && katalog.has(it.product_id);
        return (
          <li key={it.id ?? i} className={dikenal ? "" : "item-asing"}>
            <span className="item-qty">{it.qty ?? "?"}×</span>
            <span className="item-nama">
              {namaMenu(it.product_id, it.teks_asli, katalog)}
              {!dikenal && (
                <span className="item-catatan">
                  <Icon nama="peringatan" ukuran={14} /> tidak ada di katalog: "{it.teks_asli}"
                </span>
              )}
              {it.catatan_item && <span className="item-catatan">{it.catatan_item}</span>}
            </span>
            <span className="item-harga">{it.harga_satuan != null && it.qty != null ? rupiah(it.harga_satuan * it.qty) : "-"}</span>
          </li>
        );
      })}
    </ul>
  );
}

export function GelembungChat({ pesan }: { pesan: PesanSumber[] }) {
  if (pesan.length === 0) return <p className="redup miring">Tidak ada chat sumber.</p>;
  return (
    <ol className="gelembung-daftar" aria-label="Chat asli">
      {pesan.map((m) => (
        <li key={m.id} className="gelembung">
          <p>{m.isi}</p>
          <time dateTime={m.waktu}>{jamPesan(m.waktu)}</time>
        </li>
      ))}
    </ol>
  );
}

function ringkasItem(items: OrderItem[], katalog: Map<string, Product>): string {
  return items.map((it) => `${it.qty ?? "?"} ${namaMenu(it.product_id, it.teks_asli, katalog)}`).join(", ") || "tanpa item";
}

export function Perubahan({ sebelum, sesudah, katalog }: { sebelum: PotretPesanan; sesudah: PotretPesanan | null; katalog: Map<string, Product> }) {
  return (
    <div className="perubahan" aria-label="Perubahan dari pembeli">
      <p className="perubahan-judul">
        <Icon nama="ulang" ukuran={18} /> Pembeli mengubah pesanan
      </p>
      <div className="perubahan-kisi">
        <div className="perubahan-lama">
          <span className="label-kecil">Sebelum</span>
          <p>{ringkasItem(sebelum.items, katalog)}</p>
          <p className="redup">{rupiah(sebelum.total)}</p>
        </div>
        <Icon nama="kanan" className="perubahan-panah" />
        <div className="perubahan-baru">
          <span className="label-kecil">Sesudah</span>
          {sesudah ? (
            <>
              <p>{sesudah.status === "batal" ? "Dibatalkan" : ringkasItem(sesudah.items, katalog)}</p>
              <p className="redup">{rupiah(sesudah.total)}</p>
            </>
          ) : (
            <p>-</p>
          )}
        </div>
      </div>
    </div>
  );
}

export function KartuPesanan({
  order,
  setujui,
  tolak,
}: {
  order: Order;
  setujui: (o: Order) => Promise<void>;
  tolak: (o: Order) => void;
}) {
  const { katalogMap } = useApp();
  const bertanda = order.tanda.length > 0;
  const [chatBuka, setChatBuka] = useState(bertanda || !!order.perubahan.sebelum);
  const [jalan, setJalan] = useState(false);
  const idJudul = `pesanan-${order.id}`;

  return (
    <Kaca as="article" className={`kartu kartu-pesanan ${bertanda ? "bertanda" : ""} status-${order.status}`} aria-labelledby={idJudul}>
      <header className="pesanan-kepala">
        <span className="avatar" aria-hidden="true">
          {inisial(order.customer.nama_tampil)}
        </span>
        <div className="pesanan-nama">
          <h2 id={idJudul}>{order.customer.nama_tampil}</h2>
          <LencanaStatus status={order.status} />
        </div>
        <div className="pesanan-total">
          <span className="label-kecil">Total</span>
          <strong>{rupiah(order.total)}</strong>
        </div>
      </header>

      {bertanda && (
        <div className="baris-tanda" aria-label="Tanda kuning">
          {order.tanda.map((t) => (
            <ChipTanda key={t} kode={t} />
          ))}
        </div>
      )}

      {order.perubahan.sebelum && <Perubahan sebelum={order.perubahan.sebelum} sesudah={order.perubahan.sesudah} katalog={katalogMap} />}

      <div className={`banding ${chatBuka ? "chat-buka" : ""}`}>
        <div className="banding-chat">
          <button type="button" className="tombol-lipat" aria-expanded={chatBuka} onClick={() => setChatBuka((v) => !v)}>
            <Icon nama="chat" ukuran={18} />
            Chat asli ({order.pesan_sumber.length})
            <Icon nama="bawah" ukuran={18} className="panah-lipat" />
          </button>
          {chatBuka && <GelembungChat pesan={order.pesan_sumber} />}
        </div>
        <div className="banding-hasil">
          <span className="label-kecil">
            <Icon nama="tanya" ukuran={16} /> Dibaca AI, dihitung sistem
          </span>
          <DaftarItem items={order.items} katalog={katalogMap} />
          <dl className="info-kirim">
            <div className={order.jam_kirim ? "" : "kosong-isi"}>
              <dt>
                <Icon nama="jam" ukuran={18} />
                <span className="sr">Jam kirim</span>
              </dt>
              <dd>{order.jam_kirim ?? "Jam belum ada"}</dd>
            </div>
            <div className={order.alamat ? "" : "kosong-isi"}>
              <dt>
                <Icon nama="lokasi" ukuran={18} />
                <span className="sr">Alamat</span>
              </dt>
              <dd>{order.alamat ?? "Alamat belum ada"}</dd>
            </div>
            {order.catatan && (
              <div>
                <dt>
                  <Icon nama="info" ukuran={18} />
                  <span className="sr">Catatan</span>
                </dt>
                <dd>{order.catatan}</dd>
              </div>
            )}
          </dl>
        </div>
      </div>

      <footer className="pesanan-aksi">
        {order.status === "perlu_cek" ? (
          <>
            <Tombol
              varian="sukses"
              ikon="centang"
              memuat={jalan}
              onClick={async () => {
                setJalan(true);
                try {
                  await setujui(order);
                } finally {
                  setJalan(false);
                }
              }}
            >
              Setujui
            </Tombol>
            <a className="tombol tombol-kedua" href={`#/pesanan/${order.id}`}>
              <Icon nama="ubah" />
              <span>Ubah</span>
            </a>
            <Tombol varian="hantu" ikon="tutup" onClick={() => tolak(order)} className="teks-bahaya">
              Tolak
            </Tombol>
          </>
        ) : (
          <a className="tombol tombol-kedua tombol-penuh" href={`#/pesanan/${order.id}`}>
            <span>Buka detail</span>
            <Icon nama="kanan" />
          </a>
        )}
      </footer>
    </Kaca>
  );
}
