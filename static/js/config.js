/**
 * AxiomOS Configuration
 * Central configuration for API endpoints and settings
 */

const AxiomOSConfig = {
    // API Configuration
    api: {
        baseURL: (() => {
            // For Render deployment, API and static files are served from the same origin
            // For local development, API is on port 8000, static on 8080
            const hostname = window.location.hostname;
            const port = window.location.port;
            
            if (hostname === 'localhost' || hostname === '127.0.0.1') {
                // Local development - API on port 8000
                return 'http://localhost:8000';
            } else {
                // Production (Render) - same origin
                return '';
            }
        })(),
        endpoints: {
            health: '/api/health',
            sessions: '/api/sessions',
            chat: '/api/chat',
            memories: '/api/memories',
            memoryCategories: '/api/memories/categories',
            memoryExport: '/api/memories/export'
        }
    },

    // Application Settings
    app: {
        name: 'AxiomOS',
        version: '0.1.0',
        debug: false
    },

    // Get full API URL
    getAPIUrl(endpoint) {
        return this.api.baseURL + this.api.endpoints[endpoint] || endpoint;
    },

    // Make API request with error handling
    async apiRequest(endpoint, options = {}) {
        const url = this.getAPIUrl(endpoint);
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
        };

        try {
            const response = await fetch(url, { ...defaultOptions, ...options });
            
            if (!response.ok) {
                throw new Error(`API Error: ${response.status} ${response.statusText}`);
            }
            
            return response;
        } catch (error) {
            console.error(`API Request failed for ${endpoint}:`, error);
            throw error;
        }
    }
};

// Global configuration
window.AxiomOSConfig = AxiomOSConfig;

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AxiomOSConfig;
}
