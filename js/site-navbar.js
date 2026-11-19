(() => {
    const script = document.currentScript;
    const siteRoot = new URL(script.dataset.siteRoot || "./", document.baseURI);
    const placeholder = document.getElementById("navbar-placeholder");
    const groups = [
        ["Final ladder", "final"],
        ["Post-season", "post-season"],
        ["During season", "active"],
        ["Older archives", "legacy"]
    ];

    function link(text, path) {
        const element = document.createElement("a");
        element.textContent = text;
        element.href = new URL(path, siteRoot).href;
        return element;
    }

    function hoverDetails(details) {
        let openedByHover = false;
        let closeTimer;
        const summary = details.querySelector("summary");
        details.addEventListener("mouseenter", () => {
            clearTimeout(closeTimer);
            if (window.matchMedia("(hover: hover)").matches && !details.open) {
                openedByHover = true;
                details.open = true;
            }
        });
        details.addEventListener("mouseleave", () => {
            closeTimer = setTimeout(() => {
                if (openedByHover && !details.contains(document.activeElement)) {
                    details.open = false;
                    openedByHover = false;
                }
            }, 250);
        });
        summary.addEventListener("click", event => {
            if (openedByHover && event.detail > 0) {
                event.preventDefault();
                openedByHover = false;
            }
        });
        details.addEventListener("toggle", () => {
            if (!details.open) {
                clearTimeout(closeTimer);
                openedByHover = false;
                details.querySelectorAll("details[open]").forEach(child => {
                    child.open = false;
                });
            }
        });
    }

    function renderHistory(target, archives) {
        target.replaceChildren();
        const seasons = [...new Set(archives.map(entry => entry.season))].sort((a, b) => b - a);
        if (!seasons.length) {
            target.textContent = "No archives available yet.";
            return;
        }
        for (const season of seasons) {
            const details = document.createElement("details");
            details.className = "history-season";
            const summary = document.createElement("summary");
            summary.textContent = `Season ${season}`;
            details.append(summary);
            const content = document.createElement("div");
            content.className = "history-season-content";
            for (const [label, kind] of groups) {
                const entries = archives.filter(entry => entry.season === season && entry.kind === kind)
                    .sort((a, b) => (b.month || "").localeCompare(a.month || "") || a.label.localeCompare(b.label));
                if (!entries.length) continue;
                const heading = document.createElement("div");
                heading.className = "history-group-label";
                heading.textContent = label;
                content.append(heading);
                for (const entry of entries) content.append(link(entry.label, entry.url));
            }
            details.append(content);
            hoverDetails(details);
            target.append(details);
        }
    }

    async function initialize() {
        if (!placeholder) throw new Error("Navbar placeholder is missing");
        const templateResponse = await fetch("templates/navbar.html");
        if (!templateResponse.ok) throw new Error(`Navbar request failed: HTTP ${templateResponse.status}`);
        placeholder.innerHTML = await templateResponse.text();
        const nav = placeholder.querySelector(".site-navbar");
        const toggle = nav.querySelector(".site-navbar-toggle");
        const links = nav.querySelector(".site-navbar-links");
        const menu = nav.querySelector(".history-menu");
        const seasons = nav.querySelector(".history-seasons");
        nav.querySelector(".history-current").href = new URL("home.html", siteRoot).href;
        nav.querySelector(".history-all").href = new URL("history.html", siteRoot).href;
        toggle.addEventListener("click", () => {
            const expanded = toggle.getAttribute("aria-expanded") !== "true";
            toggle.setAttribute("aria-expanded", String(expanded));
            links.classList.toggle("is-open", expanded);
        });
        hoverDetails(menu);
        document.addEventListener("click", event => {
            if (!nav.contains(event.target)) {
                menu.open = false;
                links.classList.remove("is-open");
                toggle.setAttribute("aria-expanded", "false");
            }
        });
        nav.addEventListener("keydown", event => {
            if (event.key !== "Escape") return;
            const current = event.target.closest("details[open]");
            if (current) {
                current.open = false;
                current.querySelector("summary").focus();
                event.preventDefault();
                event.stopPropagation();
            } else if (links.classList.contains("is-open")) {
                links.classList.remove("is-open");
                toggle.setAttribute("aria-expanded", "false");
                toggle.focus();
            }
        });
        try {
            const response = await fetch(new URL("data/history.json", siteRoot));
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            if (!Array.isArray(data.archives)) throw new Error("Invalid history manifest");
            renderHistory(seasons, data.archives);
        } catch (error) {
            console.error("Could not load history:", error);
            seasons.textContent = "History unavailable. Please try again later.";
        }
    }

    initialize().catch(error => {
        console.error("Could not load navigation:", error);
        if (placeholder) {
            placeholder.textContent = "Navigation unavailable. ";
            placeholder.append(link("View history", "history.html"));
        }
    });
})();
