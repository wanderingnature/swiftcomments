# Campaign organisations, 2026-10-11

Which organisation ran each campaign (text family). The operator's instruction of
2026-10-11: the organisations that delivered the attachment bundles are the campaign
sponsors; most ran both an online form that posted individual comments (the campaign) and
a signed form letter delivered as a bundle; name as many campaigns as possible, on every
basis, and leave a family NULL only where none holds.

`scripts/campaign_organisations.py` names a family on the first of these that holds:

1. a reviewed phrase (the table below): the family's exemplar carries a phrase read by hand
   from the organisation's action page (`action_page`, evidence the URL) or from the letter
   itself where it names the organisation (`letter`, evidence the quote);
2. `cover`: a named bundle's cover comment is a member of the family, and every named cover
   in the family is the same organisation;
3. `enclosed`: the organisation's bundles enclose at least five records whose sentences are
   the family's letter, and hold three quarters of all such records in named bundles.

The loaded result is `roadless.family_organisation`
([analysis-data-model](../reference/analysis-data-model.md), section 3.28).

## Reviewed phrases

Read by the loader, in this order; the first phrase found in a family's exemplar (markup
and entities removed, case ignored) names it. One organisation can have several rows: one
per letter it ran.

| organisation | basis | evidence | phrase |
|---|---|---|---|
| League of Conservation Voters | letter | As an environmentalist and member of the League of Conservation Voters, I am writing in strong opposition to the proposed repeal of the Roadless Rule | member of the League of Conservation Voters |
| National Audubon Society | letter | I stand with the National Audubon Society to urge the U.S. Forest Service | I stand with the National Audubon Society |
| The Conservation Alliance | letter | On behalf of The Conservation Alliance, we are submitting comments in favor of Alternative 1 | On behalf of The Conservation Alliance |
| Potomac Appalachian Trail Club | letter | Dozens of volunteers with the Potomac Appalachian Trail Club maintain 61 trails in two districts on the George Washington National Forest | volunteers with the Potomac Appalachian Trail Club |
| Earthjustice | letter | Attached are 20 unique comments from Earthjustice supporters | Earthjustice supporters |
| Natural Resources Defense Council | letter | Attachments to Technical Comments of NRDC et al. submitted by Earthjustice | Technical Comments of NRDC et al |
| Bears Belong | letter | Bears Belong. The Roadless Rule: How rescinding the Roadless Rule will negatively impact grizzlies. https://www.bearsbelong.com/roadless-rule | bearsbelong.com/roadless-rule |
| Southern Off-Road Bicycle Association | action_page | https://sorba.org/action-alert-defending-the-roadless-rule/ | member of the Southern Off-Road Bicycle Association |
| Earthjustice | action_page | https://earthjustice.org/action/protect-forests-from-massive-expansion-of-logging | The roadless areas in our national forests are an American treasure. For a quarter century |
| Earthjustice | action_page | https://earthjustice.org/?p=45378 | develop the last remaining undeveloped lands within our national forests |
| American Rivers | action_page | https://act.americanrivers.org/page/101689/action/1 | the largest loss of protections for rivers on federal lands in U.S. history |
| International Fund for Animal Welfare | action_page | https://action.ifaw.org/page/199462/action/1 | industrial logging and accompanying roadbuilding disrupted and destroyed 3.2 million acres |
| National Wildlife Federation | action_page | https://support.nwfactionfund.org/page/101819/action/1 | irreplaceable habitat for wildlife like elk and cold-water fish species |
| Runners for Public Lands | action_page | https://runnersforpubliclands.org/take-action/defend-the-roadless-rule/ | retain the 2001 Roadless Rule and select the No Action Alternative in the Draft Environmental Impact Statement |
| MountainTrue | action_page | https://mountaintrue.org/the-roadless-rule-comment-period-is-now-open/ | strong opposition to any efforts to rescind, weaken, or roll back the 2001 Roadless Area Conservation Rule |
| Western Watersheds Project | action_page | https://westernwatersheds.org/talking-points-roadless-rule/ | The Forest Service should strengthen the Roadless Rule, not eliminate it |
| Environmental Protection Information Center | action_page | https://www.wildcalifornia.org/post/action-alert-roadless-rule-rescission-posted-for-public-comment | The longer that forests are left alone and the longer that trees are left to grow |
| Wilderness Watch | action_page | https://wildernesswatch.salsalabs.org/strengthen-roadless-rule | It has helped protect roadless areas, and adjacent Wilderness areas, on national forests for 25 years |
| Wilderness Watch | action_page | https://wildernesswatch.salsalabs.org/strengthen-roadless-rule | Roads fragment wildlife habitat. Existing roadless areas provide habitat for many threatened and endangered native species |
| Outdoor Alliance | action_page | https://www.outdooralliance.org/blog/2026/8/18/administration-takes-final-steps-to-roll-back-roadless-rule-with-30-day-comment-period | extremely important to the outdoor recreation community and the outdoor recreation economy |
| CalWild | action_page | https://www.calwild.org/defendroadlessdefendrivers/ | The Roadless Rule protects the watersheds of many of our National Wild and Scenic Rivers in California |
| Trout Unlimited | action_page | https://www.tu.org/roadless-areas-defending-americas-sporting-lands/ | provide some of the best places to hunt and fish in America |
| Southern Utah Wilderness Alliance | action_page | https://suwa.quorum.us/campaign/169441/ | including approximately 4 million acres in Utah |
| Healthy Forests, Healthy Communities | action_page | https://www.votervoice.net/iframes/HFHC/Campaigns/129835/Respond | The rule unnecessarily restricts access and limits the ability of Forest Service professionals |

## How each was read, 2026-10-11

Read from the page or its form, the letter word for word:

- Earthjustice 2026: the EveryAction form behind the page (`act.earthjustice.org/v1/Forms/YWxXBoEhmECxbmVrmrTzzA2`) carries "I oppose the Trump administration's plans to rescind the Roadless Area Conservation Rule. The roadless areas in our national forests are an American treasure. For a quarter century, the Roadless Rule has protected them …". Earthjustice's bundle cover (611258) is a member of the same family (14621, 71,680).
- American Rivers: "In response to the U.S. Department of Agriculture's announcement that it is proposing a complete rollback of the 2001 Roadless Rule, I ask you to resist making this change … the largest loss of protections for rivers on federal lands in U.S. history".
- IFAW: "I urge the U.S. Forest Service to keep intact the existing Roadless Area Conservation Rule ("Roadless Rule"), which protects nearly 45 million acres … 3.2 million acres".
- National Wildlife Federation (the Action Fund's page): "Dear Secretary Rollins, I'm writing asking you not to repeal the 2001 Roadless Area Conservation Rule. For more than two decades, this important policy has safeguarded 58 million acres of irreplaceable habitat for wildlife like elk and cold-water fish species".
- SORBA: "As an active trail advocate, mountain biker, and member of the Southern Off-Road Bicycle Association (SORBA), I am writing to express my strong opposition …".
- Runners for Public Lands: "I am writing to urge the U.S. Forest Service to retain the 2001 Roadless Rule and select the No Action Alternative in the Draft Environmental Impact Statement and proposed rule."
- MountainTrue: "To the U.S. Forest Service: I am writing to express my strong opposition to any efforts to rescind, …".
- Western Watersheds Project: talking points, "The Forest Service should strengthen the Roadless Rule, not eliminate it."
- EPIC: "The longer that forests are left alone and the longer that trees are left to grow, the more time a fully-fledged, interconnected forest ecosystem has to develop."
- Wilderness Watch: talking points, "I oppose rescinding the Roadless Area Conservation Rule. It has helped protect roadless areas, and adjacent Wilderness areas, on national forests for 25 years. … Roads fragment wildlife habitat. Existing roadless areas provide habitat for many threatened and endangered native species."
- Outdoor Alliance: the EveryAction form behind the 2026 post (`secure.everyaction.com/v1/Forms/X7CnjgkSvUqOdcELAfhFKA2`): "… rescinding the Roadless Rule, which is extremely important to the outdoor recreation community and the outdoor recreation economy. The rescission would remove important protections for approximately 45 million acres …".

Not read from the page (the form is served by script and refused the read); the page is the
organisation's action for this letter, and the [More Than Just Parks docket
report](https://morethanjustparks.com/news/reports/roadless-docket) of 2026-10-08, which
captured 334 action pages from 91 groups and matched each page's text against every
campaign, traces the same letter to the same page:

- Earthjustice 2025: the earlier action for the notice of intent ("Tell the Trump administration to keep this landmark conservation rule in place"); the letter is the 2026 text with the 2025 figures ("the last remaining undeveloped lands within our national forests … over 50 million acres"). The form now serves the 2026 message.
- CalWild: "I oppose the proposed repeal of the Roadless Area Conservation Rule. I urge you to maintain the existing Rule as is. The Roadless Rule protects the watersheds of many of our National Wild and Scenic Rivers in California …" (the page invites adding rivers "to your public comment" through its form).
- Trout Unlimited: "The 2001 Roadless Area Conservation Rule conserves over 58 million acres of multiple-use public lands managed by the U.S. Forest Service that provide some of the best places to hunt and fish in America …" (the page's "Submit Your Comment" form).
- Southern Utah Wilderness Alliance: "Dear Secretary Rollins, I urge you not to rescind the 2001 Roadless Area Conservation Rule … including approximately 4 million acres in Utah …" (SUWA's Quorum action centre; its September 2025 Redrock Report says thousands commented through its online action portal).
- Healthy Forests, Healthy Communities: the one letter asking the agency to rescind ("I support the Forest Service's proposal to rescind the 2001 Roadless Area Conservation Rule. The rule unnecessarily restricts access …"); the VoterVoice campaign is closed.

The Bears Belong letter (the grizzly and hellbender letter, 21 families) names Bears Belong
only in its references, the one advocacy source among agency and journal citations; its
grizzly connectivity figures are that page's, and the page's "act now" is the campaign's
petition. The Sky Island Alliance letter (15474) is a supporter's own opening on the "Chief
Tom Schultz / choose Alternative 1" template of 15028 and is not attributed.

## Not found

Searched for and not attributed (no page carries the letter, or the page could not be
read; the docket report above traced none of them either): 14610 (33,601; "Like millions
of Americans who have spoken out since 2001 … 44.7 million acres"), 14657 (22,871;
"protect nearly 59 million acres … withdraw this rollback"), 14962 and the Tlingit-quote
variants (11,650; "more than 625,000 people … Please do not rescind the Roadless Area
Conservation Rule, Secretary Rollins"), 15028, 15037, 15038 ("Dear U.S. Forest Service
Chief Tom Schultz … choose Alternative 1 … at least 90 days"), 16081, 16089, 16090 and
variants ("As someone who cares deeply about national parks and the public lands that
sustain them"; the framing is the National Parks Conservation Association's, but no page
of theirs with the letter was found), 14627 (Montana; Wild Montana's Quorum centre),
14625 (hiker; close to Outdoor Alliance's form but not the same text), 14551 (climber;
Access Fund), 15225 (outdoor recreation enthusiast, DEIS), and the REI Cooperative Action
Network, Environment America (134) and Wyoming Outdoor Council campaigns the docket report
traced, whose pages refused the read and whose letters we could not identify.
