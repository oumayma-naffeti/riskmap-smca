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
                message = data.detail || message;
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

    treatments(riskId) {
        return this.request(`/api/risks/${riskId}/treatments`);
    }
};
