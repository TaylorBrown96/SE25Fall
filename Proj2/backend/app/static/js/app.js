document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("generate");
  const status = document.getElementById("status");
  if (btn && status) {
    btn.addEventListener("click", () => {
      status.textContent = "Generating (stub)…";
      setTimeout(() => (status.textContent = "Ready"), 600);
    });
  }
});
