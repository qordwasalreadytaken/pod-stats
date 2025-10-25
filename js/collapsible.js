// Collapsible functionality for buttons
document.addEventListener("DOMContentLoaded", function() {
    // Get all collapsible buttons
    const collapsibleButtons = document.querySelectorAll(".collapsible");
    
    collapsibleButtons.forEach(function(button) {
        button.addEventListener("click", function() {
            // Toggle the active class
            this.classList.toggle("active");
            
            // Get the content div (next sibling)
            const content = this.nextElementSibling;
            
            if (content && content.classList.contains("content")) {
                // Toggle display
                if (content.style.display === "none" || content.style.display === "") {
                    content.style.display = "block";
                    
                    // Toggle icon images
                    const openIcon = this.querySelector(".open-icon");
                    const closeIcon = this.querySelector(".close-icon");
                    
                    if (openIcon && closeIcon) {
                        openIcon.classList.remove("hidden");
                        closeIcon.classList.add("hidden");
                    }
                } else {
                    content.style.display = "none";
                    
                    // Toggle icon images
                    const openIcon = this.querySelector(".open-icon");
                    const closeIcon = this.querySelector(".close-icon");
                    
                    if (openIcon && closeIcon) {
                        openIcon.classList.add("hidden");
                        closeIcon.classList.remove("hidden");
                    }
                }
            }
        });
    });
});