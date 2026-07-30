document.querySelectorAll("[data-review-form]").forEach((form) => {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = event.submitter;
    const status = form.querySelector(".form-status");
    const fields = new FormData(form);
    const payload = {
      action: button.value,
      reviewer: fields.get("reviewer"),
      rationale: fields.get("rationale"),
      canonical_product_id: null,
    };

    form.querySelectorAll("button").forEach((item) => {
      item.disabled = true;
    });
    status.textContent = "Saving decision…";

    try {
      const response = await fetch(
        `/api/v1/reviews/${form.dataset.proposalId}/decisions`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      );
      if (!response.ok) {
        const problem = await response.json();
        throw new Error(problem.detail || "Decision could not be saved.");
      }
      status.textContent = "Decision saved. Returning to the queue…";
      window.setTimeout(() => {
        window.location.assign("/review");
      }, 500);
    } catch (error) {
      status.textContent = error.message;
      form.querySelectorAll("button").forEach((item) => {
        item.disabled = false;
      });
    }
  });
});

