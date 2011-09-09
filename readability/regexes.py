"""
Regular expressions used by readability processing.
"""

import re

REGEXES = {
    'unlikelyCandidatesRe': re.compile('combx|comment|community|disqus|extra|foot|header|menu|remark|rss|shoutbox|sidebar|sponsor|ad-break|agegate|pagination|pager|popup|tweet|twitter',re.I),
    'okMaybeItsACandidateRe': re.compile('and|article|body|column|main|shadow',re.I),
    'positiveRe': re.compile('article|body|content|entry|hentry|main|page|pagination|post|text|blog|story',re.I),
    'negativeRe': re.compile('combx|comment|com-|contact|foot|footer|footnote|masthead|media|meta|outbrain|promo|related|scroll|shoutbox|sidebar|sponsor|shopping|tags|tool|widget',re.I),
    'extraneous': re.compile(r'print|archive|comment|discuss|e[\-]?mail|share|reply|all|login|sign|single', re.I),
    'divToPElementsRe': re.compile('<(a|blockquote|dl|div|img|ol|p|pre|table|ul)',re.I),
    'nextLink': re.compile(r'(next|weiter|continue|>[^\|]$)', re.I), # Match: next, continue, >, >>, but not >|, as those usually mean last.
    'prevLink': re.compile(r'(prev|earl|old|new|<)', re.I),
    'page': re.compile(r'pag(e|ing|inat)', re.I),
    'firstLast': re.compile(r'(first|last)', re.I)
    #'replaceBrsRe': re.compile('(<br[^>]*>[ \n\r\t]*){2,}',re.I),
    #'replaceFontsRe': re.compile('<(\/?)font[^>]*>',re.I),
    #'trimRe': re.compile('^\s+|\s+$/'),
    #'normalizeRe': re.compile('\s{2,}/'),
    #'killBreaksRe': re.compile('(<br\s*\/?>(\s|&nbsp;?)*){1,}/'),
    #'videoRe': re.compile('http:\/\/(www\.)?(youtube|vimeo)\.com', re.I),
    #skipFootnoteLink:      /^\s*(\[?[a-z0-9]{1,2}\]?|^|edit|citation needed)\s*$/i,
}

