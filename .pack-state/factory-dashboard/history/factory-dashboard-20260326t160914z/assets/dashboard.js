(() => {
  const buttons = Array.from(document.querySelectorAll("[data-filter]"));
  const cards = Array.from(document.querySelectorAll("[data-truth-layer]"));
  if (!buttons.length || !cards.length) {
    return;
  }

  const applyFilter = (value) => {
    buttons.forEach((button) => {
      button.classList.toggle("is-active", button.dataset.filter === value);
    });
    cards.forEach((card) => {
      const truthLayer = card.dataset.truthLayer || "";
      const hidden = value !== "all" && truthLayer !== value;
      card.classList.toggle("hidden-by-filter", hidden);
    });
  };

  buttons.forEach((button) => {
    button.addEventListener("click", () => applyFilter(button.dataset.filter || "all"));
  });

  applyFilter("all");
})();
