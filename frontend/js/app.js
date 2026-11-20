const $ = (id) => document.getElementById(id);

let currentUser = null;
let appData = {
    processes: [],
    assets: [],
    risks: [],
    treatments: [],
    bia: []
};

const titles = {
    dashboard: "Tableau de bord",
    processes: "Processus métier",
    assets: "Actifs",
    risks: "Cartographie des risques",
    matrix: "Matrice des risques",
    treatments: "Traitement des risques",
    bia: "Analyse d’impact métier (BIA)",
    audit: "Journal d'audit"
};

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;",
        '"': "&quot;", "'": "&#39;"
    })[char]);
}

function showMessage(message, type = "error") {
    const el = $("global-message");
    el.textContent = message;
    el.className = `message ${type}`;
    el.classList.remove("hidden");
}

function hideMessage() {
    $("global-message").classList.add("hidden");
}

function showApp(user) {
    currentUser = user;
    $("login-page").classList.add("hidden");
    $("app-page").classList.remove("hidden");

    $("sidebar-username").textContent = user.username;
    $("sidebar-role").textContent = user.role;
    $("user-avatar").textContent = user.username[0].toUpperCase();
    $("current-username").textContent = user.username;
    $("current-role").textContent = user.role;
    $("nav-audit").classList.toggle("hidden", user.role !== "admin");

    loadDashboard();
}

function showLogin() {
    API.clearToken();
    currentUser = null;
    $("app-page").classList.add("hidden");
    $("login-page").classList.remove("hidden");
}

function levelClass(level) {
    return {
        "Faible": "faible",
        "Moyen": "moyen",
        "Élevé": "eleve",
        "Critique": "critique"
    }[level] || "";
}

function levelBadge(level) {
    return `<span class="badge ${levelClass(level)}">${escapeHTML(level)}</span>`;
}

function processName(id) {
    return appData.processes.find(p => p.id === id)?.name || `Processus #${id}`;
}

function assetName(id) {
    return appData.assets.find(a => a.id === id)?.name || "Non associé";
}

function renderDashboard() {
    const { processes, assets, risks, bia } = appData;

    const biaLevels = bia.map(item => Math.max(
        item.financial_impact,
        item.operational_impact,
        item.legal_impact,
        item.reputational_impact
    ));

    $("stat-bia-total").textContent = bia.length;
    $("stat-bia-critical").textContent =
        biaLevels.filter(level => level === 5).length;
    $("stat-bia-high").textContent =
        biaLevels.filter(level => level === 4).length;
    $("stat-bia-moderate").textContent =
        biaLevels.filter(level => level <= 3).length;

    const biaLabels = {
        1: "Très faible",
        2: "Faible",
        3: "Moyen",
        4: "Élevé",
        5: "Critique"
    };

    const biaMax = Math.max(1, ...[1, 2, 3, 4, 5].map(
        level => biaLevels.filter(value => value === level).length
    ));

    $("bia-distribution").innerHTML = [1, 2, 3, 4, 5].map(level => {
        const count = biaLevels.filter(value => value === level).length;
        const barLength = count === 0
            ? 0
            : Math.max(1, Math.round((count / biaMax) * 20));

        return `
            <div class="distribution-row">
                <span>${biaLabels[level]}</span>
                <span class="bia-bar" aria-label="${count} analyse(s)">
                    ${"█".repeat(barLength) || "—"}
                </span>
                <strong>${count}</strong>
            </div>
        `;
    }).join("");

    $("stat-processes").textContent = processes.length;
    $("stat-assets").textContent = assets.length;
    $("stat-risks").textContent = risks.length;
    $("stat-critical").textContent =
        risks.filter(r => r.level === "Critique").length;

    const levels = ["Faible", "Moyen", "Élevé", "Critique"];
    $("risk-distribution").innerHTML = levels.map(level => {
        const count = risks.filter(r => r.level === level).length;
        return `<div class="distribution-row">
            <span>${levelBadge(level)}</span>
            <strong>${count}</strong>
        </div>`;
    }).join("");

    $("recent-risks").innerHTML = risks.slice(0, 5).map(r => `
        <tr>
            <td>#${r.id}</td>
            <td>${escapeHTML(r.threat)}</td>
            <td>${escapeHTML(processName(r.process_id))}</td>
            <td>${r.score}</td>
            <td>${levelBadge(r.level)}</td>
        </tr>
    `).join("") || `<tr><td colspan="5">Aucun risque enregistré</td></tr>`;
}

function renderProcesses() {
    const canWrite = ["admin", "analyste"].includes(currentUser?.role);
    const isAdmin = currentUser?.role === "admin";

    $("processes-content").innerHTML = `
    ${canWrite ? `
    <div class="process-form-card">
        <h3 id="process-form-title">Ajouter un processus</h3>

        <form id="process-form">
            <input type="hidden" id="process-id">

            <div class="process-form-grid">
                <div class="form-field">
                    <label for="process-name">Nom du processus *</label>
                    <input id="process-name" name="name"
                           type="text" minlength="2" maxlength="120" required
                           placeholder="Ex : Gestion des commandes">
                </div>

                <div class="form-field">
                    <label for="process-criticality">Criticité *</label>
                    <select id="process-criticality" required>
                        <option value="1">1 - Très faible</option>
                        <option value="2">2 - Faible</option>
                        <option value="3" selected>3 - Moyenne</option>
                        <option value="4">4 - Élevée</option>
                        <option value="5">5 - Critique</option>
                    </select>
                </div>

                <div class="form-field full-width">
                    <label for="process-description">Description</label>
                    <textarea id="process-description" rows="2"
                              placeholder="Description du processus"></textarea>
                </div>

                <div class="form-field">
                    <label for="process-mtpd">MTPD (heures)</label>
                    <input id="process-mtpd" type="number" min="0"
                           step="0.5" placeholder="Ex : 24">
                </div>

                <div class="form-field">
                    <label for="process-rto">RTO (heures)</label>
                    <input id="process-rto" type="number" min="0"
                           step="0.5" placeholder="Ex : 8">
                </div>

                <div class="form-field">
                    <label for="process-rpo">RPO (minutes)</label>
                    <input id="process-rpo" type="number" min="0"
                           step="1" placeholder="Ex : 60">
                </div>
            </div>

            <div class="process-form-actions">
                <button type="submit" class="primary-button" id="process-submit">
                    Enregistrer le processus
                </button>
                <button type="button" class="secondary-button hidden"
                        id="process-cancel">Annuler</button>
            </div>
        </form>
    </div>
    ` : ""}

    <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th>Processus</th>
                    <th>Criticité</th>
                    <th>MTPD (h)</th>
                    <th>RTO (h)</th>
                    <th>RPO (min)</th>
                    ${canWrite ? "<th>Actions</th>" : ""}
                </tr>
            </thead>
            <tbody>
                ${appData.processes.map(p => `
                    <tr>
                        <td>
                            <strong>${escapeHTML(p.name)}</strong>
                            <div class="process-description">
                                ${escapeHTML(p.description || "")}
                            </div>
                        </td>
                        <td>${p.criticality}/5</td>
                        <td>${p.mtpd_hours ?? "—"}</td>
                        <td>${p.rto_hours ?? "—"}</td>
                        <td>${p.rpo_minutes ?? "—"}</td>
                        ${canWrite ? `
                        <td class="process-actions">
                            <button type="button" class="action-button"
                                    data-action="edit" data-id="${p.id}">
                                Modifier
                            </button>
                            ${isAdmin ? `
                            <button type="button" class="action-button danger-button"
                                    data-action="delete" data-id="${p.id}">
                                Supprimer
                            </button>` : ""}
                        </td>` : ""}
                    </tr>
                `).join("") || `
                    <tr><td colspan="${canWrite ? 6 : 5}">
                        Aucun processus enregistré.
                    </td></tr>
                `}
            </tbody>
        </table>
    </div>`;

    if (!canWrite) return;

    const container = $("processes-content");
    const form = $("process-form");

    function resetProcessForm() {
        form.reset();
        $("process-id").value = "";
        $("process-form-title").textContent = "Ajouter un processus";
        $("process-submit").textContent = "Enregistrer le processus";
        $("process-cancel").classList.add("hidden");
    }

    $("process-cancel").addEventListener("click", resetProcessForm);

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const name = $("process-name").value.trim();
        const mtpdValue = $("process-mtpd").value;
        const rtoValue = $("process-rto").value;
        const rpoValue = $("process-rpo").value;

        const mtpd = mtpdValue === "" ? null : Number(mtpdValue);
        const rto = rtoValue === "" ? null : Number(rtoValue);

        if (rto !== null && mtpd !== null && rto > mtpd) {
            showMessage("Le RTO doit être inférieur ou égal au MTPD.", "error");
            return;
        }

        const data = {
            name,
            description: $("process-description").value.trim() || null,
            criticality: Number($("process-criticality").value),
            mtpd_hours: mtpd,
            rto_hours: rto,
            rpo_minutes: rpoValue === "" ? null : Number(rpoValue)
        };

        const id = $("process-id").value;

        try {
            $("process-submit").disabled = true;

            if (id) {
                await API.updateProcess(Number(id), data);
            } else {
                await API.createProcess(data);
            }

            resetProcessForm();
            await loadDashboard();
            showMessage(
                id ? "Processus modifié avec succès." : "Processus ajouté avec succès.",
                "success"
            );
        } catch (error) {
            showMessage(error.message, "error");
        } finally {
            const button = $("process-submit");
            if (button) button.disabled = false;
        }
    });

    container.onclick = async (event) => {
        const button = event.target.closest("button[data-action]");
        if (!button) return;

        const id = Number(button.dataset.id);
        const process = appData.processes.find(p => p.id === id);
        if (!process) return;

        if (button.dataset.action === "edit") {
            $("process-id").value = process.id;
            $("process-name").value = process.name;
            $("process-description").value = process.description || "";
            $("process-criticality").value = process.criticality;
            $("process-mtpd").value = process.mtpd_hours ?? "";
            $("process-rto").value = process.rto_hours ?? "";
            $("process-rpo").value = process.rpo_minutes ?? "";

            $("process-form-title").textContent = "Modifier le processus";
            $("process-submit").textContent = "Enregistrer les modifications";
            $("process-cancel").classList.remove("hidden");

            $("process-form").scrollIntoView({ behavior: "smooth" });
            return;
        }

        if (button.dataset.action === "delete" && isAdmin) {
            const confirmed = confirm(
                `Supprimer le processus "${process.name}" ?\n\n` +
                "Attention : les risques associés à ce processus seront également supprimés."
            );

            if (!confirmed) return;

            try {
                await API.deleteProcess(id);
                await loadDashboard();
                showMessage("Processus supprimé avec succès.", "success");
            } catch (error) {
                showMessage(error.message, "error");
            }
        }
    };
}

function renderAssets() {
    const canWrite = ["admin", "analyste"].includes(currentUser?.role);

    const assetTypes = [
        ["serveur", "Serveur"],
        ["application", "Application"],
        ["local", "Local"],
        ["personnel", "Personnel"],
        ["fournisseur", "Fournisseur"]
    ];

    $("assets-content").innerHTML = `
    ${canWrite ? `
    <div class="process-form-card">
        <h3 id="asset-form-title">Ajouter un actif</h3>

        <form id="asset-form">
            <input type="hidden" id="asset-id">

            <div class="process-form-grid">
                <div class="form-field">
                    <label for="asset-name">Nom de l'actif *</label>
                    <input id="asset-name" type="text"
                           minlength="2" maxlength="120" required
                           placeholder="Ex : Serveur Web principal">
                </div>

                <div class="form-field">
                    <label for="asset-type">Type d'actif *</label>
                    <select id="asset-type" required>
                        ${assetTypes.map(([value, label]) =>
                            `<option value="${value}">${label}</option>`
                        ).join("")}
                    </select>
                </div>

                <div class="form-field full-width">
                    <label for="asset-description">Description</label>
                    <textarea id="asset-description" rows="2"
                              placeholder="Description de l'actif"></textarea>
                </div>
            </div>

            <div class="process-form-actions">
                <button type="submit" class="primary-button" id="asset-submit">
                    Enregistrer l'actif
                </button>
                <button type="button" class="secondary-button hidden"
                        id="asset-cancel">Annuler</button>
            </div>
        </form>
    </div>
    ` : ""}

    <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th>Nom</th>
                    <th>Type</th>
                    <th>Description</th>
                    ${canWrite ? "<th>Actions</th>" : ""}
                </tr>
            </thead>
            <tbody>
                ${appData.assets.map(a => `
                    <tr>
                        <td><strong>${escapeHTML(a.name)}</strong></td>
                        <td>${escapeHTML(a.asset_type)}</td>
                        <td>${escapeHTML(a.description || "—")}</td>
                        ${canWrite ? `
                        <td class="process-actions">
                            <button type="button" class="action-button"
                                    data-action="edit-asset" data-id="${a.id}">
                                Modifier
                            </button>
                            <button type="button"
                                    class="action-button danger-button"
                                    data-action="delete-asset" data-id="${a.id}">
                                Supprimer
                            </button>
                        </td>` : ""}
                    </tr>
                `).join("") || `
                    <tr><td colspan="${canWrite ? 4 : 3}">
                        Aucun actif enregistré.
                    </td></tr>
                `}
            </tbody>
        </table>
    </div>`;

    if (!canWrite) return;

    const container = $("assets-content");
    const form = $("asset-form");

    function resetAssetForm() {
        form.reset();
        $("asset-id").value = "";
        $("asset-form-title").textContent = "Ajouter un actif";
        $("asset-submit").textContent = "Enregistrer l'actif";
        $("asset-cancel").classList.add("hidden");
    }

    $("asset-cancel").addEventListener("click", resetAssetForm);

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const data = {
            name: $("asset-name").value.trim(),
            asset_type: $("asset-type").value,
            description: $("asset-description").value.trim() || null
        };

        const id = $("asset-id").value;

        try {
            $("asset-submit").disabled = true;

            if (id) {
                await API.updateAsset(Number(id), data);
            } else {
                await API.createAsset(data);
            }

            await loadDashboard();
            showMessage(
                id ? "Actif modifié avec succès." : "Actif ajouté avec succès.",
                "success"
            );
        } catch (error) {
            showMessage(error.message, "error");
        } finally {
            const button = $("asset-submit");
            if (button) button.disabled = false;
        }
    });

    container.onclick = async (event) => {
        const button = event.target.closest("button[data-action]");
        if (!button) return;

        const id = Number(button.dataset.id);
        const asset = appData.assets.find(a => a.id === id);
        if (!asset) return;

        if (button.dataset.action === "edit-asset") {
            $("asset-id").value = asset.id;
            $("asset-name").value = asset.name;
            $("asset-type").value = asset.asset_type;
            $("asset-description").value = asset.description || "";

            $("asset-form-title").textContent = "Modifier l'actif";
            $("asset-submit").textContent = "Enregistrer les modifications";
            $("asset-cancel").classList.remove("hidden");

            $("asset-form").scrollIntoView({ behavior: "smooth" });
            return;
        }

        if (button.dataset.action === "delete-asset") {
            const confirmed = confirm(
                `Supprimer l'actif "${asset.name}" ?\n\n` +
                "Si cet actif est associé à un risque, la suppression peut être refusée."
            );

            if (!confirmed) return;

            try {
                await API.deleteAsset(id);
                await loadDashboard();
                showMessage("Actif supprimé avec succès.", "success");
            } catch (error) {
                showMessage(error.message, "error");
            }
        }
    };
}

function renderRisks() {
    const canWrite = ["admin", "analyste"].includes(currentUser?.role);
    const processes = appData.processes || [];
    const assets = appData.assets || [];

    const riskLevel = score => {
        if (score <= 4) return "Faible";
        if (score <= 9) return "Moyen";
        if (score <= 15) return "Élevé";
        return "Critique";
    };

    $("risks-content").innerHTML = `
    ${canWrite ? `
    <div class="process-form-card">
        <h3 id="risk-form-title">Ajouter un risque</h3>

        <form id="risk-form">
            <input type="hidden" id="risk-id">

            <div class="process-form-grid">
                <div class="form-field">
                    <label for="risk-process">Processus métier *</label>
                    <select id="risk-process" required>
                        <option value="">Sélectionner un processus</option>
                        ${processes.map(p => `
                            <option value="${p.id}">${escapeHTML(p.name)}</option>
                        `).join("")}
                    </select>
                </div>

                <div class="form-field">
                    <label for="risk-asset">Actif concerné</label>
                    <select id="risk-asset">
                        <option value="">Aucun actif associé</option>
                        ${assets.map(a => `
                            <option value="${a.id}">${escapeHTML(a.name)}</option>
                        `).join("")}
                    </select>
                </div>

                <div class="form-field full-width">
                    <label for="risk-threat">Menace *</label>
                    <input id="risk-threat" type="text" minlength="3"
                           maxlength="200" required
                           placeholder="Ex : Ransomware">
                </div>

                <div class="form-field full-width">
                    <label for="risk-vulnerability">Vulnérabilité *</label>
                    <textarea id="risk-vulnerability" minlength="3"
                              maxlength="200" required rows="2"
                              placeholder="Ex : Sauvegardes non isolées"></textarea>
                </div>

                <div class="form-field">
                    <label for="risk-probability">Probabilité (1 à 5) *</label>
                    <select id="risk-probability" required>
                        <option value="1">1 - Très faible</option>
                        <option value="2">2 - Faible</option>
                        <option value="3" selected>3 - Moyenne</option>
                        <option value="4">4 - Élevée</option>
                        <option value="5">5 - Très élevée</option>
                    </select>
                </div>

                <div class="form-field">
                    <label for="risk-impact">Impact (1 à 5) *</label>
                    <select id="risk-impact" required>
                        <option value="1">1 - Très faible</option>
                        <option value="2">2 - Faible</option>
                        <option value="3" selected>3 - Moyen</option>
                        <option value="4">4 - Élevé</option>
                        <option value="5">5 - Très élevé</option>
                    </select>
                </div>
            </div>

            <div class="process-form-actions">
                <strong>Score estimé : <span id="risk-score-preview">9/25 — Moyen</span></strong>
            </div>

            <div class="process-form-actions">
                <button type="submit" class="primary-button" id="risk-submit">
                    Enregistrer le risque
                </button>
                <button type="button" class="secondary-button"
                        id="risk-cancel">Annuler</button>
            </div>
        </form>
    </div>
    ` : ""}

    <div class="process-form-card">
        <h3>Registre des risques</h3>
        <table>
          <thead><tr>
            <th>Menace</th>
            <th>Vulnérabilité</th>
            <th>Processus</th>
            <th>Actif</th>
            <th>Probabilité</th>
            <th>Impact</th>
            <th>Score</th>
            <th>Niveau</th>
            ${canWrite ? "<th>Actions</th>" : ""}
          </tr></thead>
          <tbody>
          ${appData.risks.map(r => `
            <tr>
              <td>${escapeHTML(r.threat)}</td>
              <td>${escapeHTML(r.vulnerability)}</td>
              <td>${escapeHTML(processName(r.process_id))}</td>
              <td>${escapeHTML(assetName(r.asset_id))}</td>
              <td>${r.probability}/5</td>
              <td>${r.impact}/5</td>
              <td><strong>${r.score}/25</strong></td>
              <td>${levelBadge(r.level)}</td>
              ${canWrite ? `
              <td class="process-actions">
                <button class="action-button" data-edit-risk="${r.id}">Modifier</button>
                <button class="action-button danger-button" data-delete-risk="${r.id}">Supprimer</button>
              </td>` : ""}
            </tr>
          `).join("") || `
            <tr><td colspan="${canWrite ? 9 : 8}">Aucun risque enregistré</td></tr>
          `}
          </tbody>
        </table>
    </div>`;

    if (!canWrite) return;

    const form = $("risk-form");
    const probability = $("risk-probability");
    const impact = $("risk-impact");

    function updateRiskPreview() {
        const score = Number(probability.value) * Number(impact.value);
        $("risk-score-preview").textContent =
            `${score}/25 — ${riskLevel(score)}`;
    }

    function resetRiskForm() {
        form.reset();
        $("risk-id").value = "";
        $("risk-form-title").textContent = "Ajouter un risque";
        $("risk-submit").textContent = "Enregistrer le risque";
        probability.value = "3";
        impact.value = "3";
        updateRiskPreview();
    }

    probability.addEventListener("change", updateRiskPreview);
    impact.addEventListener("change", updateRiskPreview);

    $("risk-cancel").addEventListener("click", resetRiskForm);

    form.addEventListener("submit", async event => {
        event.preventDefault();

        const id = $("risk-id").value;
        const processId = $("risk-process").value;

        if (!processId) {
            showMessage("Veuillez sélectionner un processus.");
            return;
        }

        const data = {
            process_id: Number(processId),
            asset_id: $("risk-asset").value
                ? Number($("risk-asset").value) : null,
            threat: $("risk-threat").value.trim(),
            vulnerability: $("risk-vulnerability").value.trim(),
            probability: Number(probability.value),
            impact: Number(impact.value)
        };

        try {
            if (id) {
                await API.updateRisk(Number(id), {
                    asset_id: data.asset_id,
                    threat: data.threat,
                    vulnerability: data.vulnerability,
                    probability: data.probability,
                    impact: data.impact
                });
            } else {
                await API.createRisk(data);
            }

            await loadDashboard();
            showMessage(
                id ? "Risque modifié avec succès." : "Risque ajouté avec succès.",
                "success"
            );
        } catch (error) {
            showMessage("Erreur : " + error.message);
        }
    });

    $("risks-content").onclick = async event => {
        const editButton = event.target.closest("[data-edit-risk]");
        const deleteButton = event.target.closest("[data-delete-risk]");

        if (editButton) {
            const risk = appData.risks.find(
                r => r.id === Number(editButton.dataset.editRisk)
            );
            if (!risk) return;

            $("risk-id").value = risk.id;
            $("risk-process").value = String(risk.process_id);
            $("risk-asset").value = risk.asset_id
                ? String(risk.asset_id) : "";
            $("risk-threat").value = risk.threat;
            $("risk-vulnerability").value = risk.vulnerability;
            probability.value = String(risk.probability);
            impact.value = String(risk.impact);

            $("risk-form-title").textContent = "Modifier le risque";
            $("risk-submit").textContent = "Enregistrer les modifications";
            updateRiskPreview();
            form.scrollIntoView({ behavior: "smooth" });
            return;
        }

        if (deleteButton) {
            const id = Number(deleteButton.dataset.deleteRisk);
            const risk = appData.risks.find(r => r.id === id);
            if (!risk) return;

            if (!confirm(`Supprimer le risque "${risk.threat}" ?`)) return;

            try {
                await API.deleteRisk(id);
                await loadDashboard();
                showMessage("Risque supprimé avec succès.", "success");
            } catch (error) {
                showMessage("Erreur : " + error.message);
            }
        }
    };

    updateRiskPreview();
}
async function renderMatrix() {
    const data = await API.matrix();
    const cells = data.cells || [];

    $("matrix-content").innerHTML = `
    <div class="matrix-grid">
      <div class="matrix-label">P / I</div>
      ${[1,2,3,4,5].map(i => `<div class="matrix-label">${i}</div>`).join("")}
      ${[5,4,3,2,1].map(p => `
        <div class="matrix-label">${p}</div>
        ${[1,2,3,4,5].map(i => {
            const cell = cells.find(c =>
                c.probability === p && c.impact === i
            );
            return `<div class="matrix-cell matrix-${levelClass(cell?.level)}">
                <strong>${cell?.score ?? p*i}</strong>
                <span>${cell?.count ?? 0} risque(s)</span>
            </div>`;
        }).join("")}
      `).join("")}
    </div>
    <p class="matrix-caption">Probabilité (verticale) × Impact (horizontal)</p>`;
}


function riskLevelLabel(score) {
    if (score <= 4) return "Faible";
    if (score <= 9) return "Moyen";
    if (score <= 15) return "Élevé";
    return "Critique";
}

async function renderTreatments() {
    const canWrite = ["admin", "analyste"].includes(currentUser?.role);
    const canDelete = currentUser?.role === "admin";

    const results = await Promise.all(
        appData.risks.map(async risk => {
            try {
                const treatments = await API.treatments(risk.id);
                return treatments.map(t => ({
                    ...t,
                    threat: risk.threat
                }));
            } catch (error) {
                console.error("Traitement du risque", risk.id, error);
                return [];
            }
        })
    );

    appData.treatments = results.flat();

    const strategies = [
        ["réduire", "Réduire"],
        ["accepter", "Accepter"],
        ["transférer", "Transférer"],
        ["éviter", "Éviter"]
    ];

    const statuses = [
        ["à faire", "À faire"],
        ["en cours", "En cours"],
        ["terminé", "Terminé"]
    ];

    $("treatments-content").innerHTML = `
    ${canWrite ? `
    <div class="process-form-card">
        <h3 id="treatment-form-title">Ajouter un traitement</h3>

        <form id="treatment-form">
            <input type="hidden" id="treatment-id">

            <div class="process-form-grid">

                <div class="form-field full-width">
                    <label for="treatment-risk">Risque concerné *</label>
                    <select id="treatment-risk" required>
                        <option value="">Sélectionner un risque</option>
                        ${appData.risks.map(r => `
                            <option value="${r.id}">
                                ${escapeHTML(r.threat)} (${r.score}/25 - ${escapeHTML(r.level)})
                            </option>
                        `).join("")}
                    </select>
                </div>

                <div class="form-field">
                    <label for="treatment-strategy">Stratégie *</label>
                    <select id="treatment-strategy" required>
                        ${strategies.map(([value, label]) => `
                            <option value="${value}">${label}</option>
                        `).join("")}
                    </select>
                </div>

                <div class="form-field">
                    <label for="treatment-status">Statut *</label>
                    <select id="treatment-status" required>
                        ${statuses.map(([value, label]) => `
                            <option value="${value}">${label}</option>
                        `).join("")}
                    </select>
                </div>

                <div class="form-field full-width">
                    <label for="treatment-action">Action corrective *</label>
                    <textarea id="treatment-action" minlength="5"
                              maxlength="5000" required rows="3"
                              placeholder="Décrire les actions à mettre en place..."></textarea>
                </div>

                <div class="form-field">
                    <label for="treatment-owner">Responsable</label>
                    <input id="treatment-owner" type="text"
                           maxlength="80"
                           placeholder="Ex : Responsable informatique">
                </div>

                <div class="form-field">
                    <label for="treatment-date">Date limite</label>
                    <input id="treatment-date" type="date">
                </div>

                <div class="form-field">
                    <label for="residual-probability">Probabilité résiduelle</label>
                    <select id="residual-probability">
                        <option value="">Non évaluée</option>
                        <option value="1">1 - Très faible</option>
                        <option value="2">2 - Faible</option>
                        <option value="3">3 - Moyenne</option>
                        <option value="4">4 - Élevée</option>
                        <option value="5">5 - Très élevée</option>
                    </select>
                </div>

                <div class="form-field">
                    <label for="residual-impact">Impact résiduel</label>
                    <select id="residual-impact">
                        <option value="">Non évalué</option>
                        <option value="1">1 - Très faible</option>
                        <option value="2">2 - Faible</option>
                        <option value="3">3 - Moyen</option>
                        <option value="4">4 - Élevé</option>
                        <option value="5">5 - Très élevé</option>
                    </select>
                </div>

                <div class="full-width" id="residual-preview">
                    Score résiduel : non évalué
                </div>
            </div>

            <div class="process-form-actions">
                <button type="submit" class="primary-button"
                        id="treatment-submit">
                    Enregistrer le traitement
                </button>
                <button type="button" class="secondary-button"
                        id="treatment-cancel">
                    Annuler
                </button>
            </div>
        </form>
    </div>
    ` : ""}

    <div class="process-form-card">
        <h3>Registre des traitements</h3>

        <table>
          <thead>
            <tr>
                <th>Risque</th>
                <th>Stratégie</th>
                <th>Action corrective</th>
                <th>Responsable</th>
                <th>Échéance</th>
                <th>Statut</th>
                <th>Risque résiduel</th>
                ${canWrite ? "<th>Actions</th>" : ""}
            </tr>
          </thead>

          <tbody>
          ${appData.treatments.map(t => {
              const residualScore =
                  t.residual_probability != null &&
                  t.residual_impact != null
                  ? t.residual_probability * t.residual_impact
                  : null;

              return `
              <tr>
                  <td>${escapeHTML(t.threat)}</td>
                  <td>${escapeHTML(t.strategy)}</td>
                  <td>${escapeHTML(t.action)}</td>
                  <td>${escapeHTML(t.owner || "—")}</td>
                  <td>${escapeHTML(t.due_date || "—")}</td>
                  <td>${escapeHTML(t.status)}</td>
                  <td>${residualScore !== null
                      ? `${residualScore}/25 — ${riskLevelLabel(residualScore)}`
                      : "Non évalué"}</td>
                  ${canWrite ? `
                  <td class="process-actions">
                      <button class="action-button"
                              data-edit-treatment="${t.id}">
                          Modifier
                      </button>
                      ${canDelete ? `
                      <button class="action-button danger-button"
                              data-delete-treatment="${t.id}">
                          Supprimer
                      </button>` : ""}
                  </td>` : ""}
              </tr>`;
          }).join("") || `
              <tr>
                  <td colspan="${canWrite ? 8 : 7}">
                      Aucun traitement enregistré
                  </td>
              </tr>
          `}
          </tbody>
        </table>
    </div>`;

    if (!canWrite) return;

    const form = $("treatment-form");

    const residualProbability = $("residual-probability");
    const residualImpact = $("residual-impact");

    function riskLevelLabel(score) {
        if (score <= 4) return "Faible";
        if (score <= 9) return "Moyen";
        if (score <= 15) return "Élevé";
        return "Critique";
    }

    function updateResidualPreview() {
        const p = residualProbability.value;
        const i = residualImpact.value;

        if (!p && !i) {
            $("residual-preview").textContent =
                "Score résiduel : non évalué";
        } else if (!p || !i) {
            $("residual-preview").textContent =
                "Veuillez renseigner les deux valeurs.";
        } else {
            const score = Number(p) * Number(i);
            $("residual-preview").textContent =
                `Score résiduel : ${score}/25 — ${riskLevelLabel(score)}`;
        }
    }

    function resetTreatmentForm() {
        form.reset();
        $("treatment-id").value = "";
        $("treatment-risk").disabled = false;
        $("treatment-form-title").textContent =
            "Ajouter un traitement";
        $("treatment-submit").textContent =
            "Enregistrer le traitement";
        updateResidualPreview();
    }

    residualProbability.addEventListener(
        "change", updateResidualPreview
    );
    residualImpact.addEventListener(
        "change", updateResidualPreview
    );

    $("treatment-cancel").addEventListener(
        "click", resetTreatmentForm
    );

    form.addEventListener("submit", async event => {
        event.preventDefault();

        const id = $("treatment-id").value;
        const riskId = $("treatment-risk").value;

        if (!riskId) {
            showMessage("Veuillez sélectionner un risque.");
            return;
        }

        const p = residualProbability.value;
        const i = residualImpact.value;

        if ((p && !i) || (!p && i)) {
            showMessage(
                "La probabilité et l'impact résiduels doivent être renseignés ensemble."
            );
            return;
        }

        const data = {
            strategy: $("treatment-strategy").value,
            action: $("treatment-action").value.trim(),
            owner: $("treatment-owner").value.trim() || null,
            due_date: $("treatment-date").value || null,
            status: $("treatment-status").value,
            residual_probability: p ? Number(p) : null,
            residual_impact: i ? Number(i) : null
        };

        try {
            if (id) {
                await API.updateTreatment(Number(id), data);
            } else {
                await API.createTreatment(Number(riskId), data);
            }

            await renderTreatments();

            showMessage(
                id
                    ? "Traitement modifié avec succès."
                    : "Traitement ajouté avec succès.",
                "success"
            );
        } catch (error) {
            showMessage("Erreur : " + error.message);
        }
    });

    $("treatments-content").onclick = async event => {
        const editButton =
            event.target.closest("[data-edit-treatment]");
        const deleteButton =
            event.target.closest("[data-delete-treatment]");

        if (editButton) {
            const treatment = appData.treatments.find(
                t => t.id === Number(editButton.dataset.editTreatment)
            );

            if (!treatment) return;

            $("treatment-id").value = treatment.id;
            $("treatment-risk").value = String(treatment.risk_id);
            $("treatment-risk").disabled = true;
            $("treatment-strategy").value = treatment.strategy;
            $("treatment-action").value = treatment.action;
            $("treatment-owner").value = treatment.owner || "";
            $("treatment-date").value = treatment.due_date || "";
            $("treatment-status").value = treatment.status;

            residualProbability.value =
                treatment.residual_probability ?? "";
            residualImpact.value =
                treatment.residual_impact ?? "";

            $("treatment-form-title").textContent =
                "Modifier le traitement";
            $("treatment-submit").textContent =
                "Enregistrer les modifications";

            updateResidualPreview();
            form.scrollIntoView({ behavior: "smooth" });
            return;
        }

        if (deleteButton && canDelete) {
            const id = Number(deleteButton.dataset.deleteTreatment);

            const treatment = appData.treatments.find(
                t => t.id === id
            );

            if (!treatment) return;

            if (!confirm("Voulez-vous supprimer ce traitement ?")) {
                return;
            }

            try {
                await API.deleteTreatment(id);
                await renderTreatments();
                showMessage(
                    "Traitement supprimé avec succès.",
                    "success"
                );
            } catch (error) {
                showMessage("Erreur : " + error.message);
            }
        }
    };

    updateResidualPreview();
}

async function loadDashboard() {
    hideMessage();

    try {
        const [processes, assets, risks, bia] = await Promise.all([
            API.processes(),
            API.assets(),
            API.risks(),
            API.bia()
        ]);

        appData.processes = processes;
        appData.assets = assets;
        appData.risks = risks;
        appData.bia = bia;

        renderDashboard();
        renderProcesses();
        renderAssets();
        renderRisks();
    } catch (error) {
        showMessage("Erreur de chargement : " + error.message);
    }
}

async function navigate(section) {
    if (!titles[section]) return;

    document.querySelectorAll(".content-section").forEach(el => {
        el.classList.add("hidden");
    });

    const target = $("section-" + section);
    if (target) target.classList.remove("hidden");

    document.querySelectorAll(".nav-link").forEach(link => {
        link.classList.toggle(
            "active",
            link.dataset.section === section
        );
    });

    $("page-title").textContent = titles[section];
    $("breadcrumb-section").textContent = titles[section];
    hideMessage();

    try {
        if (section === "matrix") await renderMatrix();
        if (section === "treatments") await renderTreatments();
        if (section === "bia") await renderBIA();
        if (section === "audit") await renderAudit();
    } catch (error) {
        showMessage("Erreur : " + error.message);
    }
}

$("login-form").addEventListener("submit", async event => {
    event.preventDefault();

    const button = $("login-button");
    const errorBox = $("login-error");

    button.disabled = true;
    errorBox.classList.add("hidden");

    try {
        const username = $("username").value.trim();
        const password = $("password").value;

        await API.login(username, password);
        const user = await API.me();

        showApp(user);
        navigate("dashboard");
    } catch (error) {
        API.clearToken();
        errorBox.textContent = error.message;
        errorBox.classList.remove("hidden");
    } finally {
        button.disabled = false;
    }
});

document.querySelectorAll(".nav-link").forEach(link => {
    link.addEventListener("click", () => {
        navigate(link.dataset.section);
    });
});

$("logout-button").addEventListener("click", showLogin);


$("download-report-button").addEventListener("click", async () => {
    const button = $("download-report-button");
    const originalText = button.textContent;

    button.disabled = true;
    button.textContent = "Génération du rapport...";

    hideMessage();

    try {
        const filename = await API.downloadReport();
        showMessage(
            `Rapport téléchargé avec succès : ${filename}`,
            "success"
        );
    } catch (error) {
        showMessage(
            "Impossible de télécharger le rapport : " + error.message
        );
    } finally {
        button.disabled = false;
        button.textContent = originalText;
    }
});


async function initializeApp() {
    if (!API.getToken()) {
        showLogin();
        return;
    }

    try {
        const user = await API.me();
        showApp(user);
    } catch (error) {
        showLogin();
    }
}

document.addEventListener("DOMContentLoaded", initializeApp);


// ---------- Analyse d'impact sur l'activité (BIA) ----------
async function renderBIA() {
    const canWrite = ["admin", "analyste"].includes(currentUser?.role);
    const canDelete = currentUser?.role === "admin";

    appData.bia = await API.bia();

    const impactOptions = `
        <option value="1">1 - Très faible</option>
        <option value="2">2 - Faible</option>
        <option value="3">3 - Moyen</option>
        <option value="4">4 - Élevé</option>
        <option value="5">5 - Très élevé</option>
    `;

    const impactLabel = value => ({
        1: "Très faible",
        2: "Faible",
        3: "Moyen",
        4: "Élevé",
        5: "Critique"
    }[value] || "—");

    $("bia-content").innerHTML = `
        ${canWrite ? `
        <div class="process-form-card">
            <h3 id="bia-form-title">Nouvelle analyse BIA</h3>

            <form id="bia-form">
                <input type="hidden" id="bia-id">

                <div class="process-form-grid">
                    <div class="form-field full-width">
                        <label for="bia-process">Processus métier *</label>
                        <select id="bia-process" required>
                            <option value="">Sélectionner un processus</option>
                            ${appData.processes.map(p => `
                                <option value="${p.id}">
                                    ${escapeHTML(p.name)}
                                </option>
                            `).join("")}
                        </select>
                    </div>

                    <div class="form-field">
                        <label for="bia-financial">Impact financier *</label>
                        <select id="bia-financial" required>${impactOptions}</select>
                    </div>

                    <div class="form-field">
                        <label for="bia-operational">Impact opérationnel *</label>
                        <select id="bia-operational" required>${impactOptions}</select>
                    </div>

                    <div class="form-field">
                        <label for="bia-legal">Impact juridique *</label>
                        <select id="bia-legal" required>${impactOptions}</select>
                    </div>

                    <div class="form-field">
                        <label for="bia-reputational">Impact réputationnel *</label>
                        <select id="bia-reputational" required>${impactOptions}</select>
                    </div>

                    <div class="form-field full-width">
                        <label for="bia-consequences">Conséquences métier *</label>
                        <textarea id="bia-consequences" minlength="10"
                            maxlength="5000" rows="4" required
                            placeholder="Décrire les conséquences d'une interruption de ce processus..."></textarea>
                    </div>

                    <div class="form-field full-width">
                        <label for="bia-resources">Ressources essentielles</label>
                        <textarea id="bia-resources" maxlength="5000" rows="3"
                            placeholder="Personnel, systèmes informatiques, fournisseurs, locaux..."></textarea>
                    </div>
                </div>

                <div class="process-form-actions">
                    <button type="submit" class="primary-button" id="bia-submit">
                        Enregistrer l'analyse
                    </button>
                    <button type="button" class="secondary-button" id="bia-cancel">
                        Annuler
                    </button>
                </div>
            </form>
        </div>
        ` : ""}

        <div class="process-form-card">
            <h3>Registre des analyses BIA</h3>
            <table>
                <thead>
                    <tr>
                        <th>Processus</th>
                        <th>Financier</th>
                        <th>Opérationnel</th>
                        <th>Juridique</th>
                        <th>Réputationnel</th>
                        <th>Criticité globale</th>
                        <th>Conséquences métier</th>
                        <th>Ressources essentielles</th>
                        ${canWrite ? "<th>Actions</th>" : ""}
                    </tr>
                </thead>
                <tbody>
                    ${appData.bia.map(item => {
                        const process = appData.processes.find(
                            p => p.id === item.process_id
                        );
                        const globalImpact = Math.max(
                            item.financial_impact,
                            item.operational_impact,
                            item.legal_impact,
                            item.reputational_impact
                        );
                        return `
                        <tr>
                            <td>${escapeHTML(process?.name || `Processus #${item.process_id}`)}</td>
                            <td>${item.financial_impact}/5 — ${impactLabel(item.financial_impact)}</td>
                            <td>${item.operational_impact}/5 — ${impactLabel(item.operational_impact)}</td>
                            <td>${item.legal_impact}/5 — ${impactLabel(item.legal_impact)}</td>
                            <td>${item.reputational_impact}/5 — ${impactLabel(item.reputational_impact)}</td>
                            <td><strong>${globalImpact}/5 — ${impactLabel(globalImpact)}</strong></td>
                            <td>${escapeHTML(item.business_consequences)}</td>
                            <td>${escapeHTML(item.essential_resources || "—")}</td>
                            ${canWrite ? `
                            <td class="process-actions">
                                <button class="action-button" data-edit-bia="${item.id}">
                                    Modifier
                                </button>
                                ${canDelete ? `
                                <button class="action-button danger-button" data-delete-bia="${item.id}">
                                    Supprimer
                                </button>` : ""}
                            </td>` : ""}
                        </tr>`;
                    }).join("") || `
                        <tr>
                            <td colspan="${canWrite ? 8 : 7}">
                                Aucune analyse BIA enregistrée.
                            </td>
                        </tr>
                    `}
                </tbody>
            </table>
        </div>
    `;

    if (!canWrite) return;

    const form = $("bia-form");

    function resetBIAForm() {
        form.reset();
        $("bia-id").value = "";
        $("bia-process").disabled = false;
        $("bia-form-title").textContent = "Nouvelle analyse BIA";
        $("bia-submit").textContent = "Enregistrer l'analyse";
    }

    $("bia-cancel").addEventListener("click", resetBIAForm);

    form.addEventListener("submit", async event => {
        event.preventDefault();

        const id = $("bia-id").value;
        const processId = $("bia-process").value;

        if (!id && !processId) {
            showMessage("Veuillez sélectionner un processus.");
            return;
        }

        const data = {
            financial_impact: Number($("bia-financial").value),
            operational_impact: Number($("bia-operational").value),
            legal_impact: Number($("bia-legal").value),
            reputational_impact: Number($("bia-reputational").value),
            business_consequences: $("bia-consequences").value.trim(),
            essential_resources: $("bia-resources").value.trim() || null
        };

        if (!id) data.process_id = Number(processId);

        try {
            if (id) {
                await API.updateBIA(Number(id), data);
            } else {
                await API.createBIA(data);
            }

            await renderBIA();
            showMessage(
                id ? "Analyse BIA modifiée avec succès."
                   : "Analyse BIA créée avec succès.",
                "success"
            );
        } catch (error) {
            showMessage("Erreur : " + error.message);
        }
    });

    $("bia-content").addEventListener("click", async event => {
        const editButton = event.target.closest("[data-edit-bia]");
        const deleteButton = event.target.closest("[data-delete-bia]");

        if (editButton) {
            const item = appData.bia.find(
                entry => entry.id === Number(editButton.dataset.editBia)
            );
            if (!item) return;

            $("bia-id").value = item.id;
            $("bia-process").value = String(item.process_id);
            $("bia-process").disabled = true;
            $("bia-financial").value = item.financial_impact;
            $("bia-operational").value = item.operational_impact;
            $("bia-legal").value = item.legal_impact;
            $("bia-reputational").value = item.reputational_impact;
            $("bia-consequences").value = item.business_consequences;
            $("bia-resources").value = item.essential_resources || "";

            $("bia-form-title").textContent = "Modifier l'analyse BIA";
            $("bia-submit").textContent = "Enregistrer les modifications";
            form.scrollIntoView({ behavior: "smooth" });
            return;
        }

        if (deleteButton && canDelete) {
            const id = Number(deleteButton.dataset.deleteBia);
            if (!confirm("Voulez-vous supprimer cette analyse BIA ?")) return;

            try {
                await API.deleteBIA(id);
                await renderBIA();
                showMessage("Analyse BIA supprimée avec succès.", "success");
            } catch (error) {
                showMessage("Erreur : " + error.message);
            }
        }
    });
}

async function renderAudit() {
    const logs = await API.auditLogs();

    $("audit-content").innerHTML = logs.length === 0
        ? "<p>Aucune action enregistrée.</p>"
        : `<table>
            <thead><tr>
                <th>Date</th><th>Utilisateur</th><th>Action</th><th>Objet</th><th>Détails</th>
            </tr></thead>
            <tbody>
            ${logs.map(l => `<tr>
                <td>${escapeHTML(new Date(l.created_at).toLocaleString("fr-FR"))}</td>
                <td>${escapeHTML(l.username)}</td>
                <td>${escapeHTML(l.action)}</td>
                <td>${escapeHTML(l.entity_type)}${l.entity_id ? " #" + l.entity_id : ""}</td>
                <td>${escapeHTML(l.details)}</td>
            </tr>`).join("")}
            </tbody>
        </table>`;
}
