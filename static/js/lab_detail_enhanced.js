/**
 * Lab Detail Page Enhancements
 * Provides interactive features and UX improvements
 */

class LabDetailEnhancer {
    constructor() {
        this.init();
    }

    init() {
        this.setupFilterTabs();
        this.setupComputerCards();
        this.setupResponsiveFeatures();
        this.setupAccessibility();
    }

    /**
     * Setup filter tabs for filtering computers by status
     */
    setupFilterTabs() {
        const filterTabs = document.querySelectorAll('.filter-tab');
        const computerCards = document.querySelectorAll('.computer-card');

        filterTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                // Update active state
                filterTabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');

                const filterStatus = tab.getAttribute('data-filter');
                this.filterComputers(filterStatus, computerCards);
            });
        });
    }

    /**
     * Filter computers based on status
     */
    filterComputers(status, cards) {
        cards.forEach(card => {
            if (status === 'all' || card.getAttribute('data-status') === status) {
                card.style.display = '';
                setTimeout(() => {
                    card.style.animation = 'slideInUp 0.3s ease-out';
                }, 0);
            } else {
                card.style.animation = 'slideInUp 0.3s ease-out reverse';
                setTimeout(() => {
                    card.style.display = 'none';
                }, 300);
            }
        });

        // Show/hide empty state
        this.updateComputersDisplay();
    }

    /**
     * Setup computer card interactions
     */
    setupComputerCards() {
        const computerCards = document.querySelectorAll('.computer-card');

        computerCards.forEach(card => {
            // Add hover effect feedback
            card.addEventListener('mouseenter', () => {
                card.style.transform = 'translateY(-4px)';
            });

            card.addEventListener('mouseleave', () => {
                card.style.transform = 'translateY(0)';
            });

            // Add touch feedback for mobile
            card.addEventListener('touchstart', () => {
                card.style.transform = 'scale(0.98)';
            });

            card.addEventListener('touchend', () => {
                card.style.transform = 'scale(1)';
            });

            // Track booking click
            const bookButton = card.querySelector('a[href*="computer_booking"]');
            if (bookButton) {
                bookButton.addEventListener('click', (e) => {
                    this.trackBookingClick(card);
                });
            }
        });
    }

    /**
     * Setup responsive features
     */
    setupResponsiveFeatures() {
        // Smooth scroll behavior for anchor links
        document.querySelectorAll('a[href^="#"]').forEach(link => {
            link.addEventListener('click', (e) => {
                const target = document.querySelector(link.getAttribute('href'));
                if (target) {
                    e.preventDefault();
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            });
        });

        // Handle window resize for responsive adjustments
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                this.adjustResponsiveLayout();
            }, 250);
        });
    }

    /**
     * Adjust layout based on screen size
     */
    adjustResponsiveLayout() {
        const computersGrid = document.querySelector('.computers-grid');
        if (!computersGrid) return;

        const screenWidth = window.innerWidth;
        const cards = computersGrid.querySelectorAll('.computer-card');

        if (screenWidth < 640) {
            computersGrid.style.gridTemplateColumns = '1fr';
        } else if (screenWidth < 1024) {
            computersGrid.style.gridTemplateColumns = 'repeat(2, 1fr)';
        } else {
            computersGrid.style.gridTemplateColumns = 'repeat(auto-fill, minmax(280px, 1fr))';
        }
    }

    /**
     * Setup accessibility features
     */
    setupAccessibility() {
        // Add keyboard navigation
        const computerCards = document.querySelectorAll('.computer-card');
        
        computerCards.forEach((card, index) => {
            card.setAttribute('tabindex', '0');
            
            card.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    const bookButton = card.querySelector('a[href*="computer_booking"], .flex-1:not(.bg-gray-100):not(.bg-red-100):not(.bg-amber-100) a');
                    if (bookButton) {
                        bookButton.click();
                    }
                }
            });
        });

        // Ensure all interactive elements are keyboard accessible
        this.ensureKeyboardAccessibility();
    }

    /**
     * Ensure keyboard accessibility
     */
    ensureKeyboardAccessibility() {
        const focusableElements = document.querySelectorAll(
            'a, button, [tabindex]:not([tabindex="-1"])'
        );

        focusableElements.forEach(element => {
            element.addEventListener('focus', () => {
                element.style.outline = '2px solid var(--ttu-green)';
                element.style.outlineOffset = '2px';
            });

            element.addEventListener('blur', () => {
                element.style.outline = '';
            });
        });
    }

    /**
     * Track booking clicks (for analytics)
     */
    trackBookingClick(card) {
        const computerId = card.getAttribute('data-computer-id');
        const status = card.getAttribute('data-status');
        
        // Log to console (you can send to analytics service)
        console.log(`User clicked to book computer ${computerId} (Status: ${status})`);

        // You can add Google Analytics or other tracking here
        if (typeof gtag !== 'undefined') {
            gtag('event', 'computer_booking_clicked', {
                computer_id: computerId,
                status: status
            });
        }
    }

    /**
     * Update display of computers section
     */
    updateComputersDisplay() {
        const computerCards = document.querySelectorAll('.computer-card:not([style*="display: none"])');
        const emptyState = document.querySelector('.empty-state');
        
        if (computerCards.length === 0 && emptyState) {
            emptyState.style.display = 'flex';
        } else if (emptyState) {
            emptyState.style.display = 'none';
        }
    }

    /**
     * Add animation observer for intersection
     */
    setupIntersectionObserver() {
        if (!('IntersectionObserver' in window)) return;

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.animation = 'slideInUp 0.6s ease-out forwards';
                }
            });
        }, {
            threshold: 0.1
        });

        document.querySelectorAll('.info-card, .computers-section').forEach(el => {
            observer.observe(el);
        });
    }

    /**
     * Get computer statistics
     */
    getComputerStats() {
        const stats = {
            total: 0,
            available: 0,
            reserved: 0,
            maintenance: 0
        };

        document.querySelectorAll('.computer-card').forEach(card => {
            const status = card.getAttribute('data-status');
            stats.total++;
            
            if (status === 'available') stats.available++;
            else if (status === 'reserved') stats.reserved++;
            else if (status === 'maintenance') stats.maintenance++;
        });

        return stats;
    }

    /**
     * Export computer list as CSV (optional enhancement)
     */
    exportComputersAsCSV() {
        const stats = this.getComputerStats();
        const timestamp = new Date().toLocaleString();
        
        let csv = 'Lab Computer Report\n';
        csv += `Generated: ${timestamp}\n\n`;
        csv += 'Computer #,Status\n';
        
        document.querySelectorAll('.computer-card').forEach(card => {
            const computerNumber = card.querySelector('.card-title')?.textContent || 'Unknown';
            const status = card.getAttribute('data-status');
            csv += `${computerNumber.replace('Computer #', '')},${status}\n`;
        });

        this.downloadCSV(csv, 'lab_computers.csv');
    }

    /**
     * Download CSV file
     */
    downloadCSV(csv, filename) {
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

/**
 * Initialize enhancements when DOM is ready
 */
document.addEventListener('DOMContentLoaded', () => {
    const enhancer = new LabDetailEnhancer();
    
    // Setup intersection observer for animations
    enhancer.setupIntersectionObserver();
    
    // Log stats to console
    console.log('Lab statistics:', enhancer.getComputerStats());
    
    // Expose to global scope for debugging
    window.labDetailEnhancer = enhancer;
});

/**
 * Handle page visibility changes
 */
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        console.log('Lab detail page hidden');
    } else {
        console.log('Lab detail page visible');
    }
});
