# [Qord's Info/Stats/Analytics for Path of Diablo](https://qordwasalreadytaken.github.io/pod-stats/home.html)

Data analysis and statistics for the current **Path of Diablo** season.

## A year and a half in

The Trends site has now been live for about a year and a half, and it has gone through several major facelifts and functionality changes along the way.

The original goal was never to permanently replace the old analytics site. It was meant to fill the gap while that site was unavailable, while also providing some information that wasn't available there. I originally just wanted to look at things like all the bow and melee Sorceresses, count Deleriums and Dangoons (my favorite items), and generally poke around in the ladder data.

Well... that turned into this.

At this point, it looks like the site is here for the long term, so maintainability and futureproofing have become much more important. The most recent major change has been replacing many of the old static HTML pages with more dynamic pages and shifting more of the work from Python into JavaScript.

The goal is to make the site easier to maintain, expand, and hopefully keep around for a long time.

**Important:** The data presented here is **not real-time**. The site works from periodic snapshots of the Path of Diablo ladder and armory data.

## How it works

The site is entirely static and runs from GitHub Pages. There is no database or traditional backend.

The general process is:

1. Ladder and armory data is collected from Path of Diablo.
2. Periodic snapshots are saved as JSON.
3. Scripts process those snapshots into smaller, purpose-specific datasets.
4. The HTML/JavaScript pages load those datasets and turn them into the various reports, charts, and statistics on the site.

The site has gradually moved toward doing more processing in JavaScript rather than Python. This makes the generated pages more flexible and reduces the amount of Python code that needs to be maintained.

The data is intentionally snapshot-based rather than real-time, so numbers should be considered a representation of the ladder at the time the snapshot was taken.

## To-do

* Consolidate existing scripts
* Remove deprecated Python
* Documentation
* Continue cleaning up old/unused files and code

## Feedback?

Have an idea, found something broken, or just want to tell Qord that something is dumb?

Let Qord know: **Qord @ PoD Discord**

## Credits

Armory quickview pop-ups are powered by the **PoD Gear Twitch extension** by Vinthian, Sizzles & Qord, adapted for use here by Qord.

Thanks to everyone who has helped along the way:

**Zardoz, GD, myang26, TheHornBlower, Sizzles, Aramex**

And thanks to the Path of Diablo community for the data, feedback, testing, suggestions, bug reports, and general willingness to let me obsess over increasingly pointless Diablo 2 statistics.

What started as a temporary project to fill a gap in the PoD analytics ecosystem has grown considerably beyond its original scope, and has since been brought into the broader Path of Diablo fold.

## About the process

I am not a professional programmer. I'm just the guy who kept taking things apart, figuring out how they worked, and eventually getting something built.

The site is static and runs from GitHub Pages. There is no traditional backend or database.

Periodic snapshots of Path of Diablo ladder and armory data are collected and saved as JSON. A series of scripts then processes those snapshots into smaller, purpose-specific datasets. The HTML and JavaScript pages use those datasets to generate the various statistics, charts, reports, and other nonsense found throughout the site.

The project originally relied much more heavily on Python and pre-generated HTML. As the site grew, much of that work has gradually moved toward JavaScript and dynamic pages, making it easier to maintain and expand.

The data is **not real-time**. Everything displayed on the site represents the state of the available data when the relevant snapshot was collected, and historical data may be incomplete or affected by changes to the PoD armory/API.
