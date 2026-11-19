fetch("archive_metadata.json")
    .then(response => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
    })
    .then(metadata => {
        const banner = document.createElement("div");
        banner.setAttribute("role", "status");
        banner.style.cssText = "position:relative;z-index:1100;padding:10px;text-align:center;background:#533d1f;color:white;font-weight:bold";
        const captured = new Date(metadata.captured_at).toLocaleString();
        const type = metadata.kind === "final" ? "Final ladder" :
            metadata.status === "post-season" ? "Post-season" : "Season";
        banner.textContent = `${type} ${metadata.season} snapshot — captured ${captured}. Armory links may show current data.`;
        document.body.prepend(banner);
    })
    .catch(error => console.error("Could not load archive metadata:", error));
