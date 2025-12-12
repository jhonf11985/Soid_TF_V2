// finanzas_app/static/finanzas_app/js/adjuntos.js

/**
 * Manejo de adjuntos para movimientos financieros
 */

class AdjuntosManager {
    constructor(movimientoId, containerId = 'attach-list', inputId = 'attachment-input') {
        this.movimientoId = movimientoId;
        this.container = document.getElementById(containerId);
        this.input = document.getElementById(inputId);
        this.archivosTemporales = [];
        
        if (!this.container || !this.input) {
            console.error('Container o input de adjuntos no encontrado');
            return;
        }
        
        this.init();
    }
    
    init() {
        // Si hay movimientoId, cargar adjuntos existentes
        if (this.movimientoId) {
            this.cargarAdjuntos();
        }
        
        // Listener para cambios en el input
        this.input.addEventListener('change', (e) => this.handleFileSelect(e));
    }
    
    async cargarAdjuntos() {
        try {
            const response = await fetch(`/finanzas/adjuntos/movimiento/${this.movimientoId}/listar/`);
            const data = await response.json();
            
            if (data.success && data.adjuntos.length > 0) {
                data.adjuntos.forEach(adjunto => this.renderAdjunto(adjunto, true));
            }
        } catch (error) {
            console.error('Error al cargar adjuntos:', error);
        }
    }
    
    handleFileSelect(e) {
        const files = Array.from(e.target.files);
        
        files.forEach(file => {
            // Validación básica en cliente
            if (file.size > 10 * 1024 * 1024) {
                this.mostrarError(`El archivo "${file.name}" es demasiado grande (máx 10MB)`);
                return;
            }
            
            // Si ya hay movimientoId, subir inmediatamente
            if (this.movimientoId) {
                this.subirArchivo(file);
            } else {
                // Si no hay movimiento aún, guardar temporalmente
                this.archivosTemporales.push(file);
                this.renderArchivoTemporal(file);
            }
        });
        
        // Limpiar input
        e.target.value = '';
    }
    
    async subirArchivo(file) {
        const formData = new FormData();
        formData.append('archivo', file);
        
        // Añadir token CSRF
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        
        try {
            // Mostrar loader
            const loaderId = this.mostrarLoader(file.name);
            
            const response = await fetch(`/finanzas/adjuntos/movimiento/${this.movimientoId}/subir/`, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': csrfToken,
                },
            });
            
            const data = await response.json();
            
            // Quitar loader
            this.quitarLoader(loaderId);
            
            if (data.success) {
                this.renderAdjunto(data.adjunto, true);
                this.mostrarExito(`Archivo "${file.name}" subido correctamente`);
            } else {
                this.mostrarError(data.error || 'Error al subir archivo');
            }
        } catch (error) {
            console.error('Error al subir archivo:', error);
            this.mostrarError(`Error al subir "${file.name}"`);
        }
    }
    
    async eliminarAdjunto(adjuntoId, nombre) {
        if (!confirm(`¿Eliminar el archivo "${nombre}"?`)) {
            return;
        }
        
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        
        try {
            const response = await fetch(`/finanzas/adjuntos/${adjuntoId}/eliminar/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                },
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Remover del DOM
                const elemento = document.querySelector(`[data-adjunto-id="${adjuntoId}"]`);
                if (elemento) {
                    elemento.remove();
                }
                this.mostrarExito(data.mensaje);
            } else {
                this.mostrarError(data.error || 'Error al eliminar archivo');
            }
        } catch (error) {
            console.error('Error al eliminar archivo:', error);
            this.mostrarError('Error al eliminar archivo');
        }
    }
    
    renderAdjunto(adjunto, esServidor = false) {
        const item = document.createElement('div');
        item.className = 'odoo-attach-item';
        item.dataset.adjuntoId = adjunto.id;
        
        // Si es imagen, mostrar preview
        let contenido = '';
        if (adjunto.es_imagen && adjunto.url_imagen) {
            contenido = `
                <a href="${adjunto.url_descarga}" target="_blank" class="attach-image-preview">
                    <img src="${adjunto.url_imagen}" alt="${adjunto.nombre}" />
                </a>
            `;
        } else {
            contenido = `
                <span class="material-icons">${adjunto.icono}</span>
                <a href="${adjunto.url_descarga}" class="odoo-attach-item-name" title="${adjunto.nombre}" target="_blank">
                    ${this.truncate(adjunto.nombre, 30)}
                </a>
            `;
        }
        
        item.innerHTML = `
            ${contenido}
            <span class="odoo-attach-item-size">${adjunto.tamaño}</span>
            ${adjunto.puede_eliminar ? `
                <button type="button" class="odoo-attach-remove" title="Eliminar" data-id="${adjunto.id}" data-nombre="${adjunto.nombre}">
                    <span class="material-icons">close</span>
                </button>
            ` : ''}
        `;
        
        // Event listener para eliminar
        if (adjunto.puede_eliminar) {
            const btnEliminar = item.querySelector('.odoo-attach-remove');
            btnEliminar.addEventListener('click', () => {
                this.eliminarAdjunto(adjunto.id, adjunto.nombre);
            });
        }
        
        this.container.appendChild(item);
    }
    
    renderArchivoTemporal(file) {
        const item = document.createElement('div');
        item.className = 'odoo-attach-item odoo-attach-temporal';
        item.dataset.fileName = file.name;
        
        const icono = this.getIconoByExtension(file.name);
        const tamaño = this.formatFileSize(file.size);
        
        item.innerHTML = `
            <span class="material-icons">${icono}</span>
            <span class="odoo-attach-item-name" title="${file.name}">
                ${this.truncate(file.name, 30)}
            </span>
            <span class="odoo-attach-item-size">${tamaño}</span>
            <button type="button" class="odoo-attach-remove" title="Quitar">
                <span class="material-icons">close</span>
            </button>
        `;
        
        // Event listener para quitar temporal
        const btnRemove = item.querySelector('.odoo-attach-remove');
        btnRemove.addEventListener('click', () => {
            this.quitarArchivoTemporal(file.name);
            item.remove();
        });
        
        this.container.appendChild(item);
    }
    
    quitarArchivoTemporal(fileName) {
        this.archivosTemporales = this.archivosTemporales.filter(f => f.name !== fileName);
    }
    
    async subirArchivosPendientes(movimientoId) {
        this.movimientoId = movimientoId;
        
        for (const file of this.archivosTemporales) {
            await this.subirArchivo(file);
        }
        
        this.archivosTemporales = [];
        
        // Limpiar items temporales del DOM
        document.querySelectorAll('.odoo-attach-temporal').forEach(el => el.remove());
    }
    
    mostrarLoader(nombre) {
        const id = `loader-${Date.now()}`;
        const item = document.createElement('div');
        item.className = 'odoo-attach-item odoo-attach-loading';
        item.id = id;
        
        item.innerHTML = `
            <span class="material-icons spinner">sync</span>
            <span class="odoo-attach-item-name">${this.truncate(nombre, 30)}</span>
            <span class="odoo-attach-item-size">Subiendo...</span>
        `;
        
        this.container.appendChild(item);
        return id;
    }
    
    quitarLoader(loaderId) {
        const loader = document.getElementById(loaderId);
        if (loader) {
            loader.remove();
        }
    }
    
    mostrarExito(mensaje) {
        // Puedes implementar tu sistema de notificaciones
        console.log('✓', mensaje);
    }
    
    mostrarError(mensaje) {
        // Puedes implementar tu sistema de notificaciones
        console.error('✗', mensaje);
        alert(mensaje);
    }
    
    // Utilidades
    getIconoByExtension(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        const iconos = {
            'pdf': 'picture_as_pdf',
            'doc': 'description',
            'docx': 'description',
            'xls': 'table_chart',
            'xlsx': 'table_chart',
            'jpg': 'image',
            'jpeg': 'image',
            'png': 'image',
            'gif': 'image',
        };
        return iconos[ext] || 'insert_drive_file';
    }
    
    formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }
    
    truncate(str, maxLen) {
        if (str.length <= maxLen) return str;
        return str.substring(0, maxLen - 3) + '...';
    }
}

// Hacer disponible globalmente
window.AdjuntosManager = AdjuntosManager;   