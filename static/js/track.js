/**
 * Order tracking — timeline, map placeholder, drone meta
 */

const API = "";
const POLL_MS = 5000;

const form = document.getElementById("track-form");
const resultSection = document.getElementById("track-result");
const errorEl = document.getElementById("track-error");
let pollTimer = null;

const STEPS = [
  { key: "pending", label: "Order placed", icon: "fa-clipboard-list" },
  { key: "accepted", label: "Restaurant accepted", icon: "fa-check" },
  { key: "preparing", label: "Food preparing", icon: "fa-fire" },
  { key: "out_for_delivery", label: "Drone in the air", icon: "fa-helicopter" },
  { key: "delivered", label: "Delivered", icon: "fa-circle-check" },
];

function stepIndex(status) {
  if (status === "declined") return -1;
  const idx = STEPS.findIndex((s) => s.key === status);
  return idx >= 0 ? idx : 0;
}

function renderTimeline(order) {
  if (order.status === "declined") {
    return '<p class="alert alert-error"><i class="fas fa-times-circle"></i> Order declined by restaurant.</p>';
  }

  const current = stepIndex(order.status);
  return `
    <div class="track-steps">
      ${STEPS.map((step, i) => {
        const done = i <= current;
        const active = i === current;
        return `
          <div class="track-step ${done ? "done" : ""} ${active ? "active" : ""}">
            <span class="track-icon"><i class="fas ${step.icon}"></i></span>
            <span>${step.label}</span>
          </div>
        `;
      }).join("")}
    </div>
  `;
}

function mockBattery(status) {
  if (status === "delivered") return 68;
  if (status === "out_for_delivery") return 72;
  if (status === "preparing") return 88;
  return 95;
}

function etaText(status) {
  if (status === "delivered") return "Delivered";
  if (status === "out_for_delivery") return "3–5 minutes";
  if (status === "preparing") return "8–12 minutes";
  return "Restaurant confirming";
}

function showOrder(order) {
  resultSection.classList.remove("hidden");
  errorEl.classList.add("hidden");

  document.getElementById("result-id").textContent = order.id;
  document.getElementById("track-order-summary").innerHTML = `
    <strong>${order.restaurant_name}</strong> · ${order.customer_name}<br>
    <i class="fas fa-location-dot"></i> ${order.customer_address}
  `;
  document.getElementById("track-timeline").innerHTML = renderTimeline(order);
  document.getElementById("track-details").innerHTML = `
    <p>Status: <span class="status-pill status-${order.status}">${order.status.replace(/_/g, " ")}</span></p>
    <p>Total paid: <strong>₹${order.total_amount}</strong></p>
  `;

  const battery = mockBattery(order.status);
  document.getElementById("drone-meta").innerHTML = `
    <span><i class="fas fa-battery-three-quarters"></i> Battery
      <span class="battery-bar"><span class="battery-fill" style="width:${battery}%"></span></span>
      ${battery}%
    </span>
    <span><i class="fas fa-clock"></i> ETA: <strong>${etaText(order.status)}</strong></span>
  `;

  const mapEl = document.getElementById("map-container");
  mapEl.style.display =
    order.status === "out_for_delivery" || order.status === "delivered" ? "flex" : "none";

  const payEl = document.getElementById("track-payment");
  if (order.payment_status === "paid") {
    payEl.innerHTML = '<i class="fas fa-check-circle"></i> Payment received.';
    payEl.className = "alert alert-success";
  } else if (order.payment_status === "refunded") {
    payEl.textContent = "Payment refunded.";
    payEl.className = "alert alert-info";
  } else {
    payEl.innerHTML = '<i class="fas fa-exclamation-circle"></i> Payment pending.';
    payEl.className = "alert alert-error";
  }
}

async function fetchTrack() {
  const orderId = document.getElementById("track-order-id").value.trim();
  const phone = document.getElementById("track-phone").value.trim();
  if (!orderId || !phone) return;

  const res = await fetch(
    `${API}/api/orders/track?order_id=${encodeURIComponent(orderId)}&phone=${encodeURIComponent(phone)}`
  );
  const data = await res.json();

  if (!res.ok) {
    resultSection.classList.add("hidden");
    errorEl.textContent = data.error || "Order not found";
    errorEl.classList.remove("hidden");
    return;
  }

  showOrder(data);
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  if (pollTimer) clearInterval(pollTimer);
  fetchTrack();
  pollTimer = setInterval(fetchTrack, POLL_MS);
});

const params = new URLSearchParams(window.location.search);
if (params.get("order_id")) document.getElementById("track-order-id").value = params.get("order_id");
if (params.get("phone")) document.getElementById("track-phone").value = params.get("phone");
if (params.get("order_id") && params.get("phone")) {
  fetchTrack();
  pollTimer = setInterval(fetchTrack, POLL_MS);
}
