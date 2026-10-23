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
});
