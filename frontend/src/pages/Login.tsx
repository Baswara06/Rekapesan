import { useState, type FormEvent } from "react";
import { Icon } from "../components/Icon";
import { Kaca, Tombol } from "../components/ui";
import { ApiError } from "../lib/api";
import { useApp } from "../lib/store";

export default function Login() {
  const { login } = useApp();
  const [username, setUsername] = useState("demo");
  const [password, setPassword] = useState("");
  const [lihat, setLihat] = useState(false);
  const [jalan, setJalan] = useState(false);
  const [galat, setGalat] = useState("");

  async function kirim(e: FormEvent) {
    e.preventDefault();
    setGalat("");
    setJalan(true);
    try {
      await login(username.trim(), password);
      window.location.hash = "/";
    } catch (err) {
      setGalat(err instanceof ApiError ? err.message : "Gagal masuk. Coba lagi.");
    } finally {
      setJalan(false);
    }
  }

  return (
    <main className="login" id="isi">
      <div className="login-merek">
        <div className="logo" aria-hidden="true">
          <Icon nama="chat" ukuran={30} />
        </div>
        <h1 className="judul-merek">Rekapesan</h1>
        <p className="login-slogan">Dari chat grup jadi rekap pesanan, tanpa salin ulang.</p>
      </div>

      <Kaca className="login-kartu">
        <form onSubmit={kirim} noValidate>
          <h2>Masuk</h2>
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
              />
            </div>
          </div>
          <div className="isian">
            <label htmlFor="p">Kata sandi</label>
            <div className="masukan-ikon">
              <Icon nama="kunci" />
              <input
                id="p"
                type={lihat ? "text" : "password"}
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                aria-describedby={galat ? "galat-login" : undefined}
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
          </div>
          {galat && (
            <p id="galat-login" className="teks-galat" role="alert">
              <Icon nama="peringatan" ukuran={18} /> {galat}
            </p>
          )}
          <Tombol type="submit" varian="utama" besar penuh memuat={jalan} disabled={!username || !password}>
            Masuk
          </Tombol>
        </form>
      </Kaca>

      <p className="login-catatan">
        <Icon nama="perisai" ukuran={18} /> Nomor telepon pembeli disamarkan sebelum dibaca AI.
      </p>
    </main>
  );
}
