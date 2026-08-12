// Site-wide admin controls. Per-user actions live in admin.js.

function formatAmount(cents, currency) {
  if (cents === null || cents === undefined) {
    return "—";
  }
  const value = (cents / 100).toFixed(2);
  return currency ? value + " " + currency.toUpperCase() : value;
}

function loadPayments() {
  const body = document.getElementById("paymentsBody");

  fetch("/admin/payments/?limit=50", { credentials: "include" })
    .then((response) => {
      if (!response.ok) {
        throw new Error("Failed to load payments (" + response.status + ")");
      }
      return response.json();
    })
    .then((payload) => {
      const payments = payload.data || [];
      body.replaceChildren();

      if (payments.length === 0) {
        const row = document.createElement("tr");
        const cell = document.createElement("td");
        cell.colSpan = 5;
        cell.className = "muted";
        cell.textContent = "No payments recorded yet.";
        row.appendChild(cell);
        body.appendChild(row);
        return;
      }

      payments.forEach((payment) => {
        const row = document.createElement("tr");
        const cells = [
          payment.created_at.replace("T", " ").slice(0, 16),
          payment.member_name || payment.customer_email || payment.user_id,
          payment.source,
          formatAmount(payment.amount_cents, payment.currency),
          payment.note || "",
        ];
        cells.forEach((value) => {
          const cell = document.createElement("td");
          cell.textContent = value;
          row.appendChild(cell);
        });
        body.appendChild(row);
      });
    })
    .catch((err) => {
      body.replaceChildren();
      const row = document.createElement("tr");
      const cell = document.createElement("td");
      cell.colSpan = 5;
      cell.textContent = err.message;
      row.appendChild(cell);
      body.appendChild(row);
    });
}

function runMembershipReset() {
  const reason =
    document.getElementById("resetReason").value.trim() ||
    "Annual membership reset";
  const statusEl = document.getElementById("resetStatus");
  const button = document.getElementById("runReset");

  const confirmed = window.confirm(
    "This resets membership for EVERY user and cannot be undone in bulk.\n\n" +
      'Reason: "' +
      reason +
      '"\n\nContinue?',
  );
  if (!confirmed) {
    return;
  }

  button.disabled = true;
  statusEl.textContent = "Running…";

  fetch("/admin/reset_memberships/", {
    method: "POST",
    body: JSON.stringify({ reset_reason: reason }),
    headers: { "Content-Type": "application/json" },
    credentials: "include",
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error("Request failed (" + response.status + ")");
      }
      return response.json();
    })
    .then((data) => {
      // This endpoint returns HTTP 200 even when the reset fails, so the
      // success flag in the body is what actually matters.
      if (!data.success) {
        throw new Error(data.error || "Reset failed");
      }
      statusEl.textContent =
        "Reset " +
        data.reset_count +
        " users, archived " +
        data.archived_count +
        ".";
      setTimeout(() => window.location.reload(), 1500);
    })
    .catch((err) => {
      statusEl.textContent = err.message;
      button.disabled = false;
    });
}

document.addEventListener("DOMContentLoaded", () => {
  loadPayments();
  document.getElementById("runReset").onclick = runMembershipReset;
});
