/**
 * Admin panel - filter, search, refresh, refund action
 */

const API = "";
const POLL_INTERVAL_MS = 5000;

const tbody = document.getElementById("admin-orders-body");
const statusFilter = document.getElementById("status-filter");
const paymentFilter = document.getElementById("payment-filter");
const searchInput = document.getElementById("search-input");
const lastRefreshEl = document.getElementById("last-refresh");

let searchDebounce = null;

function formatItems(items) {
  if (!Array.isArray(items)) return "-";
  return items.map((i) => `${i.name}×${i.qty || 1}`).join(", ");
}

function buildUrl() {
  const params = new URLSearchParams();
  if (statusFilter.value) params.set("status", statusFilter.value);
  if (paymentFilter.value) params.set("payment", paymentFilter.value);
  if (searchInput.value.trim()) params.set("q", searchInput.value.trim());
  const qs = params.toString();
  return qs ? `${API}/api/orders?${qs}` : `${API}/api/orders`;
}

async function loadOrders() {
  const btn = document.getElementById("btn-refresh");
  btn.disabled = true;
  btn.textContent = "Loading...";

  try {
    const res = await fetch(buildUrl());
    const orders = await res.json();

    if (!orders.length) {
      tbody.innerHTML = '<tr><td colspan="10">No orders found.</td></tr>';
    } else {
      tbody.innerHTML = orders
        .map(
          (o) => `
        <tr>
          <td><strong>#${o.id}</strong></td>
          <td>${o.created_at || "-"}</td>
          <td>${o.customer_name}<br><small>${o.customer_phone}</small></td>
          <td>${o.restaurant_name}</td>
          <td>${formatItems(o.items)}</td>
          <td>₹${o.total_amount}</td>
          <td><code>${o.password}</code></td>
          <td><span class="status-pill status-${o.status}">${o.status.replace(/_/g, " ")}</span></td>
          <td class="${o.payment_status === "paid" ? "payment-paid" : "payment-unpaid"}">${o.payment_status}</td>
          <td>
            ${
              o.payment_status === "paid"
                ? `<button type="button" class="btn btn-small btn-danger" data-refund="${o.id}"><i class="fas fa-rotate-left"></i></button>`
                : "—"
            }
          </td>
        </tr>
      `
        )
        .join("");

      tbody.querySelectorAll("[data-refund]").forEach((btn) => {
        btn.addEventListener("click", () => refundOrder(btn.dataset.refund));
      });
    }

    const now = new Date().toLocaleTimeString();
    lastRefreshEl.textContent = `Last updated: ${now}`;
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="10">Error loading orders.</td></tr>';
  } finally {
    btn.disabled = false;
    btn.textContent = "Refresh now";
  }
}

async function refundOrder(orderId) {
  if (!confirm(`Mark order #${orderId} as refunded?`)) return;

  const res = await fetch(`${API}/api/orders/${orderId}/refund`, { method: "POST" });
  const data = await res.json();
  if (!res.ok) {
    alert(data.error || "Refund failed");
    return;
  }
  loadOrders();
}

statusFilter.addEventListener("change", loadOrders);
paymentFilter.addEventListener("change", loadOrders);
document.getElementById("btn-refresh").addEventListener("click", loadOrders);

searchInput.addEventListener("input", () => {
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(loadOrders, 400);
});

loadOrders();
setInterval(loadOrders, POLL_INTERVAL_MS);
