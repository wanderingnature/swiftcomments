"""The comparison key of comment text, and the markup and entity repair it rests on. The sentence hash (units.sentence_hash) is sha256 of it."""
import html
import re

# Comment text carries the submission form's markup. Two copies of ONE campaign
# sentence differing only in '<br/>' vs '<br/><br/>' normalized to two
# different keys, so neither reached BOILER_K and the cluster key came out
# different per copy — scattering one letter across several sub-10 clusters,
# each member then paying for its own call. Markup and entities are not
# content: strip them before the sentence becomes a key. A tag may carry
# attributes ("<span style='padding-left: 30px'>"): 2,665 roadless survivors
# do, and an unstripped one held copies of a campaign sentence apart.
_MARKUP = re.compile(
    r"</?(?:br|p|div|span|b|i|u|em|strong|li|ul|ol)(?:\s[^<>]*)?/?>",
    re.IGNORECASE)

def _unescape(s):
    """html.unescape to a fixed point. The submission form escaped some text
    twice ('&amp;#39;', '&amp;quot;' — six roadless survivors), and one pass
    leaves a literal '&#39;' behind."""
    while True:
        t = html.unescape(s)
        if t == s:
            return t
        s = t


def unescape_text(s):
    """The DISPLAY form of a string the submission form encoded: markup and
    entities repaired, spacing collapsed, punctuation and case untouched.
    'DeVelice &amp; Martin(2001)' -> 'DeVelice & Martin(2001)'."""
    return " ".join(_unescape(_MARKUP.sub(" ", s)).split())


_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def norm_key(s):
    """The COMPARISON key: two strings differing only in encoding, markup,
    case, punctuation or spacing are the same claim.

    Compared as raw bytes, one sentence encoded three ways ('&rsquo;', '&#39;',
    a literal apostrophe) would count as three distinct claims. This is the
    comparison, once,
    for excerpts, synthesized statements and citation references alike.

    Never stored and never shown — the original text is what goes to the
    model and to the reader."""
    return _NON_ALNUM.sub("", unescape_text(s).lower())
