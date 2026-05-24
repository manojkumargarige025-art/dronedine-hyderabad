/**
 * Restaurant dashboard — stats, live orders, drone boxes
 */

const API = "";
const POLL_INTERVAL_MS = 3000;

const ordersContainer = document.getElementById("orders-container");
const titleEl = document.getElementById("restaurant-title");

async function checkLogin() {
  const res = await fetch(`${API}/api/restaurant/me`, { credentials: "include" });
  if (!res.ok) {
    window.location.href = "/restaurant/login";
    return null;
  }
  return res.json();
}

async function loadStats() {
  const res = await fetch(`${API}/api/restaurant/stats`, { credentials: "include" });
  if (!res.ok) return;
  const s = await res.json();
  document.getElementById("stat-orders").textContent = s.today_orders;
  document.getElementById("stat-revenue").textContent = `₹${s.today_revenue}`;
  document.getElementById("stat-active").textContent = s.active_orders;
  document.getElementById("stat-drone").textContent = s.drone_status;
}

async function fetchOrders() {
  const res = await fetch(`${API}/api/orders/pending`, { credentials: "include" });
  if (res.status === 401) {
    window.location.href = "/restaurant/login";
    return [];
  }
  return res.json();
}

function formatItems(items) {
  if (!Array.isArray(items)) return String(items);
  return items.map((i) => `${i.name} ×${i.qty || 1}`).join(", ");
}

function renderOrders(orders) {
  if (!orders.length) {
    ordersContainer.innerHTML =
      '<p class="alert alert-info"><i class="fas fa-mug-hot"></i> No active orders. New orders appear automatically.</p>';
    return;
  }

  ordersContainer.innerHTML = orders
    .map((order) => {
      const canAcceptDecline = order.status === "pending";
      const isPaid = order.payment_status === "paid";
      const showPassword =
        isPaid &&
        ["accepted", "preparing", "out_for_delivery", "pending"].includes(order.status);

      return `
      <article class="order-card ${order.status}">
        <div class="card-header">
          <div>
            <strong><i class="fas fa-receipt"></i> ORDER #${order.id}</strong>
            <span class="status-pill status-${order.status}">${order.status.replace(/_/g, " ")}</span>
          </div>
          <span class="hint">${order.created_at || ""}</span>
        </div>
        <p><i class="fas fa-user"></i> <strong>${order.customer_name}</strong> · ${order.customer_phone}</p>
        <p><i class="fas fa-location-dot"></i> ${order.customer_address}</p>
        <p><i class="fas fa-box"></i> ${formatItems(order.items)}</p>
        <p><i class="fas fa-indian-rupee-sign"></i> ₹${order.total_amount} ·
          <span class="${isPaid ? "payment-paid" : "payment-unpaid"}">${order.payment_status}</span>
        </p>
        ${!isPaid ? '<p class="alert alert-error"><i class="fas fa-exclamation-triangle"></i> Payment pending — cannot send drone.</p>' : ""}
        ${
          showPassword
            ? `<div>
            <p><strong><i class="fas fa-key"></i> Drone box password</strong></p>
            <div class="password-display">${order.password}</div>
          </div>`
            : ""
        }
        <div class="order-actions">
          ${
            canAcceptDecline
              ? `
            <button type="button" class="btn btn-small btn-success" data-action="accept" data-id="${order.id}">
              <i class="fas fa-check"></i> Accept
            </button>
            <button type="button" class="btn btn-small btn-danger" data-action="decline" data-id="${order.id}">
              <i class="fas fa-times"></i> Decline
            </button>
          `
              : ""
          }
          ${
            order.status === "accepted"
              ? `<button type="button" class="btn btn-small btn-secondary" data-action="preparing" data-id="${order.id}">
              <i class="fas fa-fire"></i> Preparing
            </button>`
              : ""
          }
          ${
            order.status === "preparing"
              ? `<button type="button" class="btn btn-small" data-action="out_for_delivery" data-id="${order.id}" ${!isPaid ? "disabled" : ""}>
              <i class="fas fa-helicopter"></i> Send Drone
            </button>`
              : ""
          }
          ${
            order.status === "out_for_delivery"
              ? `<button type="button" class="btn btn-small btn-success" data-action="delivered" data-id="${order.id}" ${!isPaid ? "disabled" : ""}>
              <i class="fas fa-flag-checkered"></i> Delivered
            </button>`
              : ""
          }
        </div>
      </article>
    `;
    })
    .join("");

  ordersContainer.querySelectorAll("[data-action]").forEach((btn) => {
    btn.addEventListener("click", () => updateOrder(btn.dataset.id, btn.dataset.action));
  });
}

async function updateOrder(orderId, action) {
  const res = await fetch(`${API}/api/orders/${orderId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ action }),
  });
  const data = await res.json();
  if (!res.ok) {
    alert(data.error || "Update failed");
    return;
  }
  refresh();
}

async function refresh() {
  try {
    await loadStats();
    const orders = await fetchOrders();
    renderOrders(orders);
  } catch (e) {
    console.error(e);
  }
}

async function init() {
  const me = await checkLogin();
  if (!me) return;

  titleEl.innerHTML = `<i class="fas fa-store"></i> ${me.restaurant_name}`;

  document.getElementById("btn-logout").onclick = async () => {
    await fetch(`${API}/api/restaurant/logout`, { method: "POST", credentials: "include" });
    window.location.href = "/restaurant/login";
  };

  refresh();
  setInterval(refresh, POLL_INTERVAL_MS);
}

init();
