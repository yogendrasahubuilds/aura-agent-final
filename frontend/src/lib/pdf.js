import jsPDF from "jspdf";

const fmt = (n) => new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(n);

export function downloadBookingPdf(receipt) {
  const { booking_id, intent, option, quantity, amount, extra, created_at, seats } = receipt;
  const title =
    intent === "movie" ? option.cinema :
    intent === "hotel" ? option.hotel :
    `${option.airline} ${option.flight_no}`;

  const doc = new jsPDF({ unit: "pt", format: "a5" });
  const W = doc.internal.pageSize.getWidth();
  const H = doc.internal.pageSize.getHeight();

  // Header band
  doc.setFillColor(79, 70, 229);
  doc.rect(0, 0, W, 70, "F");
  doc.setTextColor(255, 255, 255);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(22);
  doc.text("AURA", 24, 36);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(9);
  doc.text("Autonomous Universal Resource Agent", 24, 52);

  doc.setFontSize(8);
  doc.text("SIMULATED BOOKING", W - 24, 36, { align: "right" });
  doc.setFontSize(7);
  doc.text("Demo ticket · no real reservation", W - 24, 50, { align: "right" });

  // Body
  let y = 100;
  doc.setTextColor(100, 116, 139);
  doc.setFontSize(8);
  doc.text("BOOKING ID", 24, y);
  y += 14;
  doc.setFont("courier", "bold");
  doc.setFontSize(18);
  doc.setTextColor(15, 23, 42);
  doc.text(booking_id, 24, y);

  // Type badge
  const typeLabel = intent.toUpperCase();
  const badgeColors = {
    MOVIE: [225, 29, 72],
    HOTEL: [16, 185, 129],
    FLIGHT: [59, 130, 246],
  };
  const bc = badgeColors[typeLabel] || [79, 70, 229];
  doc.setFillColor(...bc);
  doc.roundedRect(W - 90, y - 18, 66, 22, 4, 4, "F");
  doc.setFont("helvetica", "bold");
  doc.setFontSize(9);
  doc.setTextColor(255, 255, 255);
  doc.text(typeLabel, W - 57, y - 4, { align: "center" });

  // Dashed divider
  y += 22;
  doc.setDrawColor(203, 213, 225);
  doc.setLineDashPattern([3, 3], 0);
  doc.line(24, y, W - 24, y);
  doc.setLineDashPattern([], 0);

  // Details
  y += 24;
  const rows = [];
  rows.push(["Selection", title]);
  if (intent === "movie") {
    rows.push(["Movie", option.movie]);
    rows.push(["Show time", `${option.time} · ${option.screen} · ${option.format}`]);
    rows.push(["Location", option.location]);
    rows.push(["Tickets", String(quantity)]);
    if (seats && seats.length) rows.push(["Seats", seats.join(", ")]);
  } else if (intent === "hotel") {
    rows.push(["Room", option.room_type]);
    rows.push(["Location", option.location]);
    rows.push(["Nights", String(extra?.nights || 1)]);
    rows.push(["Guests", String(quantity)]);
  } else if (intent === "flight") {
    rows.push(["Route", `${option.source} → ${option.destination}`]);
    rows.push(["From", option.source_airport]);
    rows.push(["To", option.destination_airport]);
    rows.push(["Departure", `${option.departure}  ·  Arrival ${option.arrival}`]);
    rows.push(["Duration", option.duration]);
    rows.push(["Passengers", String(quantity)]);
  }
  rows.push(["Booked at", new Date(created_at).toLocaleString("en-IN")]);

  doc.setFont("helvetica", "normal");
  doc.setFontSize(9);
  rows.forEach(([k, v]) => {
    doc.setTextColor(100, 116, 139);
    doc.text(k, 24, y);
    doc.setTextColor(15, 23, 42);
    doc.setFont("helvetica", "bold");
    const lines = doc.splitTextToSize(String(v ?? "—"), W - 140);
    doc.text(lines, 110, y);
    doc.setFont("helvetica", "normal");
    y += Math.max(14, lines.length * 12);
  });

  // Price footer
  y = H - 100;
  doc.setDrawColor(203, 213, 225);
  doc.setLineDashPattern([3, 3], 0);
  doc.line(24, y, W - 24, y);
  doc.setLineDashPattern([], 0);
  y += 20;
  doc.setFontSize(8);
  doc.setTextColor(100, 116, 139);
  doc.text("TOTAL (SIMULATED)", 24, y);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(18);
  doc.setTextColor(15, 23, 42);
  doc.text(`Rs. ${fmt(amount.total)}`, 24, y + 20);

  // Watermark
  doc.setTextColor(226, 232, 240);
  doc.setFontSize(44);
  doc.setFont("helvetica", "bold");
  doc.text("DEMO", W - 30, H - 24, { align: "right", angle: 0 });

  // Save
  doc.save(`${booking_id}.pdf`);
}
