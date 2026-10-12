# Attachment bundles by organisation, 2026-10-08

The comment is the unit; its attachments set the count it represents
([attachment-processing](../plans/attachment-processing.md), Definitions). This page lists the
bundles, the comments whose attachments hold a hundred or more submissions or signatures, with the
organisation that sent them, what the cover states, how many distinct persons the records name,
and how the records split into unique texts, form texts and bare signatures. The counting method
and the SQL are on [attachment-count-2026-10-07](attachment-count-2026-10-07.md); the record
extractor that produced the persons and the text split is described at the end.

## Headline

| | |
|---|---:|
| comments with attachments | 4,629 |
| of which bundles holding two or more submissions or signatures | 467 |
| of which bundles of a hundred or more | 107 |
| **count the 4,629 comments represent** | **732,796** |
| beyond the comments themselves | 728,167 |
| in the 107 bundles of a hundred or more | 722,017 |
| posted through 2026-10-06, beyond the comments (CWP's snapshot estimated 296,000) | 279,265 |
| posted on 2026-10-07, beyond the comments | 448,902 |

## By organisation

Bundles of a hundred or more, summed per organisation. "Not named" is a bundle whose cover and
file titles name no organisation; the quoted phrase is how the cover describes it.

| represented | organisation | bundles |
|---:|---|---:|
| 165,659 | Natural Resources Defense Council | 1 |
| 73,775 | National Audubon Society | 1 |
| 67,077 | Outdoor Alliance | 1 |
| 47,372 | The Wilderness Society | 1 |
| 40,115 | Earthjustice | 1 |
| 38,439 | Environment America | 2 |
| 31,766 | Greater Yellowstone Coalition | 7 |
| 30,330 | not named (30,362 names) | 1 |
| 24,930 | not named ("keep America's wildest forests wild" petition) | 1 |
| 24,132 | Center for Biological Diversity | 1 |
| 20,135 | Sierra Club | 1 |
| 20,043 | Environmental Action | 2 |
| 18,539 | National Wildlife Federation Action Fund | 1 |
| 16,185 | REI Co-op | 1 |
| 15,212 | Defenders of Wildlife | 1 |
| 15,039 | not named (15,264 advocates) | 1 |
| 12,518 | Alaska Wilderness League | 1 |
| 9,578 | WildEarth Guardians | 1 |
| 9,056 | not named ("comments from N people", ASP files) | 18 |
| 4,888 | National Wildlife Federation Outdoors | 1 |
| 3,397 | Student PIRGs | 1 |
| 3,295 | Cascadia Wildlands | 1 |
| 3,143 | SaveRoadlessForests.com | 16 |
| 2,503 | Friends of Animals | 1 |
| 2,273 | Earth Day Network | 1 |
| 2,099 | California Environmental Voters | 1 |
| 1,942 | West Virginia Rivers Coalition (14 organisations) | 1 |
| 1,859 | Oregon Wild | 1 |
| 1,613 | Appalachian Voices | 1 |
| 1,586 | other, not named | 6 |
| 1,278 | not named (Tongass signatures) | 1 |
| 1,134 | Winter Wildlands Alliance | 1 |
| 1,081 | Southeast Alaska Conservation Council | 1 |
| 1,008 | The Mountaineers | 1 |
| 927 | not named (927 individual comments) | 1 |
| 853 | International Mountain Bicycling Association | 1 |
| 654 | Prairie Rivers Network | 1 |
| 650 | Organized Village of Kake et al. | 1 |
| 635 | not named (numbered signers) | 1 |
| 591 | Washington Wild | 1 |
| 529 | Prairie Hills Audubon Society | 2 |
| 500 | not named (petition table) | 1 |
| 400 | Michigan League of Conservation Voters | 1 |
| 325 | Natural Resources Council of Maine | 1 |
| 320 | State of Alaska | 1 |
| 305 | not named (305 Washington elected officials, businesses and organisations, a joint letter) | 1 |
| 284 | Sky Island Alliance | 1 |
| 232 | not named (petition) | 1 |
| 204 | not named (faith leaders petition) | 1 |
| 192 | not named (192 Americans) | 1 |
| 178 | Virginia Wilderness Committee | 1 |
| 171 | DarkSky International | 1 |
| 154 | NJPIRG Students | 1 |
| 142 | Los Padres ForestWatch | 1 |
| 126 | not named (193 signers) | 1 |
| 118 | Backcountry Hunters & Anglers, Arizona Chapter | 1 |
| 116 | The Conservation Alliance | 1 |
| 105 | not named (inbound files) | 1 |
| 104 | not named | 1 |
| 103 | California Four Wheel Drive Association | 1 |
| 100 | Keep Her Wild | 1 |

Six small entries are one commenter's own documents (papers, appendices) that still trigger a
marker or two and are listed as doubtful; together they are 1,586.

Three large figures on the coalition's own spreadsheet are not in the attachments: Patagonia's
34,779, Sierra Club's 59,000 beyond its 21,724 bundle, and the orgs whose rows show only a portal
number. Those reached the agency some other way, or are not posted.

## Persons

The record extractor splits each bundle into records and reads a person key where the shape
carries one: an e-mail address (NRDC, Outdoor Alliance), or a name with a zip, a city and state,
or a state. Columnar dumps (Audubon, the 30,362-name list, Environment America's and the Center
for Biological Diversity's signature tables) list names, cities and zips in separate blocks that
cannot be re-joined, so their records have no key.

| | |
|---|---:|
| records split | 640,100 |
| records with a person key | 394,537 |
| distinct persons among them | 327,054 |
| keys repeated within or across bundles | 39,740 |
| persons present in more than one comment's bundle | 13,276 |
| records with no key (columnar dumps, unparsed lists) | 245,563 |

So one person in six who is named signed more than once. The most repeated keys are single
e-mail addresses signed 50 to 200 times in the NRDC and Outdoor Alliance exports.

## Unique against form

Where a record carries a text, the text is normalised (export ids, codes and numbers removed) and
hashed; a text seen once across every bundle is unique, a text seen two or more times is a form.
A bare signature carries no text.

| | |
|---|---:|
| records with a text | 118,814 |
| distinct texts | 42,843 |
| unique, text seen once | 42,297 |
| form, text seen two or more times | 76,517 |
| bare signatures, no text | 521,286 |

The largest form texts: 38,931 copies in one bundle (The Wilderness Society's template), 14,459
in one (Defenders of Wildlife), 7,728 across 18 bundles (Greater Yellowstone Coalition's action
letter), 984 across 62 bundles (the Conservation Alliance's letter). The covers that state their
own split agree with the extractor: Outdoor Alliance says 14,744 unique and 52,449 signatures,
the extractor finds 12,764 unique texts and 53,497 signatures; The Wilderness Society says 5,090
custom and 42,455 template, the extractor finds 1,190 unique and 40,107 form, the custom letters
sharing more text than their name suggests; Sierra Club says 10,403 personal messages, the
extractor finds 8,589 unique texts.

This is the split within the attachments. The records' texts have not yet been run through the
comment corpus's own families, so a form text here is not yet linked to the comment family that
carries the same letter in the docket.

## The bundles

| count | comment | posted | organisation | cover states | basis | persons keyed | unique texts | form | signature |
|---:|---|---|---|---:|---|---:|---:|---:|---:|
| 165,659 | 612671 | 10-07 | Natural Resources Defense Council | 165,473 | measured | 123,308 | 190 | 2 | 165,467 |
| 73,775 | 612355 | 10-07 | National Audubon Society | 74,726 | measured | 0 | 0 | 0 | 73,775 |
| 67,077 | 604812 | 10-07 | Outdoor Alliance | 67,193 | measured | 64,118 | 12,764 | 816 | 53,497 |
| 47,372 | 559598 | 10-05 | The Wilderness Society | 47,545 | measured | 40,386 | 1,190 | 40,107 | 5,084 |
| 40,115 | 611258 | 10-07 | Earthjustice | 40,115 | declared | 0 | 0 | 0 | 531 |
| 36,910 | 540553 | 10-04 | Environment America | 37,079 | measured | 0 | 0 | 0 | 36,910 |
| 30,330 | 601247 | 10-07 | not named (30,362 names) | 30,362 | measured |  |  |  |  |
| 24,930 | 461942 | 09-21 | not named ("keep America's wildest forests wild" petition) |  | measured | 20,583 | 0 | 0 | 23,032 |
| 24,132 | 609969 | 10-07 | Center for Biological Diversity |  | measured | 0 | 0 | 0 | 24,132 |
| 20,135 | 480496 | 09-24 | Sierra Club | 21,724 | measured | 18,595 | 8,589 | 109 | 11,439 |
| 18,539 | 597242 | 10-06 | National Wildlife Federation Action Fund |  | measured | 0 | 0 | 0 | 18,539 |
| 16,393 | 552328 | 10-04 | Greater Yellowstone Coalition |  | measured | 9,941 | 9,070 | 7,299 | 24 |
| 16,185 | 589094 | 10-06 | REI Co-op | 16,190 | measured | 0 | 0 | 0 | 16,185 |
| 15,717 | 540396 | 10-04 | Environmental Action | 15,794 | measured | 0 | 0 | 0 | 15,717 |
| 15,212 | 570121 | 10-05 | Defenders of Wildlife |  | measured | 14,217 | 743 | 14,469 | 0 |
| 15,039 | 596976 | 10-06 | not named (15,264 advocates) | 15,264 | measured | 14,865 | 0 | 0 | 14,902 |
| 12,518 | 603882 | 10-07 | Alaska Wilderness League | 13,791 | measured | 0 | 0 | 0 | 12,518 |
| 9,578 | 597449 | 10-06 | WildEarth Guardians | 9,611 | measured | 9,570 | 50 | 0 | 9,528 |
| 5,176 | 552236 | 10-04 | Greater Yellowstone Coalition |  | measured | 0 | 0 | 0 | 5,176 |
| 4,888 | 611082 | 10-07 | National Wildlife Federation Outdoors |  | measured | 0 | 0 | 0 | 4,888 |
| 4,326 | 605265 | 10-07 | Environmental Action |  | measured | 0 | 0 | 0 | 4,326 |
| 3,397 | 612510 | 10-07 | Student PIRGs |  | measured | 1,530 | 0 | 0 | 1,561 |
| 3,329 | 552239 | 10-04 | Greater Yellowstone Coalition |  | measured | 2,249 | 1,139 | 2,186 | 4 |
| 3,295 | 602029 | 10-07 | Cascadia Wildlands | 3,318 | measured | 495 | 10 | 0 | 485 |
| 2,837 | 552220 | 10-04 | Greater Yellowstone Coalition |  | measured | 0 | 0 | 0 | 2,837 |
| 2,503 | 595645 | 10-06 | Friends of Animals |  | measured | 0 | 0 | 0 | 1,822 |
| 2,273 | 612101 | 10-07 | Earth Day Network |  | measured | 0 | 0 | 0 | 2,273 |
| 2,124 | 600040 | 10-07 | Greater Yellowstone Coalition |  | measured | 8 | 8 | 0 | 2,116 |
| 2,099 | 572803 | 10-06 | California Environmental Voters | 2,177 | measured | 60 | 0 | 0 | 67 |
| 1,942 | 590218 | 10-06 | West Virginia Rivers Coalition (14 organisations) |  | measured | 0 | 0 | 0 | 1,942 |
| 1,859 | 505645 | 09-29 | Oregon Wild | 1,869 | measured | 0 | 1,694 | 164 | 1 |
| 1,613 | 597700 | 10-06 | Appalachian Voices | 1,700 | measured | 718 | 154 | 0 | 564 |
| 1,529 | 605216 | 10-07 | Environment America | 1,537 | measured | 0 | 0 | 0 | 1,529 |
| 1,278 | 603831 | 10-07 | not named (Tongass signatures) |  | measured | 1,260 | 0 | 0 | 1,278 |
| 1,134 | 612252 | 10-07 | Winter Wildlands Alliance |  | measured |  |  |  |  |
| 1,081 | 604325 | 10-07 | Southeast Alaska Conservation Council | 1,089 | measured | 725 | 0 | 0 | 1,081 |
| 1,018 | 596266 | 10-06 | Greater Yellowstone Coalition |  | measured | 0 | 0 | 0 | 1,018 |
| 1,008 | 596272 | 10-06 | The Mountaineers | 1,008 | declared | 1 | 10 | 0 | 0 |
| 927 | 596456 | 10-06 | not named (927 individual comments) | 927 | declared | 0 | 0 | 0 | 1,843 |
| 889 | 547879 | 10-04 | Greater Yellowstone Coalition |  | measured | 2 | 3 | 3 | 883 |
| 853 | 601816 | 10-07 | International Mountain Bicycling Association | 853 | measured |  |  |  |  |
| 702 | 480643 | 09-24 | not named ("comments from N people", ASP files) | 702 | measured | 661 | 61 | 600 | 0 |
| 700 | 601540 | 10-07 | SaveRoadlessForests.com | 700 | declared | 700 | 538 | 162 | 0 |
| 654 | 603444 | 10-07 | Prairie Rivers Network | 658 | measured | 0 | 0 | 0 | 654 |
| 650 | 602089 | 10-07 | Organized Village of Kake et al. |  | measured | 2 | 4 | 0 | 0 |
| 635 | 603043 | 10-07 | not named (numbered signers) | 636 | measured | 310 | 141 | 0 | 173 |
| 591 | 600068 | 10-07 | Washington Wild | 591 | declared |  |  |  |  |
| 550 | 480618 | 09-24 | not named ("comments from N people", ASP files) | 550 | measured | 512 | 53 | 459 | 0 |
| 549 | 593639 | 10-06 | not named ("comments from N people", ASP files) | 549 | measured | 520 | 42 | 479 | 0 |
| 545 | 480627 | 09-24 | not named ("comments from N people", ASP files) | 545 | measured | 518 | 38 | 481 | 0 |
| 537 | 480660 | 09-24 | not named ("comments from N people", ASP files) | 537 | measured | 501 | 53 | 448 | 0 |
| 533 | 462604 | 09-21 | not named ("comments from N people", ASP files) | 533 | measured | 498 | 39 | 459 | 0 |
| 530 | 462631 | 09-21 | not named ("comments from N people", ASP files) | 530 | measured | 502 | 36 | 466 | 0 |
| 529 | 433490 | 09-16 | not named ("comments from N people", ASP files) | 530 | measured | 495 | 45 | 450 | 0 |
| 527 | 433552 | 09-16 | not named ("comments from N people", ASP files) | 527 | measured | 489 | 47 | 442 | 0 |
| 525 | 462832 | 09-21 | not named ("comments from N people", ASP files) | 525 | measured | 495 | 35 | 460 | 0 |
| 519 | 480623 | 09-24 | not named ("comments from N people", ASP files) | 519 | measured | 493 | 40 | 453 | 0 |
| 514 | 480666 | 09-24 | not named ("comments from N people", ASP files) | 514 | measured | 491 | 33 | 458 | 0 |
| 504 | 513912 | 09-29 | not named ("comments from N people", ASP files) | 504 | measured | 481 | 44 | 437 | 0 |
| 502 | 513902 | 09-29 | not named ("comments from N people", ASP files) | 502 | measured | 480 | 35 | 446 | 0 |
| 500 | 403294 | 09-15 | not named (petition table) | 500 | declared | 390 | 0 | 0 | 390 |
| 461 | 480634 | 09-24 | not named ("comments from N people", ASP files) | 461 | measured | 432 | 37 | 395 | 0 |
| 451 | 593670 | 10-06 | not named ("comments from N people", ASP files) | 451 | measured | 420 | 41 | 379 | 0 |
| 445 | 570242 | 10-06 | one commenter's own documents, count doubtful: _A Billion Dollar Investment in New Yorks; Fire Eco_ |  | measured |  |  |  |  |
| 400 | 597214 | 10-06 | Michigan League of Conservation Voters | 400 | declared | 301 | 0 | 0 | 301 |
| 338 | 604276 | 10-07 | one commenter's own documents, count doubtful: _Holshouser_Comment_FS-2025-0001; Holshouser_Defici_ |  | measured | 0 | 0 | 0 | 338 |
| 325 | 531905 | 10-01 | Natural Resources Council of Maine | 323 | measured |  |  |  |  |
| 322 | 608005 | 10-07 | Prairie Hills Audubon Society |  | measured | 0 | 0 | 0 | 322 |
| 320 | 602720 | 10-07 | State of Alaska |  | measured |  |  |  |  |
| 312 | 405596 | 09-15 | not named ("comments from N people", ASP files) | 312 | measured | 293 | 25 | 268 | 0 |
| 305 | 600247 | 10-07 | not named (305 Washington elected officials, businesses and organisations, a joint letter) | 305 | declared |  |  |  |  |
| 291 | 564910 | 10-05 | one commenter's own documents, count doubtful: _Appendix A_List of References; Appendix B_Syphard;_ |  | measured | 0 | 0 | 0 | 291 |
| 284 | 609885 | 10-07 | Sky Island Alliance | 286 | measured | 280 | 0 | 0 | 284 |
| 266 | 480638 | 09-24 | not named ("comments from N people", ASP files) | 266 | measured | 257 | 20 | 237 | 0 |
| 261 | 601814 | 10-07 | SaveRoadlessForests.com | 261 | declared | 261 | 175 | 86 | 0 |
| 257 | 577627 | 10-06 | one commenter's own documents, count doubtful: _CPP Central and West Slope Resp to Comme; Fire Bak_ |  | measured |  |  |  |  |
| 232 | 584909 | 10-06 | not named (petition) |  | measured | 0 | 0 | 0 | 232 |
| 207 | 607830 | 10-07 | Prairie Hills Audubon Society |  | measured | 0 | 0 | 0 | 207 |
| 204 | 595486 | 10-06 | not named (faith leaders petition) |  | measured | 0 | 0 | 0 | 204 |
| 194 | 601686 | 10-07 | SaveRoadlessForests.com | 194 | declared | 194 | 140 | 54 | 0 |
| 193 | 602186 | 10-07 | SaveRoadlessForests.com | 95 | measured | 95 | 79 | 16 | 0 |
| 192 | 607977 | 10-07 | not named (192 Americans) | 192 | declared |  |  |  |  |
| 188 | 602286 | 10-07 | SaveRoadlessForests.com | 95 | measured | 95 | 72 | 23 | 0 |
| 187 | 603889 | 10-07 | SaveRoadlessForests.com | 94 | measured | 94 | 63 | 31 | 0 |
| 186 | 604879 | 10-07 | SaveRoadlessForests.com | 186 | declared | 186 | 136 | 50 | 0 |
| 178 | 603109 | 10-07 | Virginia Wilderness Committee | 178 | measured | 174 | 0 | 0 | 178 |
| 173 | 604941 | 10-07 | SaveRoadlessForests.com | 173 | declared | 173 | 142 | 31 | 0 |
| 172 | 602706 | 10-07 | SaveRoadlessForests.com | 86 | measured | 85 | 43 | 43 | 0 |
| 171 | 552974 | 10-05 | DarkSky International |  | measured | 0 | 0 | 0 | 171 |
| 154 | 606392 | 10-07 | NJPIRG Students | 154 | measured | 0 | 0 | 154 | 0 |
| 150 | 610122 | 10-07 | one commenter's own documents, count doubtful: _Barthelmess The influence of body-size a; Carlson _ |  | measured | 1 | 1 | 0 | 0 |
| 150 | 603641 | 10-07 | SaveRoadlessForests.com | 74 | measured | 74 | 49 | 25 | 0 |
| 142 | 611481 | 10-07 | Los Padres ForestWatch | 142 | measured | 142 | 142 | 0 | 0 |
| 137 | 601967 | 10-07 | SaveRoadlessForests.com | 137 | declared | 137 | 101 | 36 | 0 |
| 135 | 602822 | 10-07 | SaveRoadlessForests.com | 66 | measured | 66 | 47 | 19 | 0 |
| 133 | 604016 | 10-07 | SaveRoadlessForests.com | 67 | measured | 67 | 43 | 24 | 0 |
| 126 | 605302 | 10-07 | not named (193 signers) |  | measured | 0 | 0 | 0 | 126 |
| 125 | 604814 | 10-07 | SaveRoadlessForests.com | 65 | measured | 65 | 52 | 13 | 0 |
| 118 | 546080 | 10-04 | Backcountry Hunters & Anglers, Arizona Chapter |  | measured | 0 | 0 | 0 | 118 |
| 116 | 595763 | 10-06 | The Conservation Alliance |  | measured |  |  |  |  |
| 109 | 602418 | 10-07 | SaveRoadlessForests.com | 54 | measured | 54 | 40 | 14 | 0 |
| 105 | 242581 | 08-21 | not named (inbound files) |  | measured | 0 | 0 | 0 | 105 |
| 105 | 457357 | 09-21 | one commenter's own documents, count doubtful: _2001 Roadless rule draft EIS; Oregon-Wild-Analysis_ |  | measured | 0 | 0 | 0 | 105 |
| 104 | 543159 | 10-04 | not named | 98 | measured |  |  |  |  |
| 103 | 609382 | 10-07 | California Four Wheel Drive Association |  | measured | 0 | 0 | 0 | 103 |
| 100 | 602543 | 10-07 | SaveRoadlessForests.com | 50 | measured | 50 | 33 | 17 | 0 |
| 100 | 604180 | 10-07 | Keep Her Wild | 100 | declared | 111 | 105 | 4 | 2 |

## Organisation by cover phrase

Added 2026-10-11. The table above names the bundles of a hundred or more by hand. A filer that
spread its submissions over many small bundles (SaveRoadlessForests.com over some 150 comment
numbers, The Conservation Alliance over 64, Earthjustice's supporter packets of twenty over a
hundred) is named on each of them by its cover: the loader
(`scripts/attachment_accounting.py`, `organisation_for`) takes the organisation roster's name
for the comment where the roster has one (`roadless.comment_organisation`, read from every
bundle's cover letter by `scripts/organisation_roster.py`; added later on 2026-10-11, so a
bundle carries one name wherever the site shows it), else the table's row where there is
one, else the first phrase below that the cover carries, case ignored. A bundle whose cover
names no organisation stays unnamed; "ASP" in a file title is not a name, and the eighteen
"comments from N people" packets wait on the action page that carries their letter.

| phrase | organisation |
|---|---|
| RoadlessForests.com | SaveRoadlessForests.com |
| The Conservation Alliance | The Conservation Alliance |
| Earthjustice supporters | Earthjustice |
| from Earthjustice | Earthjustice |
| New Mexico Wild is pleased to transmit | New Mexico Wild |
| Advocates for Snake Preservation | Advocates for Snake Preservation |

## Addendum 2026-10-11: the stated count, read wider

The comparison with the More Than Just Parks docket report
([mtjp-comparison-2026-10-11](mtjp-comparison-2026-10-11.md)) found two bundles this review
held as single comments, 606536 ("18,430 Bird Conservation Supporters respectfully ask") and
541173 ("comments from 5,336 Black church leaders"), and three shapes the stated-count rule of
2026-10-07 did not read. The rule moved from the SQL into Python (`declared_count`,
`head_count`, `stated_count`, `basis_for` in `scripts/attachment_accounting.py`, pinned by
`tests/test_attachment_accounting.py`) and now reads:

- a count at the start of the cover, and a count with up to two words before its noun
  ("18,430 Bird Conservation Supporters", "5,336 Black church leaders");
- not a bare year, not a number over 99,999, and not a number with "our" between its nearest
  lead and itself ("on behalf of our 500 active members and 2,600 regional supporters" is the
  organisation's membership; "on behalf of our members ... signed by over 400 individuals"
  states 400);
- on an explicit cover, one opening "Attached are", "Attached is", "Attached below are" or
  "Enclosed are", the stated number stands at any size when the markers read more than ten
  percent off it. SaveRoadlessForests.com's packets state 50 to 95 and the markers read every
  record twice; the earlier floor of a hundred let the doubled count stand on ten of them;
- where the cover states no count, the files' own first page may: "This document compiles
  1,353 individual comments" (New Mexico Wild's four packets, 4,598 together, measured 1 to 3
  by the markers because the letters inside carry no salutation). A file's statement is
  explicit.

Reloaded on DEV 2026-10-11 (the figures above are the 2026-10-08 result; the tables hold these):

| | 2026-10-08 | rules of 2026-10-11 |
|---|---:|---:|
| bundles | 467 | 492 |
| enclosed | 728,634 | 755,516 |
| on the stated number | 15 | 59 |
| bundles with an organisation | 71 | 393 |

What moved: 606536 to 18,430 and 541173 to 5,336; New Mexico Wild's four to 1,353, 1,340,
1,179 and 726; Student PIRGs from the markers' 3,397 to its stated 1,713; The Mountaineers from
1,008 to the 1,435 its cover states ("1,435 members of our community, including 1,008 petition
signers and 427 unique comments"); ten SaveRoadlessForests.com packets from twice to once their
stated number; 22 "comments from 20 people" packets and one of 19 from 1 to their stated
count; Environment Illinois's 91. Named by cover phrase: SaveRoadlessForests.com on 168
bundles (5,259), Earthjustice on 102 (42,126, the 40,115 bundle and 101 supporter packets of
twenty, 2,011), The Conservation Alliance on 66 (1,320), New Mexico Wild on 4. The 99 still
unnamed were the 64 "comments from N people" packets (9,947), the covers that name none,
and the doubtful ones.

## Addendum 2026-10-11, later: the roster names first, the doubtful six count as one

The organisation roster ([organisation-roster-2026-10-11](organisation-roster-2026-10-11.md),
`roadless.comment_organisation`) read every bundle's cover letter, and the loader now takes
its name for a bundle before this review's table and phrases, so a bundle carries one name
wherever the site shows it. Two hand names above were wrong and are corrected in the tables:
609382 is the California Four Wheel Drive Association, which its letter names in its first
sentence, not a Colorado one; and the "comments from N people" packets are not unnamed,
each cover closing "Melissa Amarello, Executive Director Advocates for Snake Preservation",
a signature block this review had passed over (the phrase is now in the table above). Three
rows that were descriptions rather than names are now written as "not named (…)", or as the
name the letter gives (546080, Backcountry Hunters & Anglers, Arizona Chapter). The six
bundles marked "one commenter's own documents, count doubtful" (1,586 together) count as
one: the review had kept their measured counts to match the published 728,634, and they
are papers and appendices that trip a marker or two, not submissions.

Reloaded on DEV later on 2026-10-11:

| | rules of 2026-10-11 | roster first, doubtful as one |
|---|---:|---:|
| bundles | 492 | 486 |
| enclosed | 755,516 | 753,930 |
| on the stated number | 59 | 59 |
| bundles with an organisation | 393 | 461 |
| represented | 759,653 | 758,073 |

## Addendum 2026-10-12: the file's own opening decides its kind

The kind of a file was decided from its title and from the comment's cover note, never
from the file. Three of those rules filed the commenter's own letter as supporting
material, and the roster, which reads own letters, never read it:

- the cover rule, which marks every file as supporting when the cover says "supporting
  documentation", "comment letter and associated documents", "in support of ... comments"
  or "refer to the ... letter". The Southern Environmental Law Center's 195-page comment
  (611313, signed by four of its attorneys and joined by 69 organisations) fell to it
  because its cover quotes the "refer to the 10/02/2026 letter" sentence of its 77 exhibit
  filings; so did the state Attorneys General's 72-page letter (604614), the Oregon Wild
  coalition's (600099), The Nature Conservancy's (485235) and the Blue Mountains
  Biodiversity Project's (602598);
- the title rule meant for citations ("Smith 2019"), which matches any title of a word
  and four digits: "IMBA 2026 Comments" (558274), "USDA 2026 Roadless Rule Proposal"
  (542625, the Aldo Leopold Foundation), "RIN 0596-AD66 Comment" (431011, 574009),
  "WER 9567.06b Signed Letter" (604447, Wyoming Game and Fish), "Resolution 2026-29"
  (402838, the Town of Mills River), and "IRA_NEPA" by name (540619, 2,740 pages);
- the doubtful-six rule, which sends all of a doubtful bundle's files to supporting
  material: the National Wildlife Federation et al. letter (610122), NRDC's 262-page
  technical comments (564910) and the 654-page Holshouser comment (604276) went with
  their exhibits.

The rule now reads each file's first 2,500 characters first. A file that opens as a letter
on this docket (a salutation, a subject or attention line, an addressee by honorific, the
docket number, a "Comments of ..." heading or a resolution; dated in the comment's year
if dated at all; not an appendix, email, index, reference list, article, Federal Register
page, draft EIS, regulatory agenda, press release or memo to all) is the comment's own
letter whatever its title or cover says, on a comment that counts as one and whose cover
does not describe it as one part of a filing of exhibits for a letter filed elsewhere. The
cover and title rules reach only the files that do not open as a letter, and such a file
with text, beside a letter, is the letter's supporting material.

Checked against DEV before it was written: 22 files on 21 comments rise to own letter,
the fifteen above with 456735, 459646, 464187, 595235 (Colorado Mountain Club), 600137,
609374 and the Holshouser deficiency statement; 175 files on 65 comments fall to
supporting material, SELC's twelve volumes of the 2001 FEIS maps (543587) among them,
with journal articles, forest plans, earlier-period letters attached again and The
Wilderness Society's eight attachments. The 21 letters enter the roster on its next run.

## How the persons and the split were produced

A Python pass over every attachment with text, excluding supporting material by cover and by
title, picks the record shape by the same tiers as the count and splits accordingly: form-export
headers; `Date Submitted` batches; `(zip code:` lists; one-record-per-file openings; letters at
each salutation, with the name read from the "Sincerely, Name City, ST" close; The Wilderness
Society's letters by their "Name City, ST zip date" close; e-mail lists, with the text before each
address as its body when it holds sentences; "Name, City, ST" closes; "Name - City, ST" lists;
signed-on petition tables; name-and-zip tables; numbered name lists; "Name from State:" packets.
Records: 640,100 of the 686,936 the count's markers measure, the rest being columnar dumps and
lists the extractor reads as counts only.
