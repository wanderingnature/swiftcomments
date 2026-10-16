"""Comment sentences by the record's method (comment_sentences.units): the record's
terminator, abbreviation and fragment rules (a piece under four words joins its neighbour)."""

import hashlib

from comment_sentences import norm_key, plain_lines, sentence_hash, units


def texts(raw):
    return [t for _, _, t, _ in units(raw)]


def test_abbreviations_the_record_protects_are_protected_here():
    assert texts("I hike on Mt. Hood every single year. It is beautiful up there.") == [
        "I hike on Mt. Hood every single year.", "It is beautiful up there."]
    assert texts("See Docket No. FS-2025-0001 for the rule. Thanks for reading this far.") == [
        "See Docket No. FS-2025-0001 for the rule.", "Thanks for reading this far."]
    assert texts("Vermont Yankee Nuclear Power Corp. v. NRDC applies. So does State Farm.") == [
        "Vermont Yankee Nuclear Power Corp. v. NRDC applies.", "So does State Farm."]


def test_a_dot_inside_a_url_or_doi_does_not_end_a_sentence():
    raw = "Fires start near roads (https://doi.org/10.1098/rspb.2013.0184). Most of them are human-caused."
    assert texts(raw) == ["Fires start near roads (https://doi.org/10.1098/rspb.2013.0184).", "Most of them are human-caused."]


def test_a_closing_quote_stays_with_its_sentence():
    raw = 'The record says "roads increase ignitions." That settles the wildfire question.'
    assert texts(raw) == ['The record says "roads increase ignitions."', "That settles the wildfire question."]
    assert texts("“Once gone, they are gone.” — Aldo Leopold") == ["“Once gone, they are gone.” — Aldo Leopold"]


def test_block_tags_and_newlines_break_lines_and_list_markers_come_off():
    raw = "<p>• Protect drinking water for 60 million people.</p><p>• Keep wildlife corridors open.</p>Thank you.<br/>Sincerely, a voter."
    got = units(raw)
    assert got == [
        (5, 50, "Protect drinking water for 60 million people.", "list_item"),
        (59, 88, "Keep wildlife corridors open.", "list_item"),
        (92, 102, "Thank you.", "sentence"),
        (107, 126, "Sincerely, a voter.", "sentence"),
    ]
    assert all(raw[a:b] == t for a, b, t, _ in got)


def test_the_bullets_comments_use_are_list_markers_too():
    raw = "* National forests supply 46% of the nation's water.\n– Roads fragment habitat for many species.\n· Fires start near roads most of the time."
    assert units(raw) == [
        (2, 52, "National forests supply 46% of the nation's water.", "list_item"),
        (55, 95, "Roads fragment habitat for many species.", "list_item"),
        (98, 138, "Fires start near roads most of the time.", "list_item"),
    ]


def test_entities_are_unescaped_to_a_fixed_point_and_spans_point_into_the_stored_text():
    raw = "Roads &amp; fires go together.<br>It&amp;#39;s   a fact of life."
    got = units(raw)
    assert [t for _, _, t, _ in got] == ["Roads & fires go together.", "It's a fact of life."]
    assert raw[got[0][0]:got[0][1]] == "Roads &amp; fires go together."
    assert raw[got[1][0]:got[1][1]] == "It&amp;#39;s   a fact of life."


def test_a_long_line_without_terminal_punctuation_joins_the_next_line():
    first = "The agency's own cost-benefit analysis projects timber revenue of five to eleven million a year against"
    raw = first + "\nrecreation losses of at least six million a year. That is a loss on its own terms."
    assert texts(raw) == [first + " recreation losses of at least six million a year.", "That is a loss on its own terms."]
    # a short line is not a cut paragraph
    assert texts("Dear Secretary Rollins\nPlease keep the rule in place.") == ["Dear Secretary Rollins", "Please keep the rule in place."]


def test_fragments_join_their_neighbour_and_punctuation_only_pieces_are_dropped():
    assert texts("Not ever. We will fight this to the end.") == ["Not ever. We will fight this to the end."]
    assert texts("We will fight this to the end. Count on it.") == ["We will fight this to the end. Count on it."]
    assert texts("...") == []


def test_a_full_stop_with_no_space_after_it_still_ends_the_sentence():
    raw = "Please withdraw this rollback before they are gone.We live in Boulder City near the dam.It is our land!"
    assert texts(raw) == ["Please withdraw this rollback before they are gone.", "We live in Boulder City near the dam.", "It is our land!"]
    # not inside an abbreviation, a decimal or an acronym
    assert texts("Vermont Yankee Nuclear Power Corp.The rule costs 6.9 billion under 16 U.S.C. 1604.") == [
        "Vermont Yankee Nuclear Power Corp. The rule costs 6.9 billion under 16 U.S.C. 1604."]


def test_markdown_markers_zero_width_spaces_quote_markers_and_glued_bullets_come_off():
    raw = "**Fiscal Responsibility:** The agency already manages 370,000 miles of road.\n\u200bI urge the agency to adopt the No Action Alternative.\n> Old growth stores carbon for centuries.\n-These undeveloped lands are critical to our health.\n+God entrusted us with this planet.\na) Identify the beneficiaries of the change.\n2) Account for the road maintenance backlog."
    got = units(raw)
    assert [(t, k) for _, _, t, k in got] == [
        ("Fiscal Responsibility: The agency already manages 370,000 miles of road.", "sentence"),
        ("I urge the agency to adopt the No Action Alternative.", "sentence"),
        ("Old growth stores carbon for centuries.", "sentence"),
        ("These undeveloped lands are critical to our health.", "list_item"),
        ("God entrusted us with this planet.", "list_item"),
        ("Identify the beneficiaries of the change.", "list_item"),
        ("Account for the road maintenance backlog.", "list_item"),
    ]
    assert raw[got[1][0]:got[1][1]] == "I urge the agency to adopt the No Action Alternative."
    assert raw[got[3][0]:got[3][1]] == "These undeveloped lands are critical to our health."


def test_a_url_encoded_comment_is_decoded_and_its_encoded_newlines_break_lines():
    raw = "re:%20Rescission%20of%20the%20Roadless%20Rule,%20Docket%20FS-2025-0001%0A%0AThe%20forests%20my%20family%20camps%20in%20matter%20to%20me.%20They%20are%20worth%20more%20than%20timber."
    got = units(raw)
    assert [t for _, _, t, _ in got] == ["re: Rescission of the Roadless Rule, Docket FS-2025-0001",
                                         "The forests my family camps in matter to me.", "They are worth more than timber."]
    assert raw[got[1][0]:got[1][1]] == "The%20forests%20my%20family%20camps%20in%20matter%20to%20me."
    # a comment with only its newlines encoded is decoded too
    assert texts("The agency owes the public an explanation of that.%0A%0AFinally, the record says so.") == [
        "The agency owes the public an explanation of that.", "Finally, the record says so."]
    # a URL glued to the end of a sentence gets its space; being lowercase it stays with the sentence, as the record's rule has it
    assert texts("Please help me find one!https://chng.it/yJGDDhSfJB") == ["Please help me find one! https://chng.it/yJGDDhSfJB"]
    # a lone percent-escape in ordinary text is left alone
    assert texts("Roads raise ignition density by 300%20 years on from the rule.") == ["Roads raise ignition density by 300%20 years on from the rule."]


def test_a_full_stop_before_a_closing_quote_with_no_space_after_still_ends_the_sentence():
    raw = "The rule must be upheld across the Tongass National Forest.”Please keep the 2001 Roadless Rule."
    assert texts(raw) == ["The rule must be upheld across the Tongass National Forest.”", "Please keep the 2001 Roadless Rule."]


def test_lines_the_form_joined_with_a_bare_comma_are_parted():
    raw = "USDA Department of Agriculture Forest Service,Stop the impunity and keep the rule.\nThank you,Marguerite from California"
    assert texts(raw) == ["USDA Department of Agriculture Forest Service,", "Stop the impunity and keep the rule.", "Thank you,", "Marguerite from California"]
    # a comma with a space after it is ordinary prose
    assert texts("Roads bring erosion, Sediment and noise to the forest.") == ["Roads bring erosion, Sediment and noise to the forest."]


def test_a_writer_who_does_not_capitalise_still_gets_sentences():
    raw = "we do not want these roads. we want nature safe and untouched. i want a livable planet for my children."
    assert texts(raw) == ["we do not want these roads.", "we want nature safe and untouched.", "i want a livable planet for my children."]
    # a capitalising writer's lowercase after a full stop is left to the record's rule
    assert texts("The rule costs money, e.g. maintenance. the agency knows it.") == ["The rule costs money, e.g. maintenance. the agency knows it."]


def test_a_line_ending_in_a_url_does_not_join_the_next_line():
    first = "BioScience, 52(5), 411-422, a review of road effects on forest ecosystems https://academic.oup.com/bioscience/article/52/5/411/236110"
    raw = first + "\nJohnston, J. D., Kilbride, J. B., & Kennedy, R. E. (2021). Fire regimes of the West."
    assert texts(raw) == [first, "Johnston, J. D., Kilbride, J. B., & Kennedy, R. E. (2021).", "Fire regimes of the West."]


def test_an_attribution_line_does_not_join_the_sentence_after_it():
    src = "— Maine DEP NECEC Follow-up Joint NGO Comments (Appendix B), citing Laurance et al. 2017, 2017"
    assert texts(src + "\nThe rule works. Keep it in place for good.") == [src, "The rule works. Keep it in place for good."]


def test_heading_markers_double_hyphens_and_stray_leading_punctuation_come_off():
    raw = "### 4. Roadless areas provide essential public benefits\n--That dirt roads erode and need constant repair.\n#2 Rescinding the rule will not reduce wildfires.\n?I am writing to you today as a constituent.\n>> More roads will be detrimental to wildlife."
    assert [(t, k) for _, _, t, k in units(raw)] == [
        ("Roadless areas provide essential public benefits", "list_item"),  # '4. ' is the record's own list marker
        ("That dirt roads erode and need constant repair.", "list_item"),
        ("Rescinding the rule will not reduce wildfires.", "list_item"),
        ("I am writing to you today as a constituent.", "sentence"),
        ("More roads will be detrimental to wildlife.", "sentence"),
    ]


def test_plain_lines_maps_every_character_to_a_stored_offset():
    raw = "a&amp;b<p>c"
    plain, idx = plain_lines(raw)
    assert plain == "a&b\nc"
    assert idx == [0, 1, 6, 7, 10]


def test_the_sentence_hash_is_the_sentence_layer_key():
    t = "Roads &amp; fires go together."
    assert sentence_hash(t) == hashlib.sha256(norm_key(t).encode()).hexdigest()
    assert sentence_hash("Roads & fires go together") == sentence_hash(t)
