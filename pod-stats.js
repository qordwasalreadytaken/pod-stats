/* pod-stats.js  */

var coll = document.getElementsByClassName("collapsible");
for (var i = 0; i < coll.length; i++) {
    coll[i].addEventListener("click", function() {
        this.classList.toggle("active");
        var content = this.nextElementSibling;
        var openIcon = this.querySelector("img.icon[alt='Open']");
        var closeIcon = this.querySelector("img.icon[alt='Close']");

        if (content.style.display === "block") {
            content.style.display = "none";
            openIcon.classList.remove("hidden");
            closeIcon.classList.add("hidden");
        } else {
            content.style.display = "block";
            openIcon.classList.add("hidden");
            closeIcon.classList.remove("hidden");
        }
    });
}


//Get the button
var backToTopBtn = document.getElementById("backToTopBtn");

// When the user scrolls down 20px from the top of the document, show the button
window.onscroll = function() {scrollFunction()};

function scrollFunction() {
if (document.body.scrollTop > 20 || document.documentElement.scrollTop > 20) {
backToTopBtn.style.display = "block";
} else {
backToTopBtn.style.display = "none";
}
}

// When the user clicks on the button, scroll to the top of the document
function topFunction() {
document.body.scrollTop = 0; // For Safari
document.documentElement.scrollTop = 0; // For Chrome, Firefox, IE and Opera
}

document.addEventListener("DOMContentLoaded", function () {
const scHcButton = document.getElementById("SC_HC");
const currentUrl = window.location.href;
const filename = currentUrl.split("/").pop(); // Get the last part of the URL

// Check if the current page is Hardcore or Softcore
const isHardcore = filename.startsWith("hc");

// Update button appearance based on current mode
if (isHardcore) {
scHcButton.classList.add("hardcore");
scHcButton.classList.remove("softcore");
} else {
scHcButton.classList.add("softcore");
scHcButton.classList.remove("hardcore");
}

// Update background image based on mode
updateButtonImage(isHardcore);

// Add click event to toggle between SC and HC pages
scHcButton.addEventListener("click", function () {
let newUrl;

if (isHardcore) {
// Convert HC -> SC (remove "hc" from filename)
newUrl = currentUrl.replace(/hc(\w+\.html)$/, "$1");
} else {
// Convert SC -> HC (prepend "hc" to the filename)
newUrl = currentUrl.replace(/(\w+\.html)$/, "hc$1");
}

// Redirect to the new page
if (newUrl !== currentUrl) {
window.location.href = newUrl;
}
});

// Function to update button background image
function updateButtonImage(isHardcore) {
if (isHardcore) {
scHcButton.style.backgroundImage = "url('../icons/Hardcore_click.png')";
} else {
scHcButton.style.backgroundImage = "url('../icons/Softcore_click.png')";
}
}
});

document.addEventListener("DOMContentLoaded", function () {
const currentPage = window.location.pathname.split("/").pop(); // Get current page filename
const menuItems = document.querySelectorAll(".top-button");

menuItems.forEach(item => {
const itemPage = item.getAttribute("href");
if (itemPage && currentPage === itemPage) {
item.classList.add("active");
}
});
});

document.addEventListener("DOMContentLoaded", function () {
let activePopup = null;

document.querySelectorAll(".hover-trigger").forEach(trigger => {
trigger.addEventListener("click", function (event) {
event.stopPropagation();
const characterName = this.getAttribute("data-character-name");

// Close any open popup first
if (activePopup) {
activePopup.classList.remove("active");
activePopup.innerHTML = ""; // Remove iframe for memory efficiency
activePopup = null;
}

// Find the associated popup container
const popup = this.closest(".character-info").nextElementSibling.querySelector(".popup");

// If this popup was already active, just close it
if (popup === activePopup) {
return;
}

// Create an iframe and set its src
const iframe = document.createElement("iframe");
iframe.src = `./armory/video_component.html?charName=${encodeURIComponent(characterName)}`;
iframe.setAttribute("id", "popupFrame");

// Add iframe to the popup
popup.appendChild(iframe);
popup.classList.add("active");

// Set this popup as the active one
activePopup = popup;
});
});

// Close the popup when clicking anywhere outside
document.addEventListener("click", function (event) {
if (activePopup && !activePopup.contains(event.target)) {
activePopup.classList.remove("active");
activePopup.innerHTML = ""; // Remove iframe to free memory
activePopup = null;
}
});
});
