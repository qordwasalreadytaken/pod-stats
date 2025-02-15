# [Qords Info/Stats/Analytics for Path of Diablo](https://qordwasalreadytaken.github.io/pod-stats/Home.html)
Data analysis for the current PoD season

The Path of Diablo analytics site seems to have been orphaned, at least temporarily, leaving a gap in available data and trends on PoD builds. This is my attempt to provide similar information, and, although it's done in a different manner, the hope is that it helps users come to the same conclusions.

The original goal of this was not to directly replace the analytics site, but fill a hole until it (hopefully) comes back while also providing some information not included in that site. I really just wanted to look at all the bow and melee sorcs, and it turned into this.

The data used to create these is not real time, it's a snapshot in time that is refreshed on a regular basis.

# Feedback?
Let Qord know, Qord @ PoD Discord 

# To-do from community
* Make Armory links open in new tab instead of same tab
    * Done for SC and HC
* Move HC/SC toggle up to below home
    * Done for SC and HC
* Better way to present the "More detailed breakdown:" sections
    * Maybe give skills weight so, for example, a freezing pulse cluster presents itslef as a freezing pulse cluster so users don't have to read between the lines to see it

# Known Issues to address
* Some item images in the pop up aren't displaying even though they work in the original twitch extension, looks like it's only the regex'd/text-replace ones? Can't be something I did, blame regex right? 
* Pie Charts not displayed properly, covered by labels
* Hardcore had a low player base so the HC data includes a lot of low level characters, skewing data. Should it be floored at lvl 60? Some other level?
    * Hardcore floor changed to level 60, should it be higher still?
* The number of clusters (builds) to use was decided by cluster analysis, silhouette, and gap analysis, followed by just eyeballing them to see if the made sense. Can this be more automatic AND reliable?
* Reused names can cause duplicate character info to fall into multiple class buckets, fixing this has been manual; need to automate that so Zon's don't show up in sorc build breakdowns. 
    * Fix in place for SC, need to add to HC
    * Need to automate purge
* HC characters that have died don't have equipment, how best to address?
    * Changed armory quickview button to reflect "dead" status
    * Is that adequate?

# Credits
Armory quickview pop ups powered by PoD Gear Twitch extension by Vinthian, Sizzles & Qord, adapted for use here by Qord

