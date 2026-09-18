export default function LoginPage() {
  return (
    <main style={{ padding: "2rem", fontFamily: "sans-serif", maxWidth: "400px", margin: "auto" }}>
      <h2>Đăng nhập - DX-Asset</h2>
      <form style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        <div>
          <label style={{ display: "block", marginBottom: "0.5rem" }}>Email / Username</label>
          <input type="text" placeholder="admin@dxasset.local" style={{ width: "100%", padding: "0.5rem" }} />
        </div>
        <div>
          <label style={{ display: "block", marginBottom: "0.5rem" }}>Mật khẩu</label>
          <input type="password" placeholder="••••••••" style={{ width: "100%", padding: "0.5rem" }} />
        </div>
        <button type="button" style={{ padding: "0.5rem 1rem", background: "#0066cc", color: "#fff", border: "none" }}>
          Đăng nhập (Skeleton)
        </button>
      </form>
    </main>
  );
}
