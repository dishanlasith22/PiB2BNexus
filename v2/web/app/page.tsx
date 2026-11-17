const modules = [
  ["Dealer Network", "Catalogues, dealer QR, goods handover and credit ledger"],
  ["Shop Operations", "Branches, staff, barcode inventory and POS billing"],
  ["Customer Loyalty", "Pi checkout, shop membership, referrals and rewards"],
  ["Financial Ledger", "Immutable sales, dealer dues, refunds and settlements"],
];

export default function Home() {
  return (
    <main style={{ maxWidth: 1040, margin: "0 auto", padding: "64px 24px" }}>
      <p style={{ color: "#7350a1", fontWeight: 700, letterSpacing: 1 }}>PI NETWORK COMMERCE</p>
      <h1 style={{ fontSize: 42, marginBottom: 12 }}>PIB2BNexus</h1>
      <p style={{ color: "#5e5868", fontSize: 18, maxWidth: 680, lineHeight: 1.6 }}>
        A connected B2B2C commerce ecosystem for dealers, retail shops and customers.
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16, marginTop: 36 }}>
        {modules.map(([title, description]) => (
          <section key={title} style={{ background: "white", border: "1px solid #e8e3ef", borderRadius: 14, padding: 20 }}>
            <h2 style={{ fontSize: 18 }}>{title}</h2>
            <p style={{ color: "#625b6d", lineHeight: 1.5 }}>{description}</p>
            <small style={{ color: "#806b9a" }}>Foundation in progress</small>
          </section>
        ))}
      </div>
      <p style={{ marginTop: 36, color: "#756d7e", fontSize: 13 }}>
        V2 development environment — existing PIB2BNexus service remains unchanged.
      </p>
    </main>
  );
}
