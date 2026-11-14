import { useState, type FormEvent } from "react";
import { Icon } from "../components/Icon";
import { TandaLogo, TeksLogo } from "../components/Logo";
import { Kaca, Tombol } from "../components/ui";
import { ApiError } from "../lib/api";
import { useApp } from "../lib/store";

const SANDI_MINIMAL = 8;

export default function Login() {
  const { login, daftar } = useApp();
  const [mode, setMode] = useState<"masuk" | "daftar">("masuk");
  const [username, setUsername] = useState("demo");
  const [password, setPassword] = useState("");
  const [lihat, setLihat] = useState(false);
  const [jalan, setJalan] = useState(false);
  const [galat, setGalat] = useState("");

  async function kirim(e: FormEvent) {
    e.preventDefault();
    setGalat("");
    if (mode === "daftar" && password.length < SANDI_MINIMAL) {
      setGalat(`Kata sandi minimal ${SANDI_MINIMAL} karakter.`);
      return;
    }
    setJalan(true);
    try {
      await (mode === "daftar" ? daftar : login)(username.trim(), password);
      window.location.hash = "/";
    } catch (err) {
      setGalat(err instanceof ApiError ? err.message : mode === "daftar" ? "Gagal mendaftar. Coba lagi." : "Gagal masuk. Coba lagi.");
    } finally {
      setJalan(false);
    }
  }

  function gantiMode() {
    const baru = mode === "masuk" ? "daftar" : "masuk";
    setMode(baru);
    setGalat("");
    setPassword("");
    setUsername(baru === "daftar" ? "" : "demo");
  }

  return (
    <main className="login" id="isi">
      <div className="login-merek">
        <TandaLogo ukuran={72} className="logo-login" />
        <h1 className="judul-merek">
          <TeksLogo />
        </h1>
        <p className="login-slogan">Dari chat grup jadi rekap pesanan, tanpa salin ulang.</p>
      </div>

      <Kaca className="login-kartu">
        <form onSubmit={kirim} noValidate>
          <h2>{mode === "masuk" ? "Masuk" : "Daftar akun penjual"}</h2>
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
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={mode === "daftar" ? SANDI_MINIMAL : undefined}
                aria-describedby={[mode === "daftar" ? "aturan-p" : "", galat ? "galat-login" : ""].join(" ").trim() || undefined}
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
            {mode === "daftar" && (
              <p id="aturan-p" className="login-catatan-isian">
                Minimal {SANDI_MINIMAL} karakter.
              </p>
            )}
          </div>
          {galat && (
            <p id="galat-login" className="teks-galat" role="alert">
              <Icon nama="peringatan" ukuran={18} /> {galat}
            </p>
          )}
          <Tombol type="submit" varian="utama" besar penuh memuat={jalan} disabled={!username || !password}>
            {mode === "masuk" ? "Masuk" : "Daftar dan masuk"}
          </Tombol>
          <p className="login-ganti">
            {mode === "masuk" ? "Belum punya akun?" : "Sudah punya akun?"}{" "}
            <button type="button" className="tombol-tautan" onClick={gantiMode}>
              {mode === "masuk" ? "Daftar" : "Masuk"}
            </button>
          </p>
        </form>

      </Kaca>

      <p className="login-catatan">
        <Icon nama="perisai" ukuran={18} /> Nomor telepon pembeli disamarkan sebelum dibaca AI.
      </p>
    </main>
  );
}
