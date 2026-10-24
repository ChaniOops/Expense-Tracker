// Global JavaScript for Expense Tracker

/**
 * Format a numeric amount using the Indian numbering system with the Rupee symbol (₹).
 * Examples: 125000 -> ₹1,25,000.00
 */
function formatINR(amount) {
    if (amount === null || amount === undefined || isNaN(amount)) {
        return '₹0.00';
    }
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(amount);
}

document.addEventListener('DOMContentLoaded', function () {
    // Enable Bootstrap tooltips if any exist
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Password Visibility Show/Hide Toggle
    const toggleButtons = document.querySelectorAll('.password-toggle-btn');
    toggleButtons.forEach(function (button) {
        button.addEventListener('click', function (e) {
            e.preventDefault(); // Prevent accidental form submission
            const targetId = this.getAttribute('data-target');
            const targetInput = document.getElementById(targetId);
            if (!targetInput) return;

            const isPassword = targetInput.type === 'password';
            targetInput.type = isPassword ? 'text' : 'password';

            // Accessible labels
            const newLabel = isPassword ? 'Hide password' : 'Show password';
            this.setAttribute('aria-label', newLabel);
            this.setAttribute('title', newLabel);

            // Icon swap between eye and eye-slash
            const eyeIcon = this.querySelector('.icon-eye');
            const eyeSlashIcon = this.querySelector('.icon-eye-slash');
            if (eyeIcon && eyeSlashIcon) {
                if (isPassword) {
                    eyeIcon.classList.add('d-none');
                    eyeSlashIcon.classList.remove('d-none');
                } else {
                    eyeIcon.classList.remove('d-none');
                    eyeSlashIcon.classList.add('d-none');
                }
            }
        });
    });

    // Dark / Light Theme Toggle Management
    const themeToggleBtn = document.getElementById('themeToggleBtn');

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-bs-theme', theme);
        try {
            localStorage.setItem('theme', theme);
        } catch (e) {}

        if (themeToggleBtn) {
            const sunIcon = themeToggleBtn.querySelector('.theme-icon-sun');
            const moonIcon = themeToggleBtn.querySelector('.theme-icon-moon');
            const themeLabel = themeToggleBtn.querySelector('.theme-label');

            if (theme === 'dark') {
                if (sunIcon) sunIcon.classList.remove('d-none');
                if (moonIcon) moonIcon.classList.add('d-none');
                if (themeLabel) themeLabel.textContent = 'Light';
                themeToggleBtn.setAttribute('title', 'Switch to Light Theme');
                themeToggleBtn.setAttribute('aria-label', 'Switch to Light Theme');
            } else {
                if (sunIcon) sunIcon.classList.add('d-none');
                if (moonIcon) moonIcon.classList.remove('d-none');
                if (themeLabel) themeLabel.textContent = 'Dark';
                themeToggleBtn.setAttribute('title', 'Switch to Dark Theme');
                themeToggleBtn.setAttribute('aria-label', 'Switch to Dark Theme');
            }
        }

        window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: theme } }));
    }

    // Sync button state on page load
    const activeTheme = document.documentElement.getAttribute('data-bs-theme') || 'light';
    applyTheme(activeTheme);

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', function () {
            const current = document.documentElement.getAttribute('data-bs-theme') || 'light';
            const nextTheme = current === 'dark' ? 'light' : 'dark';
            applyTheme(nextTheme);
        });
    }
});
