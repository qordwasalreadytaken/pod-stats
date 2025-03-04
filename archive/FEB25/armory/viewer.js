//let token = '';
//let tuid = '';

$(document).ready(function() {
    console.log("(document).ready worked");

    // Extract character name from URL if available
    function getQueryParam(param) {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get(param);
    }

    let characterName = getQueryParam("charName");

    if (characterName) {
        console.log("Character Name from URL:", characterName);
        
        // Fetch character data and process it
        try {
            fetchCharacterData(characterName);
        } catch (error) {
            console.error("Error during API calls:", error);
        }
    } else {
        console.warn("Character Name is not set in the URL.");
        document.getElementById("alertBanner").style.display = "block";
    }

    // Scroll event listeners
    $(window).scroll(function() {
        const scroll = $(window).scrollTop();
        $('.arrow').toggleClass('fade', scroll >= 1);
    });

    $('#main').scroll(function() {
        const scroll = $('#main').scrollTop();
        $('.arrow').toggleClass('fade', scroll >= 1);
    });
});

document.addEventListener("DOMContentLoaded", function() {
    initializeCharacterSections();
});

function initializeCharacterSections() {
    const characterSections = document.querySelectorAll(".character-section");

    characterSections.forEach(section => {
        const characterName = section.getAttribute("data-character-name");
        console.log("Initializing character:", characterName);

        if (characterName) {
            fetchCharacterData(characterName);
        } else {
            console.warn("Character Name is not set in the configuration for a section.");
            section.querySelector("#alertBanner").style.display = "block";
        }
    });
}

async function fetchCharacterData(characterName) {
    const url = `https://beta.pathofdiablo.com/api/characters/${encodeURIComponent(characterName)}/summary`;

    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`API call failed with status: ${response.status}`);
        }
        const data = await response.json();
        processCharacterData(data);
    } catch (error) {
        console.error("Error fetching character data:", error);
    }
}


// Function to process characterData after it's fetched
async function processCharacterData(characterData) {
  if (!characterData || typeof characterData !== 'object') {
      console.error("Invalid characterData:", characterData);
      return;
  }
  console.log("Character Data fetched:", characterData);
  updatePODComponent(characterData);  // Process and update UI after retrieval
}
   
function updatePODComponent(data) {
  if (data && data.Stats) {
  // Character information
  $("#title").text(data["Title"]);
  $("#name").text(data["Name"]);
  
  if(data["IsHardcore"] === true) {
    $("#mode").text("Hardcore");
    } else {
      $("#mode").text("Softcore");
    }
  
  $("#expansion").text("Expansion");
  
  if(data["IsLadder"] === true) {
    $("#ladder").text("Ladder");
  } else {
    $("#ladder").text("");
  }
  
  if(data["IsDead"] === true && data["IsHardcore"] === true) {
    $("#dead").text("(Dead)");
  } else {
    $("#dead").text("");
  }
  
  $("#level").text("Level " + data["Stats"]["Level"]);
  $("#class").text(data["Class"]);
  
  // Items
  var wornItems = findWornItems(data["Equipped"]);
  /*
  if ("weapon1" in wornItems) {
    // Only append the image without the tooltip
    $("#hover-container-weapon1").append(createImageHTML(wornItems["weapon1"], "hover-container"));
}

if ("helmet" in wornItems) {
    // Only append the image without the tooltip
    $("#hover-container-helmet").append(createImageHTML(wornItems["helmet"], "hover-container"));
}

if ("amulet" in wornItems) {
    // Only append the image without the tooltip
    $("#hover-container-amulet").append(createImageHTML(wornItems["amulet"], "hover-container"));
}

if ("ring1" in wornItems) {
    // Only append the image without the tooltip
    $("#hover-container-ring1").append(createImageHTML(wornItems["ring1"], "hover-container"));
}

if ("ring2" in wornItems) {
    // Only append the image without the tooltip
    $("#hover-container-ring2").append(createImageHTML(wornItems["ring2"], "hover-container"));
}

if ("body" in wornItems) {
    // Only append the image without the tooltip
    $("#hover-container-body").append(createImageHTML(wornItems["body"], "hover-container"));
}

if ("belt" in wornItems) {
    // Only append the image without the tooltip
    $("#hover-container-belt").append(createImageHTML(wornItems["belt"], "hover-container"));
}

if ("gloves" in wornItems) {
    // Only append the image without the tooltip
    $("#hover-container-gloves").append(createImageHTML(wornItems["gloves"], "hover-container"));
}

if ("boots" in wornItems) {
    // Only append the image without the tooltip
    $("#hover-container-boots").append(createImageHTML(wornItems["boots"], "hover-container"));
}

if ("weapon2" in wornItems) {
    // Only append the image without the tooltip
    $("#hover-container-weapon2").append(createImageHTML(wornItems["weapon2"], "hover-container"));
}
*/
  if ("weapon1" in wornItems) $("#hover-container-weapon1").append(createImageHTML(wornItems["weapon1"], "hover-container-weapon1"));
  if ("helmet" in wornItems) $("#hover-container-helmet").append(createImageHTML(wornItems["helmet"], "hover-container-helmet"));
  if ("amulet" in wornItems) $("#hover-container-amulet").append(createImageHTML(wornItems["amulet"], "hover-container-amulet"));
  if ("ring1" in wornItems) $("#hover-container-ring1").append(createImageHTML(wornItems["ring1"], "hover-container-ring1"));
  if ("ring2" in wornItems) $("#hover-container-ring2").append(createImageHTML(wornItems["ring2"], "hover-container-ring2"));
  if ("body" in wornItems) $("#hover-container-body").append(createImageHTML(wornItems["body"], "hover-container-body"));
  if ("belt" in wornItems) $("#hover-container-belt").append(createImageHTML(wornItems["belt"], "hover-container-belt"));
  if ("gloves" in wornItems) $("#hover-container-gloves").append(createImageHTML(wornItems["gloves"], "hover-container-gloves"));
  if ("boots" in wornItems) $("#hover-container-boots").append(createImageHTML(wornItems["boots"], "hover-container-boots"));
  if ("weapon2" in wornItems) $("#hover-container-weapon2").append(createImageHTML(wornItems["weapon2"], "hover-container-weapon2"));
  
  // Merc Items
  var mercWornItems = findWornItems(data["MercenaryEquipped"]);
  
  if ("weapon1" in mercWornItems) $("#merc-hover-container-weapon1").append(createImageHTML(mercWornItems["weapon1"], "merc-hover-container-weapon1"));
  if ("helmet" in mercWornItems) $("#merc-hover-container-helmet").append(createImageHTML(mercWornItems["helmet"], "merc-hover-container-helmet"));
  if ("body" in mercWornItems) $("#merc-hover-container-body").append(createImageHTML(mercWornItems["body"], "merc-hover-container-body"));
  if ("weapon2" in mercWornItems) $("#merc-hover-container-weapon2").append(createImageHTML(mercWornItems["weapon2"], "merc-hover-container-weapon2"));
  
  // Life, Stats
  $("#life").text(data["Stats"]["Life"]);
  $("#mana").text(data["Stats"]["Mana"]);
  if(data["Bonus"]["Strength"] > 0) {
    $("#strength").addClass("has-bonus");
    $("#strength").text(data["Stats"]["Strength"] + data["Bonus"]["Strength"]);
  } else {
    $("#strength").text(data["Stats"]["Strength"]);
  }
  $("#dexterity").text(data["Stats"]["Dexterity"]);
  $("#vitality").text(data["Stats"]["Vitality"]);
  $("#energy").text(data["Stats"]["Energy"]);
  $("#fire").text(data["Bonus"]["FireResistance"] + "%");
  $("#cold").text(data["Bonus"]["ColdResistance"] + "%");
  $("#lightning").text(data["Bonus"]["LightningResistance"] + "%");
  $("#poison").text(data["Bonus"]["PoisonResistance"] + "%");
  
    // Skills
    // Clear the skills container
    $("#skills").empty();

    // Loop through and add categories and skills
    data["SkillTabs"].forEach(category => {
        if (category["Total"] > 0) {
            $("#skills").append("<div id='skill-" + category["Name"].replace(/\s+/g, '-').toLowerCase() + "'><div class='skill-category'>" + category["Name"] + "</div></div>");
        
            category["Skills"].forEach(skill => {
                $("#skill-" + category["Name"].replace(/\s+/g, '-').toLowerCase())
                    .append("<div class='skill-icon' id='skill-" + skill["Name"].replace(/\s+/g, '-').toLowerCase() + "'><div class='skill-tooltip' id='tooltip-" + skill["Name"].replace(/\s+/g, '-').toLowerCase() + "'>" + skill["Name"] + "</div><img src='https://pathofdiablo.com/p/armory/img/skills/" + data["Class"].toLowerCase() + "/" + skill["Name"].replace(/\s+/g, '_').toLowerCase() + ".png' /><div class='skill-level'>" + skill["Level"] + "</div></div>")
                    .ready(function() {
                        $("#skill-" + skill["Name"].replace(/\s+/g, '-').toLowerCase()).hover(function() {
                            $("#tooltip-" + skill["Name"].replace(/\s+/g, '-').toLowerCase()).fadeIn(0);
                        }, function() {
                            $("#tooltip-" + skill["Name"].replace(/\s+/g, '-').toLowerCase()).fadeOut(0);
                            });
                        });
                });
        }
    });

    // Merc
    // check if no merc, hide
    if(data["MercenaryName"].length == 0) {
      $("#merc").hide();
    } else {
      $("#merc-name").text(data["MercenaryName"]);
      $("#merc-level").text(data["MercenaryLevel"]);
      $("#merc-type").text(data["MercenaryType"]);
    }
  }
  else {
    console.error("Data or Stats is undefined in updatePODComponent.");
    }
}    

function findWornItems(equippedItems) {
    var result = {};
    equippedItems.forEach((item) => {
      if(item["Worn"] !== "") {
        result[item["Worn"]] = item;
      }
    })
    return result;
}
  
function createItemHTML(itemObject) {
    let itemStr = "";

    // Title with special handling for "Delerium"
    if (itemObject["Title"] === "2693") {
        itemStr += `<div class='item-title title-${itemObject["QualityCode"]}'>Delerium</div>`;
    } else {
        itemStr += `<div class='item-title title-${itemObject["QualityCode"]}'>${itemObject["Title"]}</div>`;
    }

    // Quality tag
    if (itemObject["QualityCode"] !== "q_normal") {
        itemStr += `<div class='item-tag tag-${itemObject["QualityCode"]}'>${itemObject["Tag"]}</div>`;
    }

    // Rune tag, if applicable
    if ("RuneTag" in itemObject && itemObject["QualityCode"] === "q_runeword") {
        itemStr += `<div class='item-runetag title-q_runeword'>${itemObject["RuneTag"]}</div>`;
    }

    // Defense, block, and durability stats
    if ("Defense" in itemObject) {
        itemStr += `<div class='item-defense'>Defense: ${itemObject["Defense"]}</div>`;
    }
    if ("Block" in itemObject) {
        itemStr += `<div class='item-block'>Chance to Block: ${itemObject["Block"]}</div>`;
    }
    if ("Durability" in itemObject) {
        itemStr += `<div class='item-durability'>Durability: ${itemObject["Durability"]}/${itemObject["DurabilityMaximum"]}</div>`;
    }

    // Item level
    itemStr += `<div class='item-level'>Item Level: ${itemObject["ItemLevel"]}</div>`;

    // Property list (handling "Corrupted" specifically)
    itemObject["PropertyList"].forEach(property => {
        if (/corrupted/i.test(property)) {
            itemStr += `<div class='item-corrupted'>Corrupted</div>`;
        } else {
            itemStr += `<div class='item-property'>${property}</div>`;
        }
    });
    console.log("Tooltip content for item:", itemStr);  // Check the final content
    return itemStr;
}
     
function createImageHTML(itemObject, hoverContainerId) {
    // Generate tooltip content
    const tooltipContent = createItemHTML(itemObject);
        
    // Determine tooltip styling based on content size
    const propertySize = itemObject["PropertyList"].length;
    const maxCharWidth = Math.max.apply(Math, itemObject["PropertyList"].map(x => x.length));
    const tooltipClass = propertySize > 10 || maxCharWidth > 40 ? "itemhover-box itemhover-box-small" : "itemhover-box";
        
    // Append the tooltip content directly to the specified container
    $("#" + hoverContainerId).append(`
        <div class="${tooltipClass}" id="${hoverContainerId}-${itemObject["Worn"]}-hover">
            ${tooltipContent}
        </div>
    `);
        
    // Generate and return the image HTML
    let imageHTML = "";
    console.log("Tooltip appended with content:", tooltipContent);  // Debugging check
    if (itemObject["TextTag"] == "ring") {
        imageHTML = `<img id="${hoverContainerId}-${itemObject["Worn"]}-img" src="https://pathofdiablo.com/p/armory/img/items/ring2.gif" width="80%" height="80%" />`;
    }
    else if (itemObject["TextTag"] == "amulet") {
        imageHTML = `<img id="${hoverContainerId}-${itemObject["Worn"]}-img" src="https://pathofdiablo.com/p/armory/img/items/amulet2.gif" width="80%" height="80%" />`;
    }
    else if (itemObject["TextTag"].startsWith("Synthesized ")) {
    // Remove "Synthesized " from the beginning of TextTag
        const baseTag = itemObject["TextTag"].replace("Synthesized ", "");
        // Construct the URL using the modified baseTag
        imageHTML = `<img id="${hoverContainerId}-${itemObject["Worn"]}-img' src='https://pathofdiablo.com/p/armory/img/items/" 
        + baseTag.toLowerCase().replace(/ /g, "_").replace(/'/g, "%27") + ".gif' width='55vw' height='auto' />`;
    }
    else if (itemObject["Worn"] === "weapon1" && itemObject["Quality"] === "Unique" && itemObject["Size"]["invheight"] < 5 && itemObject["Size"]["invwidth"] < 2) {
        imageHTML = `<img id="${hoverContainerId}-${itemObject["Worn"]}-img" src="https://pathofdiablo.com/p/armory/img/items/${itemObject["Title"].toLowerCase().replace(/ /g, "_").replace(/'/g, "%27")}.gif" width="55vw" height="auto" />`;
    } 
    else if (itemObject["Worn"] === "weapon1" && itemObject["Quality"] === "Set") {
        imageHTML = `<img id="${hoverContainerId}-${itemObject["Worn"]}-img" src="https://pathofdiablo.com/p/armory/img/items/${itemObject["Title"].toLowerCase().replace(/ /g, "_").replace(/'/g, "%27")}.gif" width="55vw" height="auto" />`;
    } 
    else if (itemObject["Worn"] === "weapon1" && itemObject["Size"]["invheight"] < 5 && itemObject["Size"]["invwidth"] < 2) {
        imageHTML = `<img id="${hoverContainerId}-${itemObject["Worn"]}-img" src="https://pathofdiablo.com/p/armory/img/items/${itemObject["Tag"].toLowerCase().replace(/ /g, "_").replace(/'/g, "%27")}.gif" width="55vw" height="auto" />`;
    } 
    else if (itemObject["Worn"] === "weapon2" && itemObject["Size"]["invheight"] < 5 && itemObject["Size"]["invwidth"] < 2) {
        imageHTML = `<img id="${hoverContainerId}-${itemObject["Worn"]}-img" src="https://pathofdiablo.com/p/armory/img/items/${itemObject["Tag"].toLowerCase().replace(/ /g, "_").replace(/'/g, "%27")}.gif" width="55vw" height="auto" />`;
    } 
    else if (itemObject["Tag"] === "Bone Wand") {
        imageHTML = `<img id="${hoverContainerId}-${itemObject["Worn"]}-img" src="https://pathofdiablo.com/p/armory/img/items/${itemObject["Tag"].toLowerCase().replace(/ /g, "_").replace(/'/g, "%27")}.gif" width="55vw" height="auto" />`;
    } 
    else if (["Fetish Trophy", "Succubus Skull", "Bloodlord Skull"].includes(itemObject["Tag"])) {
        imageHTML = `<img id="${hoverContainerId}-${itemObject["Worn"]}-img" src="https://pathofdiablo.com/p/armory/img/items/homunculus.gif" width="90vw" height="auto" />`;
    } 
    else if (itemObject["Tag"] === "Blade Talons") {
        imageHTML = `<img id="${hoverContainerId}-${itemObject["Worn"]}-img" src="https://pathofdiablo.com/p/armory/img/items/${itemObject["Tag"].toLowerCase().replace(/ /g, "_").replace(/'/g, "%27")}.gif" width="55vw" height="auto" />`;
    } 
    else if (itemObject["Quality"] === "Magic") {
        imageHTML = `<img id="${hoverContainerId}-${itemObject["Worn"]}-img" src="https://pathofdiablo.com/p/armory/img/items/${itemObject["Tag"].toLowerCase().replace(/ /g, "_").replace(/'/g, "%27")}.gif" width="100vw" height="auto" />`;
    } 
    else if (itemObject["Tag"] === "Shako") {
        imageHTML = `<img id="${hoverContainerId}-${itemObject["Worn"]}-img" src="https://pathofdiablo.com/p/armory/img/items/${itemObject["Title"].toLowerCase().replace(/ /g, "_").replace(/'/g, "%27")}.gif" width="55vw" height="auto" />`;
    } 
    else if (itemObject["Title"] === "Crown of Thieves") {
        imageHTML = `<img id="${hoverContainerId}-${itemObject["Worn"]}-img" src="https://pathofdiablo.com/p/armory/img/items/${itemObject["Title"].toLowerCase().replace(/ /g, "_").replace(/'/g, "%27")}.gif" width="65vw" height="auto" />`;
    } 
    else if (itemObject["Title"] === "Steelrend") {
        imageHTML = `<img id="${hoverContainerId}-${itemObject["Worn"]}-img" src="https://pathofdiablo.com/p/armory/img/items/war_gauntlets.gif" width="65vw" height="auto" />`;
    } 
    else if (itemObject["Quality"] === "Unique") {
        imageHTML = `<img id="${hoverContainerId}-${itemObject["Worn"]}-img" src="https://pathofdiablo.com/p/armory/img/items/${itemObject["Title"].toLowerCase().replace(/ /g, "_").replace(/'/g, "%27")}.gif" width="90vw" height="auto" />`;
    } 
    else if (itemObject["Quality"] === "Set") {
        imageHTML = `<img id="${hoverContainerId}-${itemObject["Worn"]}-img" src="https://pathofdiablo.com/p/armory/img/items/${itemObject["Title"].toLowerCase().replace(/ /g, "_").replace(/'/g, "%27")}.gif" width="90vw" height="auto" />`;
    } 
    else if (itemObject["Quality"] === "Rare") {
        imageHTML = `<img id="${hoverContainerId}-${itemObject["Worn"]}-img" src="https://pathofdiablo.com/p/armory/img/items/${itemObject["Tag"].toLowerCase().replace(/ /g, "_").replace(/'/g, "%27")}.gif" width="100vw" height="auto" />`;
    } 
    else if (itemObject["Quality"] === "Craft") {
        imageHTML = `<img id="${hoverContainerId}-${itemObject["Worn"]}-img" src="https://pathofdiablo.com/p/armory/img/items/${itemObject["Tag"].toLowerCase().replace(/ /g, "_").replace(/'/g, "%27")}.gif" width="100vw" height="auto" />`;
    } 
    else if (itemObject["QualityCode"] === "q_runeword") {
        imageHTML = `<img id="${hoverContainerId}-${itemObject["Worn"]}-img" src="https://pathofdiablo.com/p/armory/img/items/${itemObject["TextTag"].toLowerCase().replace(/ /g, "_").replace(/'/g, "%27")}.gif" width="100vw" height="auto" />`;
    } 
    else if (itemObject["Worn"] === "helmet") {
        imageHTML = `<img id="${hoverContainerId}-${itemObject["Worn"]}-img" src="https://pathofdiablo.com/p/armory/img/items/${itemObject["Title"].toLowerCase().replace(/ /g, "_").replace(/'/g, "%27")}.gif" width="85vw" max-width="90%" height="auto" />`;
    } 
    else if (itemObject["Worn"] === "weapon1") {
        imageHTML = `<img id="${hoverContainerId}-${itemObject["Worn"]}-img" src="https://pathofdiablo.com/p/armory/img/items/${itemObject["TextTag"].toLowerCase().replace(/ /g, "_").replace(/'/g, "%27")}.gif" width="70vw" height="auto" />`;
    } else {  
        imageHTML = `<img id="${hoverContainerId}-${itemObject["Worn"]}-img" src="https://pathofdiablo.com/p/armory/img/items/${itemObject["Title"].toLowerCase().replace(/ /g, "_").replace(/'/g, "%27")}.gif" width="90%" height="auto" />`;
    }
    console.log("Tooltip appended with content:", imageHTML);  // Debugging check

    return imageHTML;  
    //console.log("Tooltip appended with content:", imageHTML);  // Debugging check
} 
    //console.log("Image url2:", imageHTML);  // Debugging check



