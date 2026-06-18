document.addEventListener("DOMContentLoaded", () => {
  const bookingForm = document.getElementById("booking-form");
  const bookingsList = document.getElementById("bookings-list");
  const financeSummary = document.getElementById("finance-summary");
  const messageDiv = document.getElementById("message");
  const packageSelect = document.getElementById("package-size");

  function showMessage(text, type) {
    messageDiv.textContent = text;
    messageDiv.className = type;
    messageDiv.classList.remove("hidden");
  }

  function formatMoney(amount) {
    return `R${Number(amount).toFixed(2)}`;
  }

  async function fetchPackages() {
    const response = await fetch("/packages");
    const packages = await response.json();
    packageSelect.innerHTML = '<option value="">-- Select a package --</option>';

    Object.entries(packages).forEach(([name, price]) => {
      const option = document.createElement("option");
      option.value = name;
      option.textContent = `${name} (${formatMoney(price)})`;
      packageSelect.appendChild(option);
    });
  }

  function renderFinanceSummary(summary) {
    financeSummary.innerHTML = `
      <div class="summary-grid">
        <div class="summary-card"><strong>Income</strong><span>${formatMoney(summary.total_income)}</span></div>
        <div class="summary-card"><strong>Expenses</strong><span>${formatMoney(summary.total_expenses)}</span></div>
        <div class="summary-card"><strong>Net</strong><span>${formatMoney(summary.net_income)}</span></div>
        <div class="summary-card"><strong>Outstanding</strong><span>${formatMoney(summary.outstanding_balances)}</span></div>
      </div>
      <p><strong>Items:</strong> ${formatMoney(summary.expenses_by_category.items)}</p>
      <p><strong>Food:</strong> ${formatMoney(summary.expenses_by_category.food)}</p>
      <p><strong>Labour:</strong> ${formatMoney(summary.expenses_by_category.labour)}</p>
    `;
  }

  function bookingCardMarkup(booking) {
    const invoiceMarkup = booking.invoice_number
      ? `<p><strong>Invoice:</strong> ${booking.invoice_number}</p>`
      : "<p><strong>Invoice:</strong> Not created</p>";

    return `
      <div class="booking-card">
        <h4>${booking.client_name}</h4>
        <p><strong>Email:</strong> ${booking.client_email}</p>
        <p><strong>Date:</strong> ${booking.event_date}</p>
        <p><strong>Package:</strong> ${booking.package_size} (${formatMoney(booking.package_price)})</p>
        <p><strong>Payment:</strong> ${booking.payment_type.replaceAll("_", " ")}</p>
        <p><strong>Received:</strong> ${formatMoney(booking.amount_paid)}</p>
        <p><strong>Balance due:</strong> ${formatMoney(booking.balance_due)}</p>
        <p><strong>Expenses:</strong> ${formatMoney(booking.expense_total)}</p>
        ${invoiceMarkup}
        <p><strong>Reminders sent:</strong> ${booking.reminders_sent.length}</p>
        <div class="button-row">
          <button data-action="invoice" data-id="${booking.id}" type="button">Create Invoice</button>
          <button data-action="reminder" data-id="${booking.id}" type="button">Trigger Reminder</button>
        </div>
        <form class="expense-form" data-id="${booking.id}">
          <select name="category" required>
            <option value="items">Items</option>
            <option value="food">Food</option>
            <option value="labour">Labour</option>
          </select>
          <input type="text" name="description" placeholder="Expense description" required />
          <input type="number" name="amount" step="0.01" min="0.01" placeholder="Amount" required />
          <button type="submit">Add Expense</button>
        </form>
      </div>
    `;
  }

  async function refreshDashboard() {
    const [bookingsResponse, financeResponse] = await Promise.all([
      fetch("/bookings"),
      fetch("/finance/summary"),
    ]);

    const bookings = await bookingsResponse.json();
    const summary = await financeResponse.json();

    renderFinanceSummary(summary);

    if (!bookings.length) {
      bookingsList.innerHTML = "<p>No bookings yet.</p>";
      return;
    }

    bookingsList.innerHTML = bookings.map(bookingCardMarkup).join("");
  }

  bookingForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const payload = {
      client_name: document.getElementById("client-name").value,
      client_email: document.getElementById("client-email").value,
      event_date: document.getElementById("event-date").value,
      package_size: packageSelect.value,
      payment_type: document.getElementById("payment-type").value,
      amount_paid: Number(document.getElementById("amount-paid").value),
    };

    try {
      const response = await fetch("/bookings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "Failed to create booking");
      }

      showMessage(`Booking saved for ${result.client_name}.`, "success");
      bookingForm.reset();
      await refreshDashboard();
    } catch (error) {
      showMessage(error.message, "error");
    }
  });

  bookingsList.addEventListener("click", async (event) => {
    const button = event.target.closest("button[data-action]");
    if (!button) {
      return;
    }

    const bookingId = button.dataset.id;
    const action = button.dataset.action;
    const url =
      action === "invoice"
        ? `/bookings/${bookingId}/invoice`
        : `/bookings/${bookingId}/reminders/trigger`;

    try {
      const response = await fetch(url, { method: "POST" });
      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "Request failed");
      }

      showMessage(result.message || `Action completed: ${action}`, "success");
      await refreshDashboard();
    } catch (error) {
      showMessage(error.message, "error");
    }
  });

  bookingsList.addEventListener("submit", async (event) => {
    const form = event.target.closest(".expense-form");
    if (!form) {
      return;
    }

    event.preventDefault();
    const bookingId = form.dataset.id;
    const payload = {
      category: form.elements.category.value,
      description: form.elements.description.value,
      amount: Number(form.elements.amount.value),
    };

    try {
      const response = await fetch(`/bookings/${bookingId}/expenses`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "Failed to add expense");
      }

      showMessage(result.message, "success");
      await refreshDashboard();
    } catch (error) {
      showMessage(error.message, "error");
    }
  });

  Promise.all([fetchPackages(), refreshDashboard()]).catch((error) => {
    showMessage(`Failed to load the dashboard: ${error.message}`, "error");
  });
});
