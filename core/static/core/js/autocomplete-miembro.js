// core/static/js/autocomplete-miembro.js
// Componente de autocomplete reutilizable para buscar miembros

class AutocompleteMiembro {
    constructor(wrapperSelector) {
        this.wrapper = document.querySelector(wrapperSelector);
        if (!this.wrapper) return;

        this.campoId = this.wrapper.dataset.autocompleteId;
        this.inputSearch = this.wrapper.querySelector('.autocomplete-search');
        this.dropdownEl = this.wrapper.querySelector('.autocomplete-dropdown');
        this.listEl = this.wrapper.querySelector('.autocomplete-list');
        this.emptyEl = this.wrapper.querySelector('.autocomplete-empty');
        this.loadingEl = this.wrapper.querySelector('.autocomplete-loading');
        this.clearBtn = this.wrapper.querySelector('.autocomplete-clear-btn');
        this.selectedDiv = this.wrapper.querySelector('.autocomplete-selected');
        this.selectedRemoveBtn = this.wrapper.querySelector('.selected-remove');
        this.hiddenInput = this.wrapper.querySelector(`#${this.campoId}`);

        this.debounceTimer = null;
        this.debounceDelay = 300;
        this.minChars = 2;

        this.attachEventListeners();
    }

    attachEventListeners() {
        // Búsqueda con debounce
        this.inputSearch.addEventListener('input', (e) => {
            clearTimeout(this.debounceTimer);
            this.debounceTimer = setTimeout(() => {
                this.search(e.target.value);
            }, this.debounceDelay);
        });

        // Click fuera cierra dropdown
        document.addEventListener('click', (e) => {
            if (!this.wrapper.contains(e.target)) {
                this.closeDropdown();
            }
        });

        // Botón limpiar
        this.clearBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.clearSelection();
        });

        // Botón quitar selección
        if (this.selectedRemoveBtn) {
            this.selectedRemoveBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.clearSelection();
            });
        }

        // Focus en input abre dropdown si hay contenido
        this.inputSearch.addEventListener('focus', () => {
            if (this.inputSearch.value.length >= this.minChars) {
                this.dropdownEl.classList.add('open');
            }
        });

        // Navegar con teclado (Enter para seleccionar, Escape para cerrar)
        this.inputSearch.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeDropdown();
            } else if (e.key === 'Enter') {
                e.preventDefault();
                const firstItem = this.listEl.querySelector('.autocomplete-item');
                if (firstItem) {
                    this.selectItem(
                        parseInt(firstItem.dataset.id),
                        firstItem.dataset.nombre,
                        firstItem.dataset.codigo
                    );
                }
            }
        });
    }

    async search(query) {
        query = query.trim();

        // Si es muy corto, cerrar
        if (query.length < this.minChars) {
            this.closeDropdown();
            return;
        }

        // Mostrar loading
        this.showLoading();
        this.openDropdown();

        try {
            const endpoint = this.inputSearch.dataset.endpoint || '/api/buscar-miembros/';
            const filtro = this.inputSearch.dataset.filtro || 'activos';

            const response = await fetch(
                `${endpoint}?q=${encodeURIComponent(query)}&filtro=${filtro}&limit=15`,
                {
                    credentials: 'same-origin',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                }
            );

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            if (data.success && data.resultados.length > 0) {
                this.renderResults(data.resultados);
            } else {
                this.showEmpty();
            }
        } catch (error) {
            console.error('Error en búsqueda:', error);
            this.showEmpty();
        }
    }

    renderResults(resultados) {
        this.listEl.innerHTML = '';

        resultados.forEach((miembro) => {
            const item = document.createElement('li');
            item.className = 'autocomplete-item';
            item.dataset.id = miembro.id;
            item.dataset.nombre = miembro.nombre;
            item.dataset.codigo = miembro.codigo;

            item.innerHTML = `
                <div class="autocomplete-item-main">
                    <span class="autocomplete-item-nombre">${this.escapeHtml(miembro.nombre)}</span>
                    ${miembro.codigo ? `<span class="autocomplete-item-codigo">${this.escapeHtml(miembro.codigo)}</span>` : ''}
                </div>
                <div class="autocomplete-item-meta">
                    ${miembro.edad ? `<span><span class="material-icons" style="font-size: 14px;">person</span>${miembro.edad} años</span>` : ''}
                    ${miembro.telefono ? `<span><span class="material-icons" style="font-size: 14px;">phone</span>${this.escapeHtml(miembro.telefono)}</span>` : ''}
                </div>
            `;

            item.addEventListener('click', () => {
                this.selectItem(miembro.id, miembro.nombre, miembro.codigo);
            });

            this.listEl.appendChild(item);
        });

        this.emptyEl.style.display = 'none';
        this.loadingEl.style.display = 'none';
        this.listEl.style.display = 'block';
    }

    selectItem(id, nombre, codigo) {
        // Guardar ID en campo hidden
        this.hiddenInput.value = id;

        // Mostrar confirmación
        this.inputSearch.value = nombre;
        this.closeDropdown();
        this.showSelected(nombre, codigo);

        // Disparar evento personalizado para que otros componentes reaccionen
        this.wrapper.dispatchEvent(
            new CustomEvent('miembroSeleccionado', {
                detail: { id, nombre, codigo },
            })
        );
    }

    clearSelection() {
        this.hiddenInput.value = '';
        this.inputSearch.value = '';
        this.selectedDiv.style.display = 'none';
        this.listEl.innerHTML = '';
        this.closeDropdown();
        this.inputSearch.focus();

        // Disparar evento
        this.wrapper.dispatchEvent(
            new CustomEvent('miembroLimpiado', {
                detail: {},
            })
        );
    }

    showSelected(nombre, codigo) {
        this.selectedDiv.style.display = 'block';
        this.selectedDiv.querySelector('.selected-name').textContent = nombre;
        this.selectedDiv.querySelector('.selected-codigo').textContent = codigo || 'Sin código';
    }

    showLoading() {
        this.listEl.innerHTML = '';
        this.listEl.style.display = 'none';
        this.emptyEl.style.display = 'none';
        this.loadingEl.style.display = 'block';
    }

    showEmpty() {
        this.listEl.innerHTML = '';
        this.listEl.style.display = 'none';
        this.loadingEl.style.display = 'none';
        this.emptyEl.style.display = 'block';
    }

    openDropdown() {
        this.dropdownEl.classList.add('open');
    }

    closeDropdown() {
        this.dropdownEl.classList.remove('open');
    }

    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;',
        };
        return text.replace(/[&<>"']/g, (m) => map[m]);
    }
}

// Inicializar todos los autocompletes en la página
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-autocomplete-id]').forEach((wrapper) => {
        new AutocompleteMiembro(`[data-autocomplete-id="${wrapper.dataset.autocompleteId}"]`);
    });
});