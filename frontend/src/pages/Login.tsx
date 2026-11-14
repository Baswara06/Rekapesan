import { useState, type FormEvent } from "react";
import { Icon } from "../components/Icon";
import { TandaLogo, TeksLogo } from "../components/Logo";
import { Kaca, Tombol } from "../components/ui";
import { ApiError } from "../lib/api";
import { useApp } from "../lib/store";

const SANDI_MINIMAL = 8;
const TOKO_MINIMAL = 2;
const TOKO_MAKSIMAL = 60;

type GalatIsian = Partial<Record<"toko" | "sandi" | "ulang", string>>;

/** Validasi form Daftar di perangkat. Aturan sama dengan server, supaya galat muncul sebelum dikirim. */
function periksaDaftar(namaToko: string, password: string, ulang: string): GalatIsian {
  const g: GalatIsian = {};
  const toko = namaToko.trim().replace(/\s+/g, " ");
  if (toko.length < TOKO_MINIMAL || toko.length > TOKO_MAKSIMAL) g.toko = `Nama toko ${TOKO_MINIMAL}-${TOKO_MAKSIMAL} karakter.`;
  if (password.length < SANDI_MINIMAL) g.sandi = `Kata sandi minimal ${SANDI_MINIMAL} karakter.`;
  else if (ulang !== password) g.ulang = "Kata sandi tidak sama. Ketik ulang dengan teliti.";
  return g;
}

export default function Login() {
  const { login, daftar } = useApp();
  const [mode, setMode] = useState<"masuk" | "daftar">("masuk");
  const [namaToko, setNamaToko] = useState("");
  const [username, setUsername] = useState("demo");
  const [password, setPassword] = useState("");
  const [ulang, setUlang] = useState("");
  const [lihat, setLihat] = useState(false);
  const [jalan, setJalan] = useState(false);
  const [galat, setGalat] = useState("");
  const [galatIsian, setGalatIsian] = useState<GalatIsian>({});
  const daftarMode = mode === "daftar";

  async function kirim(e: FormEvent) {
    e.preventDefault();
    setGalat("");
    if (!username.trim() || !password) {
      setGalat("Isi nama pengguna dan kata sandi.");
      document.getElementById(!username.trim() ? "u" : "p")?.focus();
      return;
    }
    if (daftarMode) {
      const g = periksaDaftar(namaToko, password, ulang);
      setGalatIsian(g);
      const pertama = (["toko", "sandi", "ulang"] as const).find((k) => g[k]);
      if (pertama) {
        document.getElementById({ toko: "toko", sandi: "p", ulang: "p2" }[pertama])?.focus();
        return;
      }
    }
    setJalan(true);
    try {
      if (daftarMode) await daftar(username.trim(), password, namaToko.trim().replace(/\s+/g, " "));
      else await login(username.trim(), password);
      window.location.hash = "/";
    } catch (err) {
      setGalat(
        err instanceof ApiError ? err.message : mode === "daftar" ? "Gagal mendaftar. Coba lagi." : "Gagal masuk. Coba lagi.",
      );
    } finally {
      setJalan(false);
    }
  }

  function gantiMode() {
    const baru = mode === "masuk" ? "daftar" : "masuk";
    setMode(baru);
    setGalat("");
    setGalatIsian({});
    setPassword("");
    setUlang("");
    setUsername(baru === "daftar" ? "" : "demo");
  }


  return (
    <main className="login" id="isi">
      <section className="login-hero" aria-labelledby="judul-login">
        <div className="login-merek">
          <TandaLogo ukuran={56} className="logo-login" />
          <h1 className="judul-merek" id="judul-login">
            <TeksLogo />
          </h1>
        </div>
        <p className="login-tagline">
          {/* Coretan kuning penanda "ramai", hiasan saja. */}
          <svg className="ilu-coretan ilu-coretan-judul" viewBox="0 0 40 32" aria-hidden="true">
            <path d="M6 18 9 4M18 22 34 10" />
          </svg>
          Chat grup ramai,
          <br />
          rekap tetap <span className="sorot">rapi.</span>
        </p>
        <p className="login-slogan">Dari chat grup jadi rekap pesanan, tanpa salin ulang.</p>

        {/* Ilustrasi alur produk: pesan bebas di grup dibaca jadi baris rekap. Hiasan, isinya samaran. */}
        <div className="login-ilustrasi" aria-hidden="true">
          <svg className="ilu-coretan ilu-coretan-chat" viewBox="0 0 24 28" aria-hidden="true">
            <path d="M4 6 16 10M3 22 15 18" />
          </svg>
          <div className="ilu-chat">
            <span className="ilu-gelembung">kak ayam bakar 2 ya, ambil jam 12</span>
            <span className="ilu-gelembung ilu-gelembung-2">es teh 3 juga kak</span>
          </div>
          <svg className="ilu-panah" viewBox="0 0 96 40" aria-hidden="true">
            <path d="M4 14C28 34 60 36 86 22" />
            <path d="M74 14 88 21 78 33" />
          </svg>
          <div className="ilu-rekap">
            <div className="ilu-rekap-kepala">
              <span>Rekap pesanan</span>
              <span className="ilu-lencana">
                <Icon nama="centang" ukuran={14} /> Disetujui
              </span>
            </div>
            <div className="ilu-baris">
              <span>Ayam Bakar</span>
              <strong>×2</strong>
            </div>
            <div className="ilu-baris">
              <span>Es Teh</span>
              <strong>×3</strong>
            </div>
          </div>
        </div>

        <ul className="login-poin">
          <li>
            <Icon nama="chat" ukuran={18} /> AI membaca chat
          </li>
          <li>
            <Icon nama="dompet" ukuran={18} /> Harga dihitung kode
          </li>
          <li>
            <Icon nama="centang" ukuran={18} /> Anda yang menyetujui
          </li>
        </ul>
        {/* Ikon chat samar di pojok, hanya di layar lebar. */}
        <span className="login-hias login-hias-1" aria-hidden="true">
          <Icon nama="chat" ukuran={88} />
        </span>
        <span className="login-hias login-hias-2" aria-hidden="true">
          <Icon nama="chat" ukuran={64} />
        </span>
      </section>

      <div className="login-panel">
        <Kaca className="login-kartu">
          <form onSubmit={kirim} noValidate>
            <div className="login-sapa">
              <h2>{mode === "masuk" ? "Selamat datang kembali" : "Daftar akun penjual"}</h2>
              <p>
                {mode === "masuk"
                  ? "Masuk untuk melanjutkan rekap pesanan Anda."
                  : "Buat akun supaya katalog dan pesanan Anda terpisah dari penjual lain."}
              </p>
            </div>
            {daftarMode && (
              <div className="isian">
                <label htmlFor="toko">Nama toko</label>
                <div className="masukan-ikon">
                  <Icon nama="belanja" />
                  <input
                    id="toko"
                    autoComplete="organization"
                    value={namaToko}
                    onChange={(e) => {
                      setNamaToko(e.target.value);
                      if (galatIsian.toko) setGalatIsian((g) => ({ ...g, toko: undefined }));
                    }}
                    required
                    maxLength={TOKO_MAKSIMAL}
                    aria-invalid={!!galatIsian.toko}
                    aria-describedby={galatIsian.toko ? "galat-toko" : "aturan-toko"}
                    placeholder="mis. Dapur Bu Rina"
                  />
                </div>
                {galatIsian.toko ? (
                  <p id="galat-toko" className="teks-galat">
                    <Icon nama="peringatan" ukuran={16} /> {galatIsian.toko}
                  </p>
                ) : (
                  <p id="aturan-toko" className="login-catatan-isian">
                    Muncul di Beranda dan di balasan konfirmasi ke pembeli.
                  </p>
                )}
              </div>
            )}
            <div className="isian">
              <label htmlFor="u">Nama pengguna</label>
              <div className="masukan-ikon">
                <Icon nama="orang" />
                <input
                  id="u"
                  autoComplete="username"
                  autoCapitalize="none"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  aria-describedby={mode === "daftar" ? "aturan-u" : undefined}
                />
              </div>
              {mode === "daftar" && (
                <p id="aturan-u" className="login-catatan-isian">
                  3-32 karakter: huruf kecil, angka, titik, atau garis bawah.
                </p>
              )}
            </div>
            <div className="isian">
              <label htmlFor="p">Kata sandi</label>
              <div className="masukan-ikon">
                <Icon nama="kunci" />
                <input
                  id="p"
                  type={lihat ? "text" : "password"}
                  autoComplete={mode === "daftar" ? "new-password" : "current-password"}
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (galatIsian.sandi || galatIsian.ulang) setGalatIsian((g) => ({ ...g, sandi: undefined, ulang: undefined }));
                  }}
                  required
                  minLength={daftarMode ? SANDI_MINIMAL : undefined}
                  aria-invalid={!!galatIsian.sandi}
                  aria-describedby={
                    [daftarMode ? (galatIsian.sandi ? "galat-sandi" : "aturan-p") : "", galat ? "galat-login" : ""].join(" ").trim() ||
                    undefined
                  }
                />
                <button
                  type="button"
                  className="tombol-mata"
                  onClick={() => setLihat((v) => !v)}
                  aria-label={lihat ? "Sembunyikan kata sandi" : "Tampilkan kata sandi"}
                  aria-pressed={lihat}
                >
                  <Icon nama="mata" />
                </button>
              </div>
              {daftarMode &&
                (galatIsian.sandi ? (
                  <p id="galat-sandi" className="teks-galat">
                    <Icon nama="peringatan" ukuran={16} /> {galatIsian.sandi}
                  </p>
                ) : (
                  <p id="aturan-p" className="login-catatan-isian">
                    Minimal {SANDI_MINIMAL} karakter.
                  </p>
                ))}
            </div>
            {daftarMode && (
              <div className="isian">
                <label htmlFor="p2">Ulangi kata sandi</label>
                <div className="masukan-ikon">
                  <Icon nama="kunci" />
                  <input
                    id="p2"
                    type={lihat ? "text" : "password"}
                    autoComplete="new-password"
                    value={ulang}
                    onChange={(e) => {
                      setUlang(e.target.value);
                      if (galatIsian.ulang) setGalatIsian((g) => ({ ...g, ulang: undefined }));
                    }}
                    required
                    aria-invalid={!!galatIsian.ulang}
                    aria-describedby={galatIsian.ulang ? "galat-ulang" : undefined}
                  />
                </div>
                {galatIsian.ulang && (
                  <p id="galat-ulang" className="teks-galat">
                    <Icon nama="peringatan" ukuran={16} /> {galatIsian.ulang}
                  </p>
                )}
              </div>
            )}
            {galat && (
              <p id="galat-login" className="teks-galat" role="alert">
                <Icon nama="peringatan" ukuran={18} /> {galat}
              </p>
            )}
            <Tombol type="submit" varian="utama" besar penuh memuat={jalan}>
              {mode === "masuk" ? "Masuk" : "Daftar dan masuk"}
            </Tombol>
            <p className="login-ganti">
              {mode === "masuk" ? "Belum punya akun?" : "Sudah punya akun?"}{" "}
              <button type="button" className="tombol-tautan" onClick={gantiMode}>
                {mode === "masuk" ? "Daftar" : "Masuk"}
              </button>
            </p>
          </form>
          <p className="login-catatan">
            <Icon nama="perisai" ukuran={18} /> Nomor telepon pembeli disamarkan sebelum dibaca AI.
          </p>
        </Kaca>
      </div>
    </main>
  );
}
