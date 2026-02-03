/**
 * AxiomOS Particles.js Utilities
 * Shared utilities for particle effects and interactions
 */

class ParticlesManager {
    constructor() {
        this.defaultConfig = {
            "particles": {
                "number": {
                    "value": 50,  // Reduced from 100 for better performance
                    "density": {
                        "enable": true,
                        "value_area": 1000  // Increased area to spread particles more
                    }
                },
                "color": {
                    "value": "#45e2f2"
                },
                "shape": {
                    "type": "circle"
                },
                "opacity": {
                    "value": 0.4,  // Reduced opacity for less visual load
                    "random": false,
                    "anim": {
                        "enable": false,
                        "speed": 1,
                        "opacity_min": 0.1,
                        "sync": false
                    }
                },
                "size": {
                    "value": 2,  // Smaller particles
                    "random": true,
                    "anim": {
                        "enable": false,
                        "speed": 40,
                        "size_min": 0.1,
                        "sync": false
                    }
                },
                "line_linked": {
                    "enable": true,
                    "distance": 120,  // Reduced distance
                    "color": "#d1daff",
                    "opacity": 0.2,  // Reduced opacity
                    "width": 1
                },
                "move": {
                    "enable": true,
                    "speed": 1.5,  // Slower movement
                    "direction": "none",
                    "random": false,
                    "straight": false,
                    "out_mode": "out",
                    "bounce": false,
                    "attract": {
                        "enable": false,
                        "rotateX": 600,
                        "rotateY": 1200
                    }
                }
            },
            "interactivity": {
                "detect_on": "canvas",
                "events": {
                    "onhover": {
                        "enable": true,
                        "mode": "repulse"
                    },
                    "onclick": {
                        "enable": false,  // Disabled for performance
                        "mode": "push"
                    },
                    "resize": true
                },
                "modes": {
                    "grab": {
                        "distance": 140,  // Reduced distance
                        "line_linked": {
                            "opacity": 1
                        }
                    },
                    "bubble": {
                        "distance": 200,  // Reduced distance
                        "size": 20,  // Smaller bubbles
                        "duration": 2,
                        "opacity": 4,
                        "speed": 3
                    },
                    "repulse": {
                        "distance": 100,  // Reduced distance
                        "duration": 0.4
                    },
                    "push": {
                        "particles_nb": 2  // Reduced from 4
                    },
                    "remove": {
                        "particles_nb": 2
                    }
                }
            },
            "retina_detect": true
        };
    }

    /**
     * Initialize particles with page-specific configuration
     */
    init(pageType = 'default') {
        const config = this.getConfigForPage(pageType);
        
        if (typeof particlesJS !== 'undefined') {
            particlesJS('particles-js', config);
            this.addInteractivity();
        } else {
            console.warn('particles.js not loaded');
        }
    }

    /**
     * Get configuration specific to each page
     */
    getConfigForPage(pageType) {
        const configs = {
            'home': {
                particles: {
                    number: { value: 60, density: { value_area: 900 } },  // Reduced from 120
                    color: { value: "#45e2f2" },
                    opacity: { value: 0.5 },
                    size: { value: 2.5, random: true },  // Smaller
                    line_linked: { distance: 130, color: "#d1daff", opacity: 0.3 },
                    move: { speed: 2 }  // Slower
                },
                interactivity: {
                    events: {
                        onhover: { enable: true, mode: "repulse" },
                        onclick: { enable: false }  // Disabled for performance
                    }
                }
            },
            'chat': {
                particles: {
                    number: { value: 40, density: { value_area: 1000 } },  // Reduced from 80
                    color: { value: "#45e2f2" },
                    opacity: { value: 0.3 },
                    size: { value: 1.5, random: true },  // Smaller
                    line_linked: { distance: 100, color: "#d1daff", opacity: 0.2 },
                    move: { speed: 1.5 }  // Slower
                },
                interactivity: {
                    events: {
                        onhover: { enable: true, mode: "repulse" },
                        onclick: { enable: false }
                    }
                }
            },
            'memory': {
                particles: {
                    number: { value: 45, density: { value_area: 950 } },  // Reduced from 100
                    color: { value: "#45e2f2" },
                    opacity: { value: 0.3 },
                    size: { value: 2, random: true },  // Smaller
                    line_linked: { distance: 110, color: "#d1daff", opacity: 0.2 },
                    move: { speed: 1.8 }  // Slower
                },
                interactivity: {
                    events: {
                        onhover: { enable: true, mode: "repulse" },
                        onclick: { enable: false }
                    }
                }
            },
            'settings': {
                particles: {
                    number: { value: 30, density: { value_area: 1200 } },  // Reduced from 60
                    color: { value: "#45e2f2" },
                    opacity: { value: 0.2 },
                    size: { value: 1.5, random: true },  // Smaller
                    line_linked: { distance: 100, color: "#d1daff", opacity: 0.15 },
                    move: { speed: 1.2 }  // Slower
                },
                interactivity: {
                    events: {
                        onhover: { enable: false },  // Disabled for settings page
                        onclick: { enable: false }
                    }
                }
            }
        };

        return this.deepMerge(this.defaultConfig, configs[pageType] || {});
    }

    /**
     * Deep merge two objects
     */
    deepMerge(target, source) {
        const result = { ...target };
        
        for (const key in source) {
            if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
                result[key] = this.deepMerge(result[key] || {}, source[key]);
            } else {
                result[key] = source[key];
            }
        }
        
        return result;
    }

    /**
     * Add interactive features to particles
     */
    addInteractivity() {
        // Add keyboard controls
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch(e.key) {
                    case 'p':
                        e.preventDefault();
                        this.toggleParticles();
                        break;
                    case 'r':
                        e.preventDefault();
                        this.refreshParticles();
                        break;
                }
            }
        });

        // Add performance monitoring
        this.monitorPerformance();
    }

    /**
     * Toggle particles on/off
     */
    toggleParticles() {
        const canvas = document.querySelector('#particles-js canvas');
        if (canvas) {
            canvas.style.display = canvas.style.display === 'none' ? 'block' : 'none';
        }
    }

    /**
     * Refresh/restart particles
     */
    refreshParticles() {
        const container = document.getElementById('particles-js');
        if (container) {
            container.innerHTML = '';
            const pageType = this.getCurrentPageType();
            this.init(pageType);
        }
    }

    /**
     * Get current page type based on URL
     */
    getCurrentPageType() {
        const path = window.location.pathname;
        if (path.includes('chat.html')) return 'chat';
        if (path.includes('memory.html')) return 'memory';
        if (path.includes('settings.html')) return 'settings';
        return 'home';
    }

    /**
     * Monitor performance and adjust particles if needed
     */
    monitorPerformance() {
        let frameCount = 0;
        let lastTime = performance.now();
        
        const checkPerformance = () => {
            frameCount++;
            const currentTime = performance.now();
            
            if (currentTime - lastTime >= 1000) {
                const fps = frameCount;
                frameCount = 0;
                lastTime = currentTime;
                
                // Reduce particles if performance is poor
                if (fps < 30 && this.pJSDom && this.pJSDom[0]) {
                    const currentParticles = this.pJSDom[0].pJS.particles.number.value;
                    if (currentParticles > 30) {
                        this.pJSDom[0].pJS.particles.number.value = Math.floor(currentParticles * 0.8);
                        this.pJSDom[0].pJS.fn.particlesRefresh();
                    }
                }
            }
            
            requestAnimationFrame(checkPerformance);
        };
        
        requestAnimationFrame(checkPerformance);
    }

    /**
     * Update particle colors based on theme
     */
    updateColors(primaryColor = "#45e2f2", secondaryColor = "#d1daff") {
        if (this.pJSDom && this.pJSDom[0]) {
            this.pJSDom[0].pJS.particles.color.value = primaryColor;
            this.pJSDom[0].pJS.particles.line_linked.color = secondaryColor;
            this.pJSDom[0].pJS.fn.particlesRefresh();
        }
    }

    /**
     * Create particle burst effect
     */
    createBurst(x, y, count = 20) {
        if (this.pJSDom && this.pJSDom[0]) {
            const pJS = this.pJSDom[0].pJS;
            for (let i = 0; i < count; i++) {
                pJS.fn.modes.pushParticles(1, { pos_x: x, pos_y: y });
            }
        }
    }

    /**
     * Add attraction point
     */
    addAttractionPoint(x, y, strength = 1000) {
        if (this.pJSDom && this.pJSDom[0]) {
            const pJS = this.pJSDom[0].pJS;
            pJS.particles.move.attract.enable = true;
            pJS.particles.move.attract.rotateX = strength;
            pJS.particles.move.attract.rotateY = strength;
            
            // Move attraction point to mouse position
            pJS.interactivity.mouse.pos_x = x;
            pJS.interactivity.mouse.pos_y = y;
        }
    }

    /**
     * Remove attraction point
     */
    removeAttractionPoint() {
        if (this.pJSDom && this.pJSDom[0]) {
            const pJS = this.pJSDom[0].pJS;
            pJS.particles.move.attract.enable = false;
        }
    }
}

// Global particles manager instance
window.particlesManager = new ParticlesManager();

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const pageType = window.particlesManager.getCurrentPageType();
    window.particlesManager.init(pageType);
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ParticlesManager;
}
