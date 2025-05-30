const isProduction = import.meta.env.VITE_NODE_ENV;

export class ApiService {
    static BASE_URL = isProduction === "production" 
        ? "https://deploy-ml-model-on-render.onrender.com" 
        : "http://127.0.0.1:8000";

    static async get(endpoint) {
        const response = await fetch(`${this.BASE_URL}${endpoint}`);
        return response.json();
    }
}