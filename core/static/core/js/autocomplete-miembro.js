// core/static/core/js/autocomplete-miembro.js
// Autocomplete estándar Soid_tf_2 (igual a Ingreso/Egreso: chip + dropdown bonito)

(function () {
  "use strict";

  const DEFAULTS = {
    endpoint: "/api/buscar-miembros/",
    filtro: "activos",
    limit: 15,
    minChars: 2,
    debounce: 300,
  };

  function escapeHtml(text) {
    if (text === null || text === undefined) return "";
    const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" };
    return String(text).replace(/[&<>"']/g, (m) => map[m]);
  }

  function getInitials(nombre) {
    if (!nombre) return "?";
    const parts = nombre.trim().split(/\s+/).filter(Boolean);
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
    return nombre.trim().substring(0, 2).toUpperCase();
  }

  class AutocompleteMiembro {
    constructor(wrapper) {
      this.wrapper = wrapper;

      // Config por dataset (opcional)
      this.endpoint = wrapper.dataset.endpoint || DEFAULTS.endpoint;
      this.filtro = wrapper.dataset.filtro || DEFAULTS.filtro;
      this.limit = parseInt(wrapper.dataset.limit || DEFAULTS.limit, 10);
      this.minChars = parseInt(wrapper.dataset.minChars || DEFAULTS.minChars, 10);
      this.debounceDelay = parseInt(wrapper.dataset.debounce || DEFAULTS.debounce, 10);

      // Elementos básicos por clases (estándar)
      this.searchInput = wrapper.querySelector(".autocomplete-search");
      this.dropdown = wrapper.querySelector(".autocomplete-dropdown");
      this.listEl = wrapper.querySelector(".autocomplete-list");
      this.emptyEl = wrapper.querySelector(".autocomplete-empty");
      this.loadingEl = wrapper.querySelector(".autocomplete-loading");
      this.clearBtn = wrapper.querySelector(".autocomplete-clear-btn"); // opcional
      this.fieldContainer = wrapper.querySelector(".autocomplete-field");

      // Hidden input:
      // 1) si existe .autocomplete-hidden, úsalo
      // 2) si no, usa data-autocomplete-id como id del hidden (tu forma actual)
      this.hiddenInput =
        wrapper.querySelector(".autocomplete-hidden") ||
        (wrapper.dataset.autocompleteId
          ? document.getElementById(wrapper.dataset.autocompleteId)
          : null) ||
        wrapper.querySelector('input[type="hidden"]');

      // Chip (modo ingreso/egreso)
      this.chip = wrapper.querySelector(".autocomplete-chip");
      this.chipAvatar = wrapper.querySelector(".chip-avatar");
      this.chipName = wrapper.querySelector(".chip-name");
      this.chipCode = wrapper.querySelector(".chip-code");
      this.chipRemove = wrapper.querySelector(".chip-remove");
      this.hasChip = !!this.chip;

      this.debounceTimer = null;

      if (!this.searchInput || !this.dropdown || !this.listEl || !this.hiddenInput) {
        // Markup incompleto
        return;
      }

      this.bind();
    }

    bind() {
      this.searchInput.addEventListener("input", (e) => {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => {
          this.search(e.target.value || "");
        }, this.debounceDelay);
      });

      this.searchInput.addEventListener("focus", () => {
        if ((this.searchInput.value || "").length >= this.minChars) {
          this.openDropdown();
        }
      });

      this.searchInput.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
          this.closeDropdown();
        } else if (e.key === "Enter") {
          e.preventDefault();
          const firstItem = this.listEl.querySelector(".autocomplete-item");
          if (firstItem) {
            this.selectMiembro(firstItem.dataset.id, firstItem.dataset.nombre, firstItem.dataset.codigo);
          }
        }
      });

      if (this.chipRemove) {
        this.chipRemove.addEventListener("click", (e) => {
          e.preventDefault();
          e.stopPropagation();
          this.clearSelection();
        });
      }

      // OJO: este botón es opcional, nunca debe romper
      if (this.clearBtn) {
        this.clearBtn.addEventListener("click", (e) => {
          e.preventDefault();
          e.stopPropagation();
          this.clearSelection();
        });
      }

      document.addEventListener("click", (e) => {
        if (!this.wrapper.contains(e.target)) this.closeDropdown();
      });
    }

    async search(query) {
      query = (query || "").trim();

      if (query.length < this.minChars) {
        this.closeDropdown();
        return;
      }

      this.showLoading();

      try {
        const url =
          `${this.endpoint}?q=${encodeURIComponent(query)}` +
          `&filtro=${encodeURIComponent(this.filtro)}` +
          `&limit=${encodeURIComponent(this.limit)}`;

        const response = await fetch(url, {
          credentials: "same-origin",
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();

        if (data.success && Array.isArray(data.resultados) && data.resultados.length > 0) {
          this.renderResults(data.resultados);
        } else {
          this.showEmpty();
        }
      } catch (err) {
        console.error("AutocompleteMiembro error:", err);
        this.showEmpty();
      }
    }

    renderResults(resultados) {
      this.listEl.innerHTML = "";

      resultados.forEach((miembro) => {
        const li = document.createElement("li");
        li.className = "autocomplete-item";
        li.dataset.id = String(miembro.id);
        li.dataset.nombre = miembro.nombre || "";
        li.dataset.codigo = miembro.codigo || "";

        const initials = getInitials(miembro.nombre || "");

        // HTML idéntico a Ingreso/Egreso
        li.innerHTML = `
          <div class="autocomplete-item-avatar">${escapeHtml(initials)}</div>
          <div class="autocomplete-item-info">
            <div class="autocomplete-item-name">${escapeHtml(miembro.nombre || "")}</div>
            <div class="autocomplete-item-meta">
              ${miembro.codigo ? `<span class="autocomplete-item-code">${escapeHtml(miembro.codigo)}</span>` : ""}
              ${miembro.telefono && miembro.telefono !== "—" ? `<span>${escapeHtml(miembro.telefono)}</span>` : ""}
            </div>
          </div>
        `;

        li.addEventListener("click", () => {
          this.selectMiembro(miembro.id, miembro.nombre, miembro.codigo);
        });

        this.listEl.appendChild(li);
      });

      if (this.loadingEl) this.loadingEl.style.display = "none";
      if (this.emptyEl) this.emptyEl.style.display = "none";
      this.listEl.style.display = "block";
      this.openDropdown();
    }

    selectMiembro(id, nombre, codigo) {
      this.hiddenInput.value = String(id);

      if (this.hasChip) {
        if (this.chipAvatar) this.chipAvatar.textContent = getInitials(nombre || "");
        if (this.chipName) this.chipName.textContent = nombre || "";
        if (this.chipCode) this.chipCode.textContent = (codigo || "Sin código");

        this.chip.style.display = "inline-flex";
        this.searchInput.value = "";
        this.searchInput.style.display = "none";
        if (this.fieldContainer) this.fieldContainer.classList.add("has-selection");
      } else {
        // Si no hay chip, rellenamos input
        this.searchInput.value = nombre || "";
      }

      this.closeDropdown();

      this.wrapper.dispatchEvent(
        new CustomEvent("miembroSeleccionado", { detail: { id, nombre, codigo } })
      );
    }

    clearSelection() {
      this.hiddenInput.value = "";

      if (this.hasChip && this.chip) {
        this.chip.style.display = "none";
        this.searchInput.style.display = "";
        if (this.fieldContainer) this.fieldContainer.classList.remove("has-selection");
      }

      this.searchInput.value = "";
      this.listEl.innerHTML = "";
      this.closeDropdown();
      this.searchInput.focus();

      this.wrapper.dispatchEvent(new CustomEvent("miembroLimpiado", { detail: {} }));
    }

    showLoading() {
      this.listEl.innerHTML = "";
      this.listEl.style.display = "none";
      if (this.emptyEl) this.emptyEl.style.display = "none";
      if (this.loadingEl) this.loadingEl.style.display = "block";
      this.openDropdown();
    }

    showEmpty() {
      this.listEl.innerHTML = "";
      this.listEl.style.display = "none";
      if (this.loadingEl) this.loadingEl.style.display = "none";
      if (this.emptyEl) this.emptyEl.style.display = "block";
      this.openDropdown();
    }

    openDropdown() {
      this.dropdown.classList.add("open");
    }

    closeDropdown() {
      this.dropdown.classList.remove("open");
      if (this.loadingEl) this.loadingEl.style.display = "none";
      if (this.emptyEl) this.emptyEl.style.display = "none";
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-autocomplete-id]").forEach((wrapper) => {
      if (wrapper.dataset.autocompleteInit === "1") return;
      wrapper.dataset.autocompleteInit = "1";
      new AutocompleteMiembro(wrapper);
    });
  });
})();
