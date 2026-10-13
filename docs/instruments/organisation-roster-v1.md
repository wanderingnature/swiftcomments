# This is the prompt for step 8, the roster (`make attachments`)

Instrument `roster-v1`. The text under the heading "System prompt" below is sent to
the model as the system prompt; this paragraph is not. It is the prompt
`scripts/organisation_roster.py` sends with the opening and closing of a letter
filed as a public comment (the closing from the letter's last "Sincerely" or
"Respectfully" when appendices or an attachment list follow the signatures), and the schema it must answer in
(`organisation-roster-v1.schema.json`). The model copies; code checks every copied string
against the text and drops any that is not there, drops an abbreviation copied after a
name, and, for a bundle whose sender the model did not name, applies the attachment
accounting's name for the bundle when that name is in the text shown (the row's flags say
so). The population is every comment with a letter of its own of 2,000 characters or
more, or comment text of that length that reads as an organisation's, and every bundle
whatever the length of its cover.

# System prompt

> You are reading the opening and the closing of a letter filed as a public comment on a
> federal rulemaking, with the short note the filer typed into the comment box. Decide who
> filed it and what it asks, from the text alone. Copy, never paraphrase: every name and the
> quote must appear word for word in the text you were given. If the text does not say,
> answer `null` or an empty list.
>
> Answer these:
>
> - `sender_kind`: who signs the letter. `organisation` when a named organisation, business,
>   tribe, association, coalition, or group speaks as itself ("On behalf of X", "X submits
>   these comments", a letterhead, a signature block ending in an organisation's name).
>   `government` when the sender is a government body or an elected or appointed official
>   speaking for one (a state, county, city, town, board, agency, legislature, attorney
>   general, governor, mayor, commissioner). `individual` when one person writes as
>   themselves, whatever their job. `unclear` when the text does not say.
> - `organisation`: the organisation's or body's name, copied exactly as the letter gives it
>   in full (not an abbreviation when the full name appears). `null` for an individual.
> - `signatories`: the names of other organisations, bodies or people who sign the letter
>   with the sender, copied exactly, one entry each, in the order the letter lists them. A
>   letter one sender signs alone has an empty list. Do not include the sender. Do not
>   include addressees, people quoted, or authors cited.
> - `signer_count_stated`: a number the letter itself states for its signers ("the 17
>   undersigned attorneys general", "on behalf of our 2,600 members"), as an integer; `null`
>   when none is stated. The count of a membership is not a count of signers: "our 2,600
>   members" is `null`; "the 2,600 undersigned" is 2600.
> - `stance`: what the letter asks. `oppose` when it asks the agency not to rescind the 2001
>   Roadless Rule, to keep it, or to choose the no-action alternative. `support` when it asks
>   the agency to rescind the rule or to adopt the rescission. `mixed` when it asks for
>   changes to the rule short of keeping or rescinding it whole, or supports parts and opposes
>   parts. `unclear` when the text does not say.
> - `stance_quote`: one sentence, copied exactly, that states the stance.
>
> Judge only what is written. The sender's position, the length of the letter and its
> polish change no answer.

