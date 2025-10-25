// Navigation functionality
document.addEventListener("DOMContentLoaded", function() {
    // Hamburger menu toggle
    const hamburger = document.querySelector('.hamburger');
    if (hamburger) {
        hamburger.addEventListener('click', function() {
            console.log('Hamburger menu clicked');
            // Add hamburger menu functionality here if needed
        });
    }
    
    // Set active button functionality
    window.setActive = function(buttonName) {
        console.log('Setting active button:', buttonName);
        // Add set active functionality here if needed
    };
    
    // Toggle menu functionality
    window.toggleMenu = function() {
        console.log('Toggle menu called');
        // Add toggle menu functionality here if needed
    };
});