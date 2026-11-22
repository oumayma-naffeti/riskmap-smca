const GOV_COLORS = {
    "brouillon": "#6b7280",
    "soumis": "#b45309",
    "approuvé": "#15803d",
    "refusé": "#b91c1c"
};

function govDate(value) {
    return value ? new Date(String(value).endsWith("Z") ? value : value + "Z").toLocaleString("fr-FR") : "";
}

function govField(id, label, value, opts = {}) {
    const { textarea = false, required = false, min = 0, full = true, disabled = false } = opts;
    const attrs = `id="${id}" ${required ? "required" : ""} ` +
                  `${min ? `minlength="${min}"` : ""} ${disabled ? "disabled" : ""}`;
    const control = textarea
        ? `<textarea ${attrs} rows="4">${escapeHTML(value)}</textarea>`
        : `<input ${attrs} value="${escapeHTML(value)}">`;
    return `<div class="form-field ${full ? "full-width" : ""}">
        <label for="${id}">${label}${required ? " *" : ""}</label>${control}</div>`;
}

async function renderGovernance() {
    const program = await API.governance();
    const canWrite = ["admin", "analyste"].includes(currentUser?.role);
    const isAdmin = currentUser?.role === "admin";
    const status = program?.approval_status ?? null;
    const submittedByMe = program && program.submitted_by === currentUser.username;
    const ro = !canWrite;

    let info = "Le programme n'a pas encore été défini.";
    if (status === "soumis") {
        info = `Soumis par ${escapeHTML(program.submitted_by)} le ${govDate(program.submitted_at)}.`;
    } else if (status === "approuvé") {
        info = `Approuvé par ${escapeHTML(program.approved_by)} le ${govDate(program.approved_at)}.`;
    } else if (status === "refusé") {
        info = "Refusé : corrigez le programme puis soumettez-le à nouveau.";
    } else if (status === "brouillon") {
        info = "Brouillon : à soumettre pour validation.";
    }

    const badge = status
        ? `<span style="background:${GOV_COLORS[status]};color:#fff;padding:3px 12px;
                 border-radius:12px;font-weight:600">${escapeHTML(status)}</span>`
        : "";

    $("governance-content").innerHTML = `
    <p style="margin-bottom:16px">${badge} ${info}</p>

    <form id="governance-form">
        <div class="process-form-grid">
            ${govField("gov-title", "Titre", program?.title ?? "Programme de continuité d'activité",
                       { required: true, min: 3, disabled: ro })}
            ${govField("gov-scope", "Périmètre", program?.scope,
                       { textarea: true, required: true, min: 10, disabled: ro })}
            ${govField("gov-objectives", "Objectifs", program?.objectives,
                       { textarea: true, required: true, min: 10, disabled: ro })}
            ${govField("gov-exclusions", "Exclusions", program?.exclusions,
                       { textarea: true, disabled: ro })}
            ${govField("gov-stakeholders", "Parties prenantes", program?.stakeholders,
                       { textarea: true, disabled: ro })}
            ${govField("gov-owner", "Responsable du programme", program?.owner,
                       { full: false, disabled: ro })}
        </div>

        <div class="process-form-actions">
            ${canWrite ? `<button type="submit" class="primary-button">Enregistrer</button>` : ""}
            ${canWrite && ["brouillon", "refusé"].includes(status)
                ? `<button type="button" id="gov-submit" class="secondary-button">
                       Soumettre pour validation</button>` : ""}
            ${isAdmin && status === "soumis"
                ? `<button type="button" id="gov-approve" class="primary-button"
                       ${submittedByMe ? "disabled" : ""}>Approuver</button>
                   <button type="button" id="gov-reject" class="danger-button">Refuser</button>` : ""}
        </div>
        ${isAdmin && status === "soumis" && submittedByMe
            ? `<p class="muted">Vous avez soumis ce programme : un autre administrateur
                   doit l'approuver (séparation des tâches).</p>` : ""}
    </form>`;

    const reload = async (message) => {
        await renderGovernance();
        showMessage(message, "success");
    };

    $("governance-form").addEventListener("submit", async event => {
        event.preventDefault();
        try {
            await API.saveGovernance({
                title: $("gov-title").value.trim(),
                scope: $("gov-scope").value.trim(),
                objectives: $("gov-objectives").value.trim(),
                exclusions: $("gov-exclusions").value.trim() || null,
                stakeholders: $("gov-stakeholders").value.trim() || null,
                owner: $("gov-owner").value.trim() || null
            });
            await reload("Programme enregistré.");
        } catch (error) {
            showMessage(error.message);
        }
    });

    const action = (id, call, okMessage) => {
        const button = $(id);
        if (!button) return;
        button.addEventListener("click", async () => {
            try {
                await call();
                await reload(okMessage);
            } catch (error) {
                showMessage(error.message);
            }
        });
    };

    action("gov-submit", () => API.submitGovernance(), "Programme soumis pour validation.");
    action("gov-approve", () => API.approveGovernance(), "Programme approuvé.");
    action("gov-reject", () => API.rejectGovernance(), "Programme refusé.");
}
