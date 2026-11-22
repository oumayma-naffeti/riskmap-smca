const API_URL = "";

const API = {
    tokenKey: "riskmap_access_token",

    getToken() {
        return sessionStorage.getItem(this.tokenKey);
    },

    saveToken(token) {
        sessionStorage.setItem(this.tokenKey, token);
    },

    clearToken() {
        sessionStorage.removeItem(this.tokenKey);
    },

    async request(path, options = {}) {
        const headers = {
            ...(options.headers || {})
        };

        if (this.getToken()) {
            headers.Authorization = `Bearer ${this.getToken()}`;
        }

        const response = await fetch(`${API_URL}${path}`, {
            ...options,
            headers
        });

        if (!response.ok) {
            let message = `Erreur HTTP ${response.status}`;
            try {
                const data = await response.json();
                if (Array.isArray(data.detail)) {
                    message = data.detail.map(e => `${(e.loc || []).slice(1).join(".")} : ${e.msg}`).join(" ; ");
                } else {
                    message = data.detail || message;
                }
            } catch (_) {}
            throw new Error(message);
        }

        if (response.status === 204) return null;
        return response.json();
    },

    async login(username, password) {
        const body = new URLSearchParams();
        body.append("username", username);
        body.append("password", password);

        const data = await this.request("/api/auth/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded"
            },
            body
        });

        this.saveToken(data.access_token);
        return data;
    },

    me() {
        return this.request("/api/auth/me");
    },

    processes() {
        return this.request("/api/processes");
    },

    createProcess(data) {
        return this.request("/api/processes", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
    },

    updateProcess(id, data) {
        return this.request(`/api/processes/${id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
    },

    deleteProcess(id) {
        return this.request(`/api/processes/${id}`, {
            method: "DELETE"
        });
    },

    assets() {
        return this.request("/api/assets");
    },

    createAsset(data) {
        return this.request("/api/assets", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
    },

    updateAsset(id, data) {
        return this.request(`/api/assets/${id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
    },

    deleteAsset(id) {
        return this.request(`/api/assets/${id}`, {
            method: "DELETE"
        });
    },

    risks() {
        return this.request("/api/risks");
    },

    createRisk(data) {
        return this.request("/api/risks", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
    },

    updateRisk(id, data) {
        return this.request(`/api/risks/${id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
    },

    deleteRisk(id) {
        return this.request(`/api/risks/${id}`, {
            method: "DELETE"
        });
    },

    matrix() {
        return this.request("/api/risks/matrix");
    },

    bia() {
        return this.request("/api/bia");
    },

    createBIA(data) {
        return this.request("/api/bia", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
    },

    updateBIA(id, data) {
        return this.request(`/api/bia/${id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
    },

    deleteBIA(id) {
        return this.request(`/api/bia/${id}`, {
            method: "DELETE"
        });
    },

    treatments(riskId) {
        return this.request(`/api/risks/${riskId}/treatments`);
    },

    createTreatment(riskId, data) {
        return this.request(`/api/risks/${riskId}/treatments`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
    },

    updateTreatment(id, data) {
        return this.request(`/api/treatments/${id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
    },

    deleteTreatment(id) {
        return this.request(`/api/treatments/${id}`, {
            method: "DELETE"
        });
    },

    auditLogs(limit = 100) {
        return this.request(`/api/audit-logs?limit=${limit}`);
    },

    governance() {
        return this.request("/api/governance/program");
    },

    saveGovernance(data) {
        return this.request("/api/governance/program", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
    },

    submitGovernance() {
        return this.request("/api/governance/program/submit", { method: "POST" });
    },

    approveGovernance() {
        return this.request("/api/governance/program/approve", { method: "POST" });
    },

    rejectGovernance() {
        return this.request("/api/governance/program/reject", { method: "POST" });
    },

    async downloadReport() {
        const token = this.getToken();

        const response = await fetch("/api/reports/smca/pdf", {
            method: "GET",
            headers: token
                ? { Authorization: `Bearer ${token}` }
                : {}
        });

        if (!response.ok) {
            let message = `Erreur HTTP ${response.status}`;
            try {
                const data = await response.json();
                message = data.detail || message;
            } catch (_) {}
            throw new Error(message);
        }

        const blob = await response.blob();

        const disposition = response.headers.get("Content-Disposition") || "";
        const match = disposition.match(/filename="?([^";]+)"?/i);
        const filename = match
            ? match[1]
            : "rapport_smca.pdf";

        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");

        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();

        setTimeout(() => URL.revokeObjectURL(url), 1000);

        return filename;
    },

};