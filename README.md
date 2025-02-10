# [Qords Info/Stats/Analytics for Path of Diablo](https://qordwasalreadytaken.github.io/pod-stats/Home.html)
Data analysis for the current PoD season

The Path of Diablo analytics site seems to have been orphaned, at least temporarily, leaving a gap in available data and trends on PoD builds. This is my attempt to provide similar information, and, although it's done in a different manner, the hope is that it helps users come to the same conclusions through statistics and data analysis.

The goal of this is not to replace the analytics site, but fill a hole until it (hopefully) comes back. 

The data used to create these is not real time, it's a snapshot in time that is refreshed on a regular basis.

# Feedback?
Let Qord know, Qord @ PoD Discord 

# Known Issues to address
* Pie Charts not displayed properly, covered by labels
* Hardcore had a low player base so the HC data includes a lot of low level characters, skewing data. Should it be floored at lvl 60? Some other level?
    * Hardcore floor changed to level 60, should it be higher still?
* The number of clusters (builds) to use was decided by cluster analysis, silhouette, and gap analysis, followed by just eyeballing them to see if the made sense. Can this be more automatic AND reliable?
* Reused names can cause duplicate character info to fall into multiple class buckets, fixing this has been manual; need to automate that so Zon's don't show up in sorc build breakdowns. 

# Credits
Armory quickview pop ups powered by PoD Gear Twitch extension by Vinthian, Sizzles & Qord, adapted for use here by Qord

