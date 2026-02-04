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
        if (!endpoint) return this.api.baseURL;

        const endpointStr = String(endpoint);

        // Support `key/suffix/...` by mapping the first segment.
        let mapped = this.api.endpoints[endpointStr];
        if (!mapped && endpointStr.includes('/')) {
            const [first, ...rest] = endpointStr.split('/');
            const firstMapped = this.api.endpoints[first];
            if (firstMapped) {
                const suffix = rest.join('/');
                mapped = suffix ? `${firstMapped.replace(/\/$/, '')}/${suffix}` : firstMapped;
            }
        }

        const path = mapped ? mapped : endpointStr;
        if (!path) return this.api.baseURL;

        // If caller passed an absolute URL, keep it.
        if (typeof path === 'string' && (path.startsWith('http://') || path.startsWith('https://'))) {
            return path;
        }

        // Ensure we end up with a leading slash for relative paths.
        const normalizedPath = typeof path === 'string' && path.startsWith('/') ? path : `/${path}`;
        return `${this.api.baseURL}${normalizedPath}`;
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
