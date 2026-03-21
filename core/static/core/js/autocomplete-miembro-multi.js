// core/static/core/js/autocomplete-miembro-multi.js
// Autocomplete MULTI-SELECT con badges para SOID
// Permite seleccionar múltiples miembros que aparecen como badges removibles

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

  class AutocompleteMiembroMulti {
    constructor(wrapper) {
      this.wrapper = wrapper;

      // Config por dataset
      this.endpoint = wrapper.dataset.endpoint || DEFAULTS.endpoint;
      this.filtro = wrapper.dataset.filtro || DEFAULTS.filtro;
      this.limit = parseInt(wrapper.dataset.limit || DEFAULTS.limit, 10);
      this.minChars = parseInt(wrapper.dataset.minChars || DEFAULTS.minChars, 10);
      this.debounceDelay = parseInt(wrapper.dataset.debounce || DEFAULTS.debounce, 10);

      // Elementos
      this.searchInput = wrapper.querySelector(".autocomplete-search");
      this.dropdown = wrapper.querySelector(".autocomplete-dropdown");
      this.listEl = wrapper.querySelector(".autocomplete-list");
      this.emptyEl = wrapper.querySelector(".autocomplete-empty");
      this.loadingEl = wrapper.querySelector(".autocomplete-loading");
      this.badgesContainer = wrapper.querySelector(".autocomplete-badges");

      // Hidden input para guardar IDs separados por coma
      this.hiddenInput =
        wrapper.querySelector(".autocomplete-hidden") ||
        (wrapper.dataset.autocompleteId
          ? document.getElementById(wrapper.dataset.autocompleteId)
          : null);

      // Array de miembros seleccionados: [{id, nombre, codigo}, ...]
      this.selected = [];

      this.debounceTimer = null;

      if (!this.searchInput || !this.dropdown || !this.listEl || !this.hiddenInput) {
        console.warn("AutocompleteMiembroMulti: markup incompleto", wrapper);
        return;
      }

      // Cargar selección inicial si existe valor en hidden
      this.loadInitialSelection();

      this.bind();
    }

    loadInitialSelection() {
      // Si hay nombres precargados (del servidor), parsearlos
      // Formato esperado en data-initial: JSON array [{id, nombre}, ...]
      const initialData = this.wrapper.dataset.initial;
      if (initialData) {
        try {
          const parsed = JSON.parse(initialData);
          if (Array.isArray(parsed)) {
            parsed.forEach((m) => {
              if (m.id && m.nombre) {
                this.selected.push({
                  id: String(m.id),
                  nombre: m.nombre,
                  codigo: m.codigo || "",
                });
              }
            });
            this.renderBadges();
            this.updateHiddenInput();
          }
        } catch (e) {
          console.warn("Error parseando data-initial:", e);
        }
      }
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
          const firstItem = this.listEl.querySelector(".autocomplete-item:not(.disabled)");
          if (firstItem) {
            this.addMiembro(firstItem.dataset.id, firstItem.dataset.nombre, firstItem.dataset.codigo);
          }
        } else if (e.key === "Backspace" && !this.searchInput.value && this.selected.length > 0) {
          // Borrar último badge con backspace si input vacío
          this.removeMiembro(this.selected[this.selected.length - 1].id);
        }
      });

      // Delegación de eventos para badges (remover)
      this.badgesContainer.addEventListener("click", (e) => {
        const removeBtn = e.target.closest(".badge-remove");
        if (removeBtn) {
          e.preventDefault();
          e.stopPropagation();
          const badge = removeBtn.closest(".autocomplete-badge");
          if (badge && badge.dataset.id) {
            this.removeMiembro(badge.dataset.id);
          }
        }
      });

      // Click fuera cierra dropdown
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
        console.error("AutocompleteMiembroMulti error:", err);
        this.showEmpty();
      }
    }

    renderResults(resultados) {
      this.listEl.innerHTML = "";
      const selectedIds = this.selected.map((s) => String(s.id));

      resultados.forEach((miembro) => {
        const li = document.createElement("li");
        const isSelected = selectedIds.includes(String(miembro.id));

        li.className = "autocomplete-item" + (isSelected ? " disabled" : "");
        li.dataset.id = String(miembro.id);
        li.dataset.nombre = miembro.nombre || "";
        li.dataset.codigo = miembro.codigo || "";

        const initials = getInitials(miembro.nombre || "");

        li.innerHTML = `
          <div class="autocomplete-item-avatar">${escapeHtml(initials)}</div>
          <div class="autocomplete-item-info">
            <div class="autocomplete-item-name">${escapeHtml(miembro.nombre || "")}</div>
            <div class="autocomplete-item-meta">
              ${miembro.codigo ? `<span class="autocomplete-item-code">${escapeHtml(miembro.codigo)}</span>` : ""}
              ${miembro.telefono && miembro.telefono !== "—" ? `<span>${escapeHtml(miembro.telefono)}</span>` : ""}
            </div>
          </div>
          ${isSelected ? '<span class="autocomplete-item-check">✓</span>' : ""}
        `;

        if (!isSelected) {
          li.addEventListener("click", () => {
            this.addMiembro(miembro.id, miembro.nombre, miembro.codigo);
          });
        }

        this.listEl.appendChild(li);
      });

      if (this.loadingEl) this.loadingEl.style.display = "none";
      if (this.emptyEl) this.emptyEl.style.display = "none";
      this.listEl.style.display = "block";
      this.openDropdown();
    }

    addMiembro(id, nombre, codigo) {
      const idStr = String(id);

      // Evitar duplicados
      if (this.selected.some((s) => s.id === idStr)) {
        return;
      }

      this.selected.push({ id: idStr, nombre: nombre || "", codigo: codigo || "" });

      this.renderBadges();
      this.updateHiddenInput();

      // Limpiar input y cerrar dropdown
      this.searchInput.value = "";
      this.closeDropdown();
      this.searchInput.focus();

      // Evento personalizado
      this.wrapper.dispatchEvent(
        new CustomEvent("miembroAgregado", { detail: { id: idStr, nombre, codigo } })
      );
    }

    removeMiembro(id) {
      const idStr = String(id);
      const idx = this.selected.findIndex((s) => s.id === idStr);

      if (idx === -1) return;

      const removed = this.selected.splice(idx, 1)[0];

      this.renderBadges();
      this.updateHiddenInput();

      // Evento personalizado
      this.wrapper.dispatchEvent(
        new CustomEvent("miembroRemovido", { detail: { id: idStr, nombre: removed.nombre } })
      );
    }

    renderBadges() {
      this.badgesContainer.innerHTML = "";

      this.selected.forEach((miembro) => {
        const badge = document.createElement("span");
        badge.className = "autocomplete-badge";
        badge.dataset.id = miembro.id;

        badge.innerHTML = `
          <span class="badge-avatar">${escapeHtml(getInitials(miembro.nombre))}</span>
          <span class="badge-name">${escapeHtml(miembro.nombre)}</span>
          <button type="button" class="badge-remove" title="Remover">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        `;

        this.badgesContainer.appendChild(badge);
      });
    }

    updateHiddenInput() {
      // Guardar IDs separados por coma
      this.hiddenInput.value = this.selected.map((s) => s.id).join(",");
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

    // Método público para obtener seleccionados
    getSelected() {
      return [...this.selected];
    }

    // Método público para limpiar todo
    clear() {
      this.selected = [];
      this.renderBadges();
      this.updateHiddenInput();
      this.searchInput.value = "";
    }
  }

  // Auto-inicialización
  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-autocomplete-multi]").forEach((wrapper) => {
      if (wrapper.dataset.autocompleteMultiInit === "1") return;
      wrapper.dataset.autocompleteMultiInit = "1";
      const instance = new AutocompleteMiembroMulti(wrapper);
      // Guardar referencia para acceso externo
      wrapper._autocompleteMulti = instance;
    });
  });

  // Exponer clase globalmente para uso manual
  window.AutocompleteMiembroMulti = AutocompleteMiembroMulti;
})();