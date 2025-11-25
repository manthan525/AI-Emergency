async function sendEmergency(type) {
  const toast = document.getElementById("emergency-toast");
  try {
    const res = await fetch("/emergency", {
      method: "POST",
      headers: {"Content-Type": "application/x-www-form-urlencoded"},
      body: "type=" + encodeURIComponent(type)
    });
    const data = await res.json();
    toast.textContent = data.message || "Request sent.";
  } catch (e) {
    toast.textContent = "Failed to send request.";
  }
  toast.classList.remove("hidden");
  setTimeout(() => toast.classList.add("hidden"), 3000);
}

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("symptom-form");
  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const formData = new FormData(form);
      const payload = {
        symptoms: formData.get("symptoms"),
        duration: formData.get("duration"),
        severity: formData.get("severity")
      };
      const resultCard = document.getElementById("result-card");
      const levelEl = document.getElementById("risk-level");
      const msgEl = document.getElementById("risk-message");
      levelEl.textContent = "Checking...";
      msgEl.textContent = "";
      resultCard.classList.remove("hidden");

      const res = await fetch("/api/check-symptoms", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      levelEl.textContent = data.risk_level + " risk";
      msgEl.textContent = data.message;
      resultCard.className = "result-card";
      if (data.risk_level === "High") {
        resultCard.classList.add("gradient-orange");
      } else if (data.risk_level === "Medium") {
        resultCard.classList.add("gradient-green");
      } else {
        resultCard.classList.add("gradient-blue");
      }
    });
  }
});
