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

## Updates and history

The demo's [site data workflow](.github/workflows/site-data.yml) runs twice daily
using Python 3.12. It collects both leagues and their derived datasets in a
temporary directory and publishes them only after collection succeeds and the
season status is checked again. The workflow also runs the pipeline tests.
When the API is unavailable or returns invalid data, the run fails rather than
replacing the last good snapshot.

On or after the 28th of each month, the first successful run creates an
immutable archive under `Season/<season>/snapshots/YYYY-MM/`. If that window
was missed and the last successful snapshot is from the preceding month, the
next run archives that snapshot with its actual capture date. The top navigation
history dropdown and history page use a generated manifest and also link to the
existing legacy archives. The dropdown supports hover, keyboard and touch.
New snapshots include their own pages, data and local assets. External services
and libraries may still be needed, and links to the PoD armory can show current
data rather than historical data.

When a previously observed active season ends or a new season starts, the
pipeline saves the last successful active snapshot as `Final`, unless a Final
archive already exists. It cannot reconstruct an end-of-ladder snapshot from
post-season data: an already-ended season must have an existing Final archive
or a recorded active snapshot. GitHub schedules can be delayed or disabled, so
failed Actions runs should be monitored.

The demo's [site configuration](site_config.json) enables post-season updates
and monthly snapshots. For a separately configured production deployment, set
`post_season_updates` to `false` to preserve the final live snapshot until the
next season. This repository does not change or deploy production. The
`archive_day` value can be 1–28. Snapshot files are sizeable and will increase
repository and Pages storage over time. The separate ranking workflow also
respects the post-season freeze setting.

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
