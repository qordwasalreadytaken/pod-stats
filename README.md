# [Qords Info/Stats/Analytics for Path of Diablo](https://qordwasalreadytaken.github.io/pod-stats/Home.html)
Data analysis for the current Path of Diablo season

# A year in
The trends site has been live for a full year now (Matrch 2026), and it's gone through a few major facelifts and functionality changes. Most recently, the home page has been condensed with items, mercs, and other clutter having been moved to their own dedicated pages to allow the main page to act more like a main page and less like a content page. This also includes the addition of skill, item, and character search pages, as well as visibility into raw counts over time of points invested in skills and items equipped by characters and mercs. 

The original goal of this was not to directly replace the analytics site, but fill a hole until it (hopefully) comes back while also providing some information not included in that site. I really just wanted to look at all the bow and melee sorcs, count Deleriums and Dangoons (my favorite items), and it turned into this.

The data used to create these is not real time, it's a snapshot in time that is refreshed on a regular basis.

# To-do
Is crafting interesting enough to get its own dedicated page? If yes, do that.
Consolidate existing scripts

# Feedback?
Let Qord know, Qord @ PoD Discord 

# Credits
Armory quickview pop ups are powered by the PoD Gear Twitch extension by Vinthian, Sizzles & Qord, adapted for use here by Qord.

Thanks to lots of help from Zardoz, GD, myang26, TheHornBlower, Sizzles, Aramex

# About the process
Preface: I am not a programmer, I'm just the guy who took the time to get something built. These pages are not real-time. Regular snapshots are taken of ladder characters PoD armory pages and saved to two flat json files (one for SC and one for HC), and a series of python scripts create these static pages based on that data. 

