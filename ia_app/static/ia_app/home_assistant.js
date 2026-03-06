// ia_app/static/ia_app/home_assistant.js
(function () {
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(";").shift();
    return null;
  }

  function el(id) {
    return document.getElementById(id);
  }

  function escapeHtml(str) {
    return (str || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  async function runQuery(text) {
    const status = el("soidAssistantStatus");
    const results = el("soidAssistantResults");
    const btn = el("soidAssistantBtn");
    const input = el("soidAssistantInput");

    if (!text) {
      status.textContent = "Escribe una consulta.";
      return;
    }

    status.textContent = "Buscando...";
    results.innerHTML = "";
    btn.disabled = true;
    input.disabled = true;

    try {
      const csrftoken = getCookie("csrftoken");

      const resp = await fetch("/ia/nl-query/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrftoken || "",
        },
        body: JSON.stringify({ text }),
      });

      const data = await resp.json().catch(() => ({}));

      if (!resp.ok || !data.ok) {
        status.textContent = data.message || "No se pudo completar la consulta.";
        return;
      }

      status.textContent = data.message || "Listo.";

      const miembros = (data.data && data.data.miembros) ? data.data.miembros : [];
      const dateField = (data.data && data.data.date_field) ? data.data.date_field : null;

      if (!miembros.length) {
        results.innerHTML = `<div class="soid-assistant__empty">No encontré resultados.</div>`;
        return;
      }

      // Render simple tipo “tabla”
      const rows = miembros.map((m) => {
        const nombre = `${m.nombres || ""} ${m.apellidos || ""}`.trim();
        const fecha = dateField ? (m[dateField] || "") : "";
        return `
          <div class="soid-row">
            <div class="soid-row__main">
              <div class="soid-row__name">${escapeHtml(nombre || "—")}</div>
              <div class="soid-row__meta">${fecha ? "Fecha: " + escapeHtml(fecha) : ""}</div>
            </div>
            <a class="soid-row__btn" href="/miembros/editar/${m.id}/">Ver</a>
          </div>
        `;
      }).join("");

      results.innerHTML = `<div class="soid-list">${rows}</div>`;
    } catch (e) {
      status.textContent = "Error de conexión.";
    } finally {
      btn.disabled = false;
      input.disabled = false;
      input.focus();
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    const input = el("soidAssistantInput");
    const btn = el("soidAssistantBtn");
    const container = el("soidAssistant");

    if (!input || !btn || !container) return;

    btn.addEventListener("click", function () {
      runQuery(input.value.trim());
    });

    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        runQuery(input.value.trim());
      }
    });

    container.querySelectorAll(".soid-chip").forEach((chip) => {
      chip.addEventListener("click", function () {
        const q = chip.getAttribute("data-q") || "";
        input.value = q;
        runQuery(q);
      });
    });
  });
})();