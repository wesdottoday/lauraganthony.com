/**
 * Main JavaScript for Laura Anthony's website
 * Handles navigation, accessibility, and interactive features
 */

(function() {
    'use strict';
    
    // DOM elements
    const navToggle = document.getElementById('nav-toggle');
    const navMenu = document.getElementById('nav-menu');
    const navigation = document.querySelector('.hamburger-nav');
    const hero = document.querySelector('.hero');
    
    // State
    let lastScrollY = window.scrollY;
    let isMenuOpen = false;
    
    /**
     * Initialize all functionality when DOM is loaded
     */
    function init() {
        setupMobileNavigation();
        setupScrollBehavior();
        setupFormEnhancements();
        setupAccessibilityFeatures();
        setupLogoCarousel();
        setupModal();
    }
    
    /**
     * Setup mobile navigation menu
     */
    function setupMobileNavigation() {
        if (!navToggle || !navMenu) return;
        
        navToggle.addEventListener('click', toggleMobileMenu);
        navToggle.addEventListener('touchend', function(e) {
            e.preventDefault();
            toggleMobileMenu();
        });
        
        // Close menu when clicking outside
        document.addEventListener('click', function(event) {
            if (isMenuOpen && !navigation.contains(event.target)) {
                closeMobileMenu();
            }
        });
        
        // Close menu on escape key
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape' && isMenuOpen) {
                closeMobileMenu();
                navToggle.focus();
            }
        });
        
        // Close menu when window is resized to desktop size
        window.addEventListener('resize', function() {
            if (window.innerWidth >= 768 && isMenuOpen) {
                closeMobileMenu();
            }
        });
    }
    
    /**
     * Toggle mobile menu open/closed
     */
    function toggleMobileMenu() {
        isMenuOpen = !isMenuOpen;
        
        navToggle.setAttribute('aria-expanded', isMenuOpen.toString());
        
        if (isMenuOpen) {
            navMenu.classList.add('nav-menu--open');
            // Focus first menu item for keyboard navigation
            const firstMenuItem = navMenu.querySelector('.nav-link');
            if (firstMenuItem) {
                firstMenuItem.focus();
            }
        } else {
            navMenu.classList.remove('nav-menu--open');
        }
    }
    
    /**
     * Close mobile menu
     */
    function closeMobileMenu() {
        isMenuOpen = false;
        navToggle.setAttribute('aria-expanded', 'false');
        navMenu.classList.remove('nav-menu--open');
    }
    
    /**
     * Setup scroll behavior for navigation visibility
     */
    function setupScrollBehavior() {
        if (!navigation || !hero) return;
        
        let ticking = false;
        
        function updateNavigation() {
            const currentScrollY = window.scrollY;
            const heroHeight = hero.offsetHeight;
            
            // Hide navigation when scrolling down past hero section
            if (currentScrollY > heroHeight && currentScrollY > lastScrollY) {
                navigation.classList.add('hidden');
            } else {
                navigation.classList.remove('hidden');
            }
            
            lastScrollY = currentScrollY;
            ticking = false;
        }
        
        function onScroll() {
            if (!ticking) {
                requestAnimationFrame(updateNavigation);
                ticking = true;
            }
        }
        
        // Use passive listener for better performance
        window.addEventListener('scroll', onScroll, { passive: true });
    }
    
    /**
     * Enhance form accessibility and user experience
     */
    function setupFormEnhancements() {
        const contactForm = document.querySelector('.contact-form form');
        if (!contactForm) return;
        
        // Add form validation
        contactForm.addEventListener('submit', function(event) {
            const isValid = validateForm(contactForm);
            if (!isValid) {
                event.preventDefault();
            }
        });
        
        // Real-time validation feedback
        const inputs = contactForm.querySelectorAll('input, textarea');
        inputs.forEach(input => {
            input.addEventListener('blur', function() {
                validateField(input);
            });
            
            input.addEventListener('input', function() {
                clearFieldError(input);
            });
        });
    }
    
    /**
     * Validate entire form
     */
    function validateForm(form) {
        const inputs = form.querySelectorAll('input[required], textarea[required]');
        let isValid = true;
        
        inputs.forEach(input => {
            if (!validateField(input)) {
                isValid = false;
            }
        });
        
        return isValid;
    }
    
    /**
     * Validate individual form field
     */
    function validateField(field) {
        const value = field.value.trim();
        const isRequired = field.hasAttribute('required');
        let isValid = true;
        let errorMessage = '';
        
        // Clear previous errors
        clearFieldError(field);
        
        // Required field validation
        if (isRequired && !value) {
            isValid = false;
            errorMessage = 'This field is required.';
        }
        
        // Email validation
        if (field.type === 'email' && value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(value)) {
                isValid = false;
                errorMessage = 'Please enter a valid email address.';
            }
        }
        
        if (!isValid) {
            showFieldError(field, errorMessage);
        }
        
        return isValid;
    }
    
    /**
     * Show field error
     */
    function showFieldError(field, message) {
        field.setAttribute('aria-invalid', 'true');
        field.style.borderColor = 'var(--color-callout)';
        
        // Create error message element
        const errorId = field.id + '-error';
        let errorElement = document.getElementById(errorId);
        
        if (!errorElement) {
            errorElement = document.createElement('div');
            errorElement.id = errorId;
            errorElement.className = 'field-error';
            errorElement.style.color = 'var(--color-callout)';
            errorElement.style.fontSize = 'var(--font-size-sm)';
            errorElement.style.marginTop = 'var(--spacing-xs)';
            field.parentNode.appendChild(errorElement);
        }
        
        errorElement.textContent = message;
        field.setAttribute('aria-describedby', errorId);
    }
    
    /**
     * Clear field error
     */
    function clearFieldError(field) {
        field.removeAttribute('aria-invalid');
        field.style.borderColor = '';
        field.removeAttribute('aria-describedby');
        
        const errorId = field.id + '-error';
        const errorElement = document.getElementById(errorId);
        if (errorElement) {
            errorElement.remove();
        }
    }
    
    /**
     * Setup accessibility features
     */
    function setupAccessibilityFeatures() {
        // Smooth scroll for anchor links with accessibility consideration
        const anchorLinks = document.querySelectorAll('a[href^="#"]');
        anchorLinks.forEach(link => {
            link.addEventListener('click', function(event) {
                const targetId = this.getAttribute('href').substring(1);
                const targetElement = document.getElementById(targetId);
                
                if (targetElement) {
                    event.preventDefault();
                    
                    // Check for reduced motion preference
                    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
                    
                    targetElement.scrollIntoView({
                        behavior: prefersReducedMotion ? 'auto' : 'smooth',
                        block: 'start'
                    });
                    
                    // Focus the target element for screen readers
                    targetElement.focus({ preventScroll: true });
                }
            });
        });
        
        // Enhanced keyboard navigation for cards
        const cards = document.querySelectorAll('.talk-card, .quote-card');
        cards.forEach(card => {
            // Make cards focusable if they contain interactive elements
            const link = card.querySelector('a');
            if (link) {
                card.addEventListener('keydown', function(event) {
                    if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault();
                        link.click();
                    }
                });
            }
        });
    }
    
    /**
     * Setup logo carousel with accessibility features
     */
    function setupLogoCarousel() {
        const carousel = document.querySelector('.logos-carousel');
        const track = document.querySelector('.logos-track');
        
        if (!carousel || !track) return;
        
        // Pause animation on hover or focus for accessibility
        carousel.addEventListener('mouseenter', function() {
            track.style.animationPlayState = 'paused';
        });
        
        carousel.addEventListener('mouseleave', function() {
            track.style.animationPlayState = 'running';
        });
        
        carousel.addEventListener('focusin', function() {
            track.style.animationPlayState = 'paused';
        });
        
        carousel.addEventListener('focusout', function() {
            track.style.animationPlayState = 'running';
        });
        
        // Respect reduced motion preference
        const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
        if (prefersReducedMotion.matches) {
            track.style.animation = 'none';
        }
        
        // Listen for changes in motion preference
        prefersReducedMotion.addEventListener('change', function() {
            if (prefersReducedMotion.matches) {
                track.style.animation = 'none';
            } else {
                track.style.animation = '';
            }
        });
        
        // Duplicate logos for seamless loop
        const logos = track.children;
        const logoCount = logos.length;
        
        // Clone logos for seamless infinite scroll
        for (let i = 0; i < logoCount; i++) {
            const clone = logos[i].cloneNode(true);
            track.appendChild(clone);
        }
    }
    
    /**
     * Setup modal functionality
     */
    function setupModal() {
        const contactModalTrigger = document.getElementById('contactModalTrigger');
        const leadMagnetTrigger = document.getElementById('leadMagnetTrigger');
        const contactTrigger = document.getElementById('contactTrigger');
        const modal = document.getElementById('contactModal');
        const modalClose = document.querySelector('.modal-close');
        const modalOverlay = document.querySelector('.modal-overlay');
        const form = document.getElementById('mc-embedded-subscribe-form');
        
        if (!modal) return;
        
        // Track which button opened the modal
        let activeModalTrigger = null;
        
        // Open modal
        function openModal(triggerElement) {
            activeModalTrigger = triggerElement;
            modal.style.display = 'flex';
            modal.setAttribute('aria-hidden', 'false');
            document.body.style.overflow = 'hidden';
            
            // Focus the first input field
            setTimeout(() => {
                const firstInput = modal.querySelector('input');
                if (firstInput) firstInput.focus();
            }, 100);
        }
        
        // Close modal
        function closeModal() {
            modal.style.display = 'none';
            modal.setAttribute('aria-hidden', 'true');
            document.body.style.overflow = '';
            // Return focus to the specific button that opened the modal
            if (activeModalTrigger) {
                activeModalTrigger.focus();
                activeModalTrigger = null;
            }
        }
        
        // Event listeners
        if (contactModalTrigger) {
            contactModalTrigger.addEventListener('click', function() {
                openModal(contactModalTrigger);
            });
        }
        
        if (leadMagnetTrigger) {
            leadMagnetTrigger.addEventListener('click', function() {
                openModal(leadMagnetTrigger);
            });
        }
        
        if (contactTrigger) {
            contactTrigger.addEventListener('click', function() {
                openModal(contactTrigger);
            });
        }
        
        // Handle form submission for lead magnet redirect
        if (form) {
            form.addEventListener('submit', function(event) {
                // Allow the form to submit to Mailchimp first
                setTimeout(function() {
                    // Redirect to PDF after a short delay to allow form submission
                    window.open('/neuroinclusive-interview-tips.pdf', '_blank');
                    closeModal();
                }, 1000);
            });
        }
        
        if (modalClose) {
            modalClose.addEventListener('click', closeModal);
        }
        
        if (modalOverlay) {
            modalOverlay.addEventListener('click', closeModal);
        }
        
        // Close on Escape key
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape' && modal.style.display === 'flex') {
                closeModal();
            }
        });
    }
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
})();