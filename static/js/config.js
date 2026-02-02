/**
 * AxiomOS Configuration
 * Central configuration for API endpoints and settings
 */

const AxiomOSConfig = {
    // API Configuration
    api: {
        baseURL: window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
            ? 'http://localhost:8000' 
            : '', // Production: same origin
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
