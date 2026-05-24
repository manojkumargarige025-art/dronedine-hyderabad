/**
 * DroneDine customer app — restaurants, search, cart, checkout, Razorpay
 */

const API = "";
const DELIVERY_FEE = 20;

const RESTAURANT_META = {
  bawarchi: {
    icon: "fa-utensils",
    cuisine: "Biryani, Kebabs, North Indian",
    eta: "10-15 min",
    tags: ["nonveg", "drone"],
  },
  paradise: {
    icon: "fa-drumstick-bite",
    cuisine: "Biryani, Haleem, Kebabs",
    eta: "15-20 min",
    tags: ["nonveg", "drone"],
  },
  chutneys: {
    icon: "fa-leaf",
    cuisine: "South Indian, Idly, Dosa, Vada",
    eta: "8-12 min",
    tags: ["veg", "drone"],
  },
};

let restaurants = [];
let selectedRestaurant = null;
let cart = [];
let activeFilter = "all";
let searchQuery = "";

const restaurantListEl = document.getElementById("restaurant-list");
const menuSectionEl = document.getElementById("menu-section");
const menuListEl = document.getElementById("menu-list");
const menuTitleEl = document.getElementById("menu-title");
const cartToggleEl = document.getElementById("cart-toggle");
const cartBadgeEl = document.getElementById("cart-badge");
const cartPanelEl = document.getElementById("cart-panel");
const cartOverlayEl = document.getElementById("cart-overlay");
const cartItemsEl = document.getElementById("cart-items");
const cartSubtotalEl = document.getElementById("cart-subtotal");
const cartTotalEl = document.getElementById("cart-total");
const cartRestaurantNameEl = document.getElementById("cart-restaurant-name");
const checkoutModalEl = document.getElementById("checkout-modal");
const checkoutFormEl = document.getElementById("checkout-form");
const checkoutFoodTotalEl = document.getElementById("checkout-food-total");
const checkoutTotalEl = document.getElementById("checkout-total");
const unlockSectionEl = document.getElementById("unlock-section");

function foodTotal() {
  return cart.reduce((s, i) => s + i.price * i.qty, 0);
}

function grandTotal() {
  return cart.length ? foodTotal() + DELIVERY_FEE : 0;
}

function openCart() {
  cartPanelEl.classList.add("open");
  cartOverlayEl.classList.add("show");
}

function closeCart() {
  cartPanelEl.classList.remove("open");
  cartOverlayEl.classList.remove("show");
}

async function loadRestaurants() {
  const res = await fetch(`${API}/api/restaurants`);
  restaurants = await res.json();
  renderRestaurants();
}

function matchesFilter(r) {
  const meta = RESTAURANT_META[r.id] || { tags: [] };
  if (activeFilter === "all") return true;
  if (activeFilter === "drone") return meta.tags.includes("drone");
  return meta.tags.includes(activeFilter);
}

function matchesSearch(r) {
  if (!searchQuery) return true;
  const q = searchQuery.toLowerCase();
  const meta = RESTAURANT_META[r.id] || {};
  const inMenu = r.menu.some((m) => m.name.toLowerCase().includes(q));
  return (
    r.name.toLowerCase().includes(q) ||
    r.area.toLowerCase().includes(q) ||
    (meta.cuisine || "").toLowerCase().includes(q) ||
    inMenu
  );
}

function renderRestaurants() {
  const filtered = restaurants.filter((r) => matchesFilter(r) && matchesSearch(r));

  if (!filtered.length) {
    restaurantListEl.innerHTML =
      '<p class="alert alert-info">No restaurants match your search.</p>';
    return;
  }

  restaurantListEl.innerHTML = filtered
    .map((r) => {
      const meta = RESTAURANT_META[r.id] || {
        icon: "fa-utensils",
        cuisine: "Indian",
        eta: "12-18 min",
        tags: [],
      };
      return `
    <div class="restaurant-card" data-id="${r.id}">
      <div class="restaurant-image">
        <i class="fas ${meta.icon}"></i>
      </div>
      <div class="restaurant-info">
        <div class="restaurant-name">${r.name}</div>
        <div class="restaurant-cuisine">${meta.cuisine}</div>
        <p class="area">${r.area}</p>
        <div class="restaurant-rating">
          <i class="fas fa-star"></i> ${r.rating}
        </div>
        <span class="drone-badge"><i class="fas fa-helicopter"></i> ${meta.eta}</span>
      </div>
    </div>
  `;
    })
    .join("");

  document.querySelectorAll(".restaurant-card").forEach((card) => {
    card.addEventListener("click", () => selectRestaurant(card.dataset.id));
    if (selectedRestaurant && card.dataset.id === selectedRestaurant.id) {
      card.classList.add("selected");
    }
  });
}

function selectRestaurant(id) {
  selectedRestaurant = restaurants.find((r) => r.id === id);
  if (!selectedRestaurant) return;

  document.querySelectorAll(".restaurant-card").forEach((c) => {
    c.classList.toggle("selected", c.dataset.id === id);
  });

  menuSectionEl.classList.remove("hidden");
  menuTitleEl.innerHTML = `<i class="fas fa-book-open"></i> Menu — ${selectedRestaurant.name}`;
  menuSectionEl.scrollIntoView({ behavior: "smooth", block: "start" });
  renderMenu();
}

function renderMenu() {
  menuListEl.innerHTML = selectedRestaurant.menu
    .map(
      (item) => `
    <div class="menu-item">
      <span>${item.name}</span>
      <div>
        <span class="price">₹${item.price}</span>
        <button type="button" class="btn btn-small btn-secondary" data-add="${item.id}">
          <i class="fas fa-plus"></i> Add
        </button>
      </div>
    </div>
  `
    )
    .join("");

  menuListEl.querySelectorAll("[data-add]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      addToCart(btn.dataset.add);
    });
  });
}

function addToCart(menuId) {
  if (!selectedRestaurant) {
    alert("Please select a restaurant first.");
    return;
  }

  const item = selectedRestaurant.menu.find((m) => m.id === menuId);
  const existing = cart.find(
    (c) => c.id === menuId && c.restaurantId === selectedRestaurant.id
  );

  if (existing) {
    existing.qty += 1;
  } else {
    if (cart.length && cart[0].restaurantId !== selectedRestaurant.id) {
      if (!confirm("Cart has items from another restaurant. Clear and add?")) return;
      cart = [];
    }
    cart.push({
      id: item.id,
      name: item.name,
      price: item.price,
      qty: 1,
      restaurantId: selectedRestaurant.id,
      restaurantName: selectedRestaurant.name,
    });
  }

  updateCartUI();
  openCart();
}

function updateCartUI() {
  const totalQty = cart.reduce((s, i) => s + i.qty, 0);
  const sub = foodTotal();
  const grand = grandTotal();

  if (cartBadgeEl) cartBadgeEl.textContent = totalQty;
  if (cartSubtotalEl) cartSubtotalEl.textContent = sub;
  if (cartTotalEl) cartTotalEl.textContent = grand;
  if (checkoutFoodTotalEl) checkoutFoodTotalEl.textContent = sub;
  if (checkoutTotalEl) checkoutTotalEl.textContent = grand;
  if (cartRestaurantNameEl) {
    cartRestaurantNameEl.textContent = cart.length
      ? `Restaurant: ${cart[0].restaurantName}`
      : "";
  }

  if (cart.length === 0) {
    cartItemsEl.innerHTML = "<p class='hint'>Your cart is empty. Add items from a menu.</p>";
    return;
  }

  cartItemsEl.innerHTML = cart
    .map(
      (i) => `
    <div class="cart-item">
      <span>${i.name} × ${i.qty}</span>
      <span>₹${i.price * i.qty}
        <button type="button" class="btn btn-small btn-danger" data-remove="${i.id}">−</button>
      </span>
    </div>
  `
    )
    .join("");

  cartItemsEl.querySelectorAll("[data-remove]").forEach((btn) => {
    btn.addEventListener("click", () => removeFromCart(btn.dataset.remove));
  });
}

function removeFromCart(menuId) {
  const idx = cart.findIndex((c) => c.id === menuId);
  if (idx === -1) return;
  if (cart[idx].qty > 1) cart[idx].qty -= 1;
  else cart.splice(idx, 1);
  updateCartUI();
}

cartToggleEl.addEventListener("click", () => {
  if (cartPanelEl.classList.contains("open")) closeCart();
  else openCart();
});
cartOverlayEl.addEventListener("click", closeCart);
document.getElementById("btn-close-cart").addEventListener("click", closeCart);

document.getElementById("btn-checkout").addEventListener("click", () => {
  if (cart.length === 0) {
    alert("Add items to cart first.");
    return;
  }
  checkoutModalEl.classList.add("show");
  closeCart();
});

document.getElementById("btn-cancel-checkout").addEventListener("click", () => {
  checkoutModalEl.classList.remove("show");
});

document.getElementById("restaurant-search").addEventListener("input", (e) => {
  searchQuery = e.target.value.trim();
  renderRestaurants();
});

document.querySelectorAll(".filter-chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    document.querySelectorAll(".filter-chip").forEach((c) => c.classList.remove("active"));
    chip.classList.add("active");
    activeFilter = chip.dataset.filter;
    renderRestaurants();
  });
});

checkoutFormEl.addEventListener("submit", async (e) => {
  e.preventDefault();

  const sub = foodTotal();
  const totalAmount = grandTotal();
  const restaurantId = cart[0].restaurantId;
  const phone = document.getElementById("customer-phone").value.trim();

  const orderPayload = {
    customer_name: document.getElementById("customer-name").value.trim(),
    customer_phone: phone,
    customer_address: document.getElementById("customer-address").value.trim(),
    restaurant_id: restaurantId,
    items: cart.map((i) => ({
      name: i.name,
      price: i.price,
      qty: i.qty,
    })),
    total_amount: totalAmount,
  };

  const msgEl = document.getElementById("checkout-message");
  msgEl.textContent = "Placing order...";
  msgEl.className = "alert alert-info";

  try {
    const orderRes = await fetch(`${API}/api/orders`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(orderPayload),
    });
    const orderData = await orderRes.json();

    if (!orderRes.ok) throw new Error(orderData.error || "Order failed");

    const orderId = orderData.order_id;
    const password = orderData.password;

    const rpRes = await fetch(`${API}/api/create-razorpay-order`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ amount: totalAmount, order_id: orderId }),
    });
    const rpData = await rpRes.json();
    if (!rpRes.ok) throw new Error(rpData.error || "Payment setup failed");

    if (rpData.demo_mode) {
      await fetch(`${API}/api/verify-payment`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ order_id: orderId, demo_mode: true }),
      });
      finishCheckout(orderId, password, phone, msgEl);
      return;
    }

    const rzp = new Razorpay({
      key: rpData.key_id,
      amount: rpData.amount,
      currency: rpData.currency,
      name: "DroneDine Hyderabad",
      description: `Order #${orderId}`,
      order_id: rpData.razorpay_order_id,
      handler: async function (response) {
        const verifyRes = await fetch(`${API}/api/verify-payment`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            order_id: orderId,
            razorpay_order_id: response.razorpay_order_id,
            razorpay_payment_id: response.razorpay_payment_id,
            razorpay_signature: response.razorpay_signature,
          }),
        });
        if (verifyRes.ok) finishCheckout(orderId, password, phone, msgEl);
        else {
          const d = await verifyRes.json();
          msgEl.textContent = d.error || "Payment verification failed";
          msgEl.className = "alert alert-error";
        }
      },
      prefill: { name: orderPayload.customer_name, contact: phone },
      theme: { color: "#1a56db" },
    });
    rzp.on("payment.failed", (resp) => {
      msgEl.textContent = "Payment failed: " + (resp.error.description || "Try again");
      msgEl.className = "alert alert-error";
    });
    rzp.open();
  } catch (err) {
    msgEl.textContent = err.message;
    msgEl.className = "alert alert-error";
  }
});

function finishCheckout(orderId, password, phone, msgEl) {
  const trackUrl = `/track?order_id=${orderId}&phone=${encodeURIComponent(phone)}`;
  msgEl.innerHTML = `
    <strong><i class="fas fa-check-circle"></i> Order #${orderId} placed!</strong><br>
    Drone password: <strong style="font-size:1.2rem;letter-spacing:0.2em">${password}</strong><br>
    <a href="${trackUrl}">Track live</a>
  `;
  msgEl.className = "alert alert-success";
  cart = [];
  updateCartUI();
  checkoutModalEl.classList.remove("show");
  unlockSectionEl.classList.remove("hidden");
  document.getElementById("unlock-order-id").value = orderId;
  unlockSectionEl.scrollIntoView({ behavior: "smooth" });
}

document.getElementById("btn-verify-password").addEventListener("click", async () => {
  const orderId = document.getElementById("unlock-order-id").value;
  const password = document.getElementById("unlock-password").value.trim();
  const msgEl = document.getElementById("unlock-message");

  if (!orderId || !/^\d{4}$/.test(password)) {
    msgEl.textContent = "Enter order ID and 4-digit password.";
    msgEl.className = "alert alert-error";
    return;
  }

  const res = await fetch(`${API}/api/verify-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ order_id: parseInt(orderId, 10), password }),
  });
  const data = await res.json();
  msgEl.textContent = data.message || data.error;
  msgEl.className = res.ok ? "alert alert-success" : "alert alert-error";
});

loadRestaurants();
