/**
 * AxiomOS Glassmorphism Utilities
 * Shared utilities for glassmorphism effects and interactions
 */

class GlassmorphismUtils {
    constructor() {
        this.isAnimating = false;
        this.ripples = [];
        this.init();
    }

    /**
     * Initialize glassmorphism utilities
     */
    init() {
        this.setupRippleEffects();
        this.setupHoverEffects();
        this.setupScrollAnimations();
        this.setupKeyboardShortcuts();
        this.setupThemeDetection();
    }

    /**
     * Setup ripple effect for clickable elements
     */
    setupRippleEffects() {
        document.addEventListener('click', (e) => {
            const target = e.target.closest('.glass-card, .feature-card, .memory-card, .nav-item, .send-button');
            if (target) {
                this.createRipple(e, target);
            }
        });
    }

    /**
     * Create ripple effect
     */
    createRipple(event, element) {
        const ripple = document.createElement('span');
        const rect = element.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = event.clientX - rect.left - size / 2;
        const y = event.clientY - rect.top - size / 2;

        ripple.style.cssText = `
            position: absolute;
            border-radius: 50%;
            background: rgba(69, 226, 242, 0.3);
            transform: scale(0);
            animation: ripple 0.6s linear;
            width: ${size}px;
            height: ${size}px;
            left: ${x}px;
            top: ${y}px;
            pointer-events: none;
            z-index: 1;
        `;

        element.style.position = 'relative';
        element.style.overflow = 'hidden';
        element.appendChild(ripple);

        setTimeout(() => {
            ripple.remove();
        }, 600);
    }

    /**
     * Setup enhanced hover effects
     */
    setupHoverEffects() {
        // Add magnetic effect to navigation items
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('mousemove', (e) => {
                const rect = item.getBoundingClientRect();
                const x = e.clientX - rect.left - rect.width / 2;
                const y = e.clientY - rect.top - rect.height / 2;
                
                item.style.transform = `translate(${x * 0.1}px, ${y * 0.1}px)`;
            });

            item.addEventListener('mouseleave', () => {
                item.style.transform = 'translate(0, 0)';
            });
        });

        // Parallax effect for glass cards
        document.querySelectorAll('.glass-card').forEach(card => {
            card.addEventListener('mousemove', (e) => {
                const rect = card.getBoundingClientRect();
                const x = (e.clientX - rect.left) / rect.width;
                const y = (e.clientY - rect.top) / rect.height;
                
                card.style.background = `
                    radial-gradient(
                        circle at ${x * 100}% ${y * 100}%,
                        rgba(255, 255, 255, 0.15) 0%,
                        rgba(255, 255, 255, 0.1) 50%,
                        rgba(255, 255, 255, 0.05) 100%
                    )
                `;
            });

            card.addEventListener('mouseleave', () => {
                card.style.background = '';
            });
        });
    }

    /**
     * Setup scroll animations
     */
    setupScrollAnimations() {
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    this.animateElement(entry.target);
                }
            });
        }, observerOptions);

        // Observe elements for animation
        document.querySelectorAll('.glass-card, .feature-card, .memory-card, .settings-section').forEach(el => {
            observer.observe(el);
        });
    }

    /**
     * Animate element on scroll
     */
    animateElement(element) {
        element.style.opacity = '0';
        element.style.transform = 'translateY(30px)';
        
        setTimeout(() => {
            element.style.transition = 'all 0.6s cubic-bezier(0.4, 0, 0.2, 1)';
            element.style.opacity = '1';
            element.style.transform = 'translateY(0)';
        }, 100);
    }

    /**
     * Setup keyboard shortcuts
     */
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + K for quick search
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                this.openQuickSearch();
            }

            // Ctrl/Cmd + / for help
            if ((e.ctrlKey || e.metaKey) && e.key === '/') {
                e.preventDefault();
                this.showHelp();
            }

            // Escape to close modals
            if (e.key === 'Escape') {
                this.closeModals();
            }
        });
    }

    /**
     * Setup theme detection and auto-switching
     */
    setupThemeDetection() {
        const hour = new Date().getHours();
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        
        // Auto-adjust theme based on time of day
        if (hour >= 6 && hour < 18) {
            document.body.classList.add('day-theme');
        } else {
            document.body.classList.add('night-theme');
        }

        // Listen for system theme changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (e.matches) {
                document.body.classList.add('night-theme');
                document.body.classList.remove('day-theme');
            } else {
                document.body.classList.add('day-theme');
                document.body.classList.remove('night-theme');
            }
        });
    }

    /**
     * Open quick search modal
     */
    openQuickSearch() {
        const modal = this.createModal('quick-search-modal', `
            <div class="glass-card" style="max-width: 600px; width: 90%;">
                <h3 style="margin-bottom: 1rem; color: var(--text-primary);">🔍 Quick Search</h3>
                <input type="text" id="quickSearchInput" placeholder="Search anything..." 
                       style="
                           width: 100%;
                           background: rgba(255, 255, 255, 0.05);
                           border: 1px solid rgba(255, 255, 255, 0.1);
                           border-radius: var(--radius-md);
                           padding: 1rem;
                           color: var(--text-primary);
                           font-size: 1rem;
                           outline: none;
                           margin-bottom: 1rem;
                       " autofocus>
                <div id="searchResults" style="max-height: 300px; overflow-y: auto;"></div>
                <div style="text-align: right; margin-top: 1rem;">
                    <button onclick="glassmorphismUtils.closeModal('quick-search-modal')" 
                            class="nav-item" style="display: inline-block; padding: 0.5rem 1rem;">
                        Close
                    </button>
                </div>
            </div>
        `);

        // Focus input and setup search
        setTimeout(() => {
            const input = document.getElementById('quickSearchInput');
            if (input) {
                input.focus();
                input.addEventListener('input', (e) => this.performQuickSearch(e.target.value));
            }
        }, 100);
    }

    /**
     * Perform quick search
     */
    performQuickSearch(query) {
        const resultsDiv = document.getElementById('searchResults');
        
        if (!query.trim()) {
            resultsDiv.innerHTML = '<div style="color: var(--text-muted); text-align: center;">Type to search...</div>';
            return;
        }

        // Mock search results (replace with actual search logic)
        const results = [
            { title: 'Chat with AI', url: '/static/chat.html', type: 'page' },
            { title: 'View Memories', url: '/static/memory.html', type: 'page' },
            { title: 'Settings', url: '/static/settings.html', type: 'page' }
        ].filter(item => item.title.toLowerCase().includes(query.toLowerCase()));

        if (results.length > 0) {
            resultsDiv.innerHTML = results.map(result => `
                <div onclick="window.location.href='${result.url}'" style="
                    padding: 0.75rem;
                    margin-bottom: 0.5rem;
                    background: rgba(255, 255, 255, 0.05);
                    border-radius: var(--radius-sm);
                    cursor: pointer;
                    transition: all var(--transition-fast);
                " onmouseover="this.style.background='rgba(255, 255, 255, 0.1)'" 
                   onmouseout="this.style.background='rgba(255, 255, 255, 0.05)'">
                    <div style="font-weight: 500; color: var(--text-primary);">${result.title}</div>
                    <div style="font-size: 0.8rem; color: var(--text-muted);">${result.type}</div>
                </div>
            `).join('');
        } else {
            resultsDiv.innerHTML = '<div style="color: var(--text-muted); text-align: center;">No results found</div>';
        }
    }

    /**
     * Show help modal
     */
    showHelp() {
        this.createModal('help-modal', `
            <div class="glass-card" style="max-width: 500px; width: 90%;">
                <h3 style="margin-bottom: 1rem; color: var(--text-primary);">⌨️ Keyboard Shortcuts</h3>
                <div style="color: var(--text-secondary); line-height: 1.8;">
                    <div style="margin-bottom: 0.5rem;"><kbd>Ctrl/Cmd + K</kbd> - Quick Search</div>
                    <div style="margin-bottom: 0.5rem;"><kbd>Ctrl/Cmd + P</kbd> - Toggle Particles</div>
                    <div style="margin-bottom: 0.5rem;"><kbd>Ctrl/Cmd + R</kbd> - Refresh Particles</div>
                    <div style="margin-bottom: 0.5rem;"><kbd>Ctrl/Cmd + /</kbd> - Show Help</div>
                    <div style="margin-bottom: 0.5rem;"><kbd>Escape</kbd> - Close Modals</div>
                </div>
                <div style="text-align: right; margin-top: 1.5rem;">
                    <button onclick="glassmorphismUtils.closeModal('help-modal')" 
                            class="send-button" style="display: inline-block;">
                        Got it!
                    </button>
                </div>
            </div>
        `);
    }

    /**
     * Create modal
     */
    createModal(id, content) {
        // Remove existing modal if it exists
        const existingModal = document.getElementById(id);
        if (existingModal) {
            existingModal.remove();
        }

        const modal = document.createElement('div');
        modal.id = id;
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(10px);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            animation: fadeIn 0.3s ease-out;
        `;

        modal.innerHTML = content;
        document.body.appendChild(modal);

        // Close on background click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.closeModal(id);
            }
        });
    }

    /**
     * Close modal
     */
    closeModal(id) {
        const modal = document.getElementById(id);
        if (modal) {
            modal.style.animation = 'fadeOut 0.3s ease-out';
            setTimeout(() => modal.remove(), 300);
        }
    }

    /**
     * Close all modals
     */
    closeModals() {
        document.querySelectorAll('[id$="-modal"]').forEach(modal => {
            this.closeModal(modal.id);
        });
    }

    /**
     * Show notification
     */
    showNotification(message, type = 'info', duration = 3000) {
        const notification = document.createElement('div');
        const colors = {
            success: 'rgba(74, 222, 128, 0.9)',
            error: 'rgba(239, 68, 68, 0.9)',
            warning: 'rgba(245, 158, 11, 0.9)',
            info: 'rgba(69, 226, 242, 0.9)'
        };

        notification.style.cssText = `
            position: fixed;
            top: 100px;
            right: 20px;
            background: ${colors[type]};
            color: white;
            padding: 1rem 1.5rem;
            border-radius: var(--radius-md);
            box-shadow: var(--glass-shadow);
            z-index: 10000;
            animation: slideInRight 0.3s ease-out;
            max-width: 300px;
            backdrop-filter: blur(10px);
        `;
        notification.textContent = message;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease-out';
            setTimeout(() => notification.remove(), 300);
        }, duration);
    }

    /**
     * Add glassmorphism effect to element
     */
    addGlassEffect(element, intensity = 1) {
        element.style.background = `rgba(255, 255, 255, ${0.1 * intensity})`;
        element.style.backdropFilter = `blur(${20 * intensity}px)`;
        element.style.border = `1px solid rgba(255, 255, 255, ${0.2 * intensity})`;
        element.style.boxShadow = `0 ${8 * intensity}px ${32 * intensity}px rgba(0, 0, 0, ${0.1 * intensity})`;
    }

    /**
     * Remove glassmorphism effect from element
     */
    removeGlassEffect(element) {
        element.style.background = '';
        element.style.backdropFilter = '';
        element.style.border = '';
        element.style.boxShadow = '';
    }

    /**
     * Create floating animation
     */
    createFloatAnimation(element, amplitude = 10, duration = 3) {
        element.style.animation = `float ${duration}s ease-in-out infinite`;
        
        // Add keyframes if not already added
        if (!document.querySelector('#float-keyframes')) {
            const style = document.createElement('style');
            style.id = 'float-keyframes';
            style.textContent = `
                @keyframes float {
                    0%, 100% { transform: translateY(0px); }
                    50% { transform: translateY(-${amplitude}px); }
                }
            `;
            document.head.appendChild(style);
        }
    }

    /**
     * Create pulse animation
     */
    createPulseAnimation(element, duration = 2) {
        element.style.animation = `pulse ${duration}s ease-in-out infinite`;
        
        // Add keyframes if not already added
        if (!document.querySelector('#pulse-keyframes')) {
            const style = document.createElement('style');
            style.id = 'pulse-keyframes';
            style.textContent = `
                @keyframes pulse {
                    0%, 100% { transform: scale(1); }
                    50% { transform: scale(1.05); }
                }
            `;
            document.head.appendChild(style);
        }
    }
}

// Global glassmorphism utilities instance
window.glassmorphismUtils = new GlassmorphismUtils();

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = GlassmorphismUtils;
}
