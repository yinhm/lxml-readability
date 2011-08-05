#!/usr/bin/env python
from cleaners import html_cleaner, clean_attributes
from collections import defaultdict
from htmls import build_doc, get_body, get_title, shorten_title
from lxml.etree import tostring, tounicode
from lxml.html import fragment_fromstring, document_fromstring
from lxml.html import builder as B
from lxml.html.diff import htmldiff
import difflib
import logging
import re
import sys
import urlfetch
import urlparse

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

PAGE_CLASS = 'article-page'

def describe(node, depth=1):
    if not hasattr(node, 'tag'):
        return "[%s]" % type(node)
    name = node.tag
    if node.get('id', ''): name += '#'+node.get('id') 
    if node.get('class', ''): 
        name += '.' + node.get('class').replace(' ','.')
    if name[:4] in ['div#', 'div.']:
        name = name[3:]
    if depth and node.getparent() is not None:
        return name+' - '+describe(node.getparent(), depth-1)
    return name

def to_int(x):
    if not x: return None
    x = x.strip()
    if x.endswith('px'):
        return int(x[:-2]) 
    if x.endswith('em'):
        return int(x[:-2]) * 12 
    return int(x)

def clean(text):
    text = re.sub('\s*\n\s*', '\n', text)
    text = re.sub('[ \t]{2,}', ' ', text)
    return text.strip()

def text_length(i):
    return len(clean(i.text_content() or ""))

def tags(node, *tag_names):
    for tag_name in tag_names:
        for e in node.findall('.//%s' % tag_name):
            yield e

def class_weight(e):
    weight = 0
    if e.get('class', None):
        if REGEXES['negativeRe'].search(e.get('class')):
            weight -= 25

        if REGEXES['positiveRe'].search(e.get('class')):
            weight += 25

    if e.get('id', None):
        if REGEXES['negativeRe'].search(e.get('id')):
            weight -= 25

        if REGEXES['positiveRe'].search(e.get('id')):
            weight += 25

    return weight

def score_node(elem):
    content_score = class_weight(elem)
    name = elem.tag.lower()
    if name == "div":
        content_score += 5
    elif name in ["pre", "td", "blockquote"]:
        content_score += 3
    elif name in ["address", "ol", "ul", "dl", "dd", "dt", "li", "form"]:
        content_score -= 3
    elif name in ["h1", "h2", "h3", "h4", "h5", "h6", "th"]:
        content_score -= 5
    return { 
        'content_score': content_score, 
        'elem': elem
    }

def split_into_parts(elem):
    '''
    Takes the text and children of an element and returns a list of parts.

    lxml represents an element's content by its .text property and its child
    elements.  Each child element has a .tail property to represent
    interspersed text.  For example, a div element that looks like this:

    <div>Hello <b>World</b>!  <i>- Jerry</i> C.</div>

    is represented (loosely) as:

    div element {
        text: 'Hello',
        children: [
                b element { text: 'World', tail: '!  ' },
                i element { text: '- Jerry', tail: 'C.' }
                ]
    }

    When breaking up divs into paragraphs (see
    transform_double_breaks_into_paragraphs_elem), this is an inconvenient
    representation, as we often need to break tail text away from its element.
    For example, if we have:

    ...end of a paragraph.<br><br>Start of a new paragraph...

    the start of the new paragraph will be the tail of the second br, which we
    will be replacing with a paragraph element that contains the second
    paragraph.

    To that end, this function gives us a representation that is easier to use.
    Instead of elements and tails, we just have a list of "parts".  A "part" is
    one of two things: an lxml element or a string.  Instead of interspersed
    text as part of the preceding element, we just break it out on its own.  So
    our "Hello World" above is represented as.
    [
        'Hello',
        b element { text: 'World' },
        '!  ',
        i element { text: '- Jerry' },
        'C.'
    ]
    '''
    parts = []

    if elem.text is not None:
        parts.append(elem.text)
        elem.text = None

    for child in elem:
        parts.append(child)
        if child.tail is not None:
            parts.append(child.tail)
        child.tail = None

    return parts

def append_or_set(base, value):
    if base is None:
        return value
    else:
        return base + value

def make_paragraph_from_parts(parts):
    '''
    Makes a paragraph element from the list of parts.  If the paragraph would
    be empty, None is returned.
    '''
    p = B.P()
    last_element = None
    for part in parts:
        if isinstance(part, basestring):
            if last_element is None:
                p.text = append_or_set(p.text, part)
            else:
                last_element.tail = append_or_set(last_element.tail, part)
        else:
            p.append(part)
            last_element = part
    
    if (p.text is None or p.text.strip() == '') and len(p) == 0:
        # No text or children.
        return None
    else:
        logging.debug('P: %s' % tostring(p))
        return p

def mark_if_whitespace(parts, left, right):
    '''
    Returns the set of indices between (exclusive) left and right in parts if
    the parts all represent whitespace.  If there is any non-whitespace, an
    empty set is returned.
    '''
    is_only_whitespace = True
    for i in range(left + 1, right):
        part = parts[i]
        if isinstance(part, basestring):
            if part.strip() != '':
                is_only_whitespace = False
                break
        else:
            is_only_whitespace = False
            break

    if is_only_whitespace:
        marked = set()
        for i in range(left + 1, right):
            marked.add(i)
        return marked
    else:
        return set()

def squeeze_breaks(parts):
    '''
    This is a preprocessing step for turning double-breaks into paragraphs
    where appropriate.  If two break tags are separated only by whitespace,
    that whitespace is filtered out and not included in the parts list that is
    returned.
    '''
    # Find the indices of the breaks.
    breaks = []
    for i, part in enumerate(parts):
        if not isinstance(part, basestring) and part.tag == 'br':
            breaks.append(i)

    # Look between breaks to see if there are only whitespace parts.  If so,
    # mark them for filtering.
    left_break = None
    marked = set()

    for b in breaks:
        if left_break is None:
            left_break = b
        else:
            right_break = b
            marked.update(mark_if_whitespace(parts, left_break, right_break))
            left_break = right_break

    # Filter parts and return.
    new_parts = []
    for i, part in enumerate(parts):
        if i not in marked:
            new_parts.append(part)

    return new_parts

def insert_p(parent, at_elem, parts):
    '''
    Inserts a paragraph element generated from a list of parts into the given
    parent, before the child element at_elem.  The parts may contain elements
    that are currently children of the parent.
    '''
    p = make_paragraph_from_parts(parts)
    if p is not None:
        index = parent.index(at_elem)
        parent.insert(index, p)
        logging.debug(
                'INSERTING AT %d IN PARENT: %s' %
                (index, tostring(parent))
                )
    del parts[:]

def append_p(parent, parts):
    '''
    Appends a paragraph element generated from a list of parts to the given
    parent.  The parts may contain elements that are currently children of the
    parent.
    '''
    p = make_paragraph_from_parts(parts)
    if p is not None:
        parent.append(p)
    del parts[:]

def transform_double_breaks_into_paragraphs_elem(elem):
    '''
    Transforms double-breaks that delineate paragraphs into proper paragraph
    elements.  See transform_double_breaks_into_paragraphs.
    '''
    # The algorithm walks the parts of the element looking for double-breaks,
    # accumulating parts with which to construct a paragraphs when they are
    # encountered.

    # We enter the BR state once we have seen a break and are looking to see if
    # there is another break immediately following it.
    START, BR = range(2)
    BLOCK_TAGS = (
            ['h%d' % i for i in range(1, 7)] +
            ['blockquote', 'div', 'img', 'p', 'pre', 'table']
            )

    state = START

    # We hang on to the first break we encounter, since we need to look ahead
    # one part before deciding what to do with it.
    first_br = None

    # We use this to accumulate parts that we will put into a paragraph where
    # we see fit.
    acc = []
    parts = squeeze_breaks(split_into_parts(elem))
    
    for part in parts:
        if state == START:
            if isinstance(part, basestring):
                acc.append(part)
            else:
                if part.tag == 'br':
                    first_br = part
                    state = BR
                elif part.tag in BLOCK_TAGS:
                    insert_p(elem, part, acc)
                else:
                    acc.append(part)
        elif state == BR:
            if isinstance(part, basestring):
                acc.append(first_br)
                acc.append(part)
            else:
                if part.tag == 'br':
                    first_br.drop_tree()
                    insert_p(elem, part, acc)
                    part.drop_tree()
                elif part.tag in BLOCK_TAGS:
                    acc.append(first_br)
                    insert_p(elem, part, acc)
                else:
                    acc.append(first_br)
                    acc.append(part)
            state = START
            first_br = None

    append_p(elem, acc)

def transform_double_breaks_into_paragraphs(doc):
    '''
    Modifies doc so that double-breaks (<br><br>) in content delineate
    paragraphs.  Some pages use double-breaks when they really should be using
    paragraphs:

        <div>
            Lorem ipsum dolor sit amet, consectetur adipiscing elit. Praesent
            in justo sapien, a consectetur est. Aliquam iaculis, augue eu
            euismod gravida, nisl nisl posuere odio, at euismod metus enim quis
            nibh.

            <br><br>

            Praesent posuere tortor at nunc iaculis eget suscipit tellus
            tempus.  Nulla facilisi. Quisque rutrum, ante eu sollicitudin
            congue, dui sapien egestas arcu, in consequat nisl metus eu sem.

            <br><br>

            Nam mi sem, lobortis eget adipiscing vitae, ultricies sit amet
            justo.  Nullam rutrum sodales magna vel vestibulum. Curabitur sit
            amet urna purus, ac aliquet sem.
        </div>

    This routine would transform this into:

        <div>
            <p>
            Lorem ipsum dolor sit amet, consectetur adipiscing elit. Praesent
            in justo sapien, a consectetur est. Aliquam iaculis, augue eu
            euismod gravida, nisl nisl posuere odio, at euismod metus enim quis
            nibh.
            </p>

            <p>
            Praesent posuere tortor at nunc iaculis eget suscipit tellus
            tempus.  Nulla facilisi. Quisque rutrum, ante eu sollicitudin
            congue, dui sapien egestas arcu, in consequat nisl metus eu sem.
            </p>

            <p>
            Nam mi sem, lobortis eget adipiscing vitae, ultricies sit amet
            justo.  Nullam rutrum sodales magna vel vestibulum. Curabitur sit
            amet urna purus, ac aliquet sem.
            </p>
        </div>
    '''
    for div in tags(doc, 'div'):
        transform_double_breaks_into_paragraphs_elem(div)

def transform_misused_divs_into_paragraphs(doc):
    for elem in tags(doc, 'div'):
        # transform <div>s that do not contain other block elements into <p>s
        logging.debug("Examining %s to see if misused" % (describe(elem)))
        logging.debug("  searching: %s" % unicode(''.join(map(tostring, list(elem)))))
        if not REGEXES['divToPElementsRe'].search(unicode(''.join(map(tostring, list(elem))))):
            logging.debug("Altering %s to p" % (describe(elem)))
            elem.tag = "p"
            #print "Fixed element "+describe(elem)
            
def remove_unlikely_candidates(doc):
    for elem in doc.iter():
        s = "%s %s" % (elem.get('class', ''), elem.get('id', ''))
        #logging.debug(s)
        if (REGEXES['unlikelyCandidatesRe'].search(s) and
                (not REGEXES['okMaybeItsACandidateRe'].search(s)) and
                elem.tag != 'body' and
                elem.getparent() is not None
                ):
            logging.debug("Removing unlikely candidate - %s" % describe(elem))
            elem.drop_tree()

def get_link_density(elem):
    link_length = 0
    for i in elem.findall(".//a"):
        link_length += text_length(i)
    #if len(elem.findall(".//div") or elem.findall(".//p")):
    #    link_length = link_length
    total_length = text_length(elem)
    return float(link_length) / max(total_length, 1)

def score_paragraphs(doc, options):
    candidates = {}
    #logging.debug(str([describe(node) for node in tags(doc, "div")]))

    ordered = []
    for elem in tags(doc, "p", "pre", "td"):
        logging.debug('Scoring %s' % describe(elem))
        parent_node = elem.getparent()
        if parent_node is None:
            continue 
        grand_parent_node = parent_node.getparent()

        inner_text = clean(elem.text_content() or "")
        inner_text_len = len(inner_text)

        # If this paragraph is less than 25 characters, don't even count it.
        if inner_text_len < options['min_text_len']:
            continue

        if parent_node not in candidates:
            candidates[parent_node] = score_node(parent_node)
            ordered.append(parent_node)
            
        if grand_parent_node is not None and grand_parent_node not in candidates:
            candidates[grand_parent_node] = score_node(grand_parent_node)
            ordered.append(grand_parent_node)

        content_score = 1
        content_score += len(inner_text.split(','))
        content_score += min((inner_text_len / 100), 3)
        #if elem not in candidates:
        #    candidates[elem] = score_node(elem)
            
        #WTF? candidates[elem]['content_score'] += content_score
        candidates[parent_node]['content_score'] += content_score
        if grand_parent_node is not None:
            candidates[grand_parent_node]['content_score'] += content_score / 2.0

    # Scale the final candidates score based on link density. Good content should have a
    # relatively small link density (5% or less) and be mostly unaffected by this operation.
    for elem in ordered:
        candidate = candidates[elem]
        ld = get_link_density(elem)
        score = candidate['content_score']
        logging.debug("Candid: %6.3f %s link density %.3f -> %6.3f" % (score, describe(elem), ld, score*(1-ld)))
        candidate['content_score'] *= (1 - ld)

    return candidates

def select_best_candidate(candidates):
    sorted_candidates = sorted(candidates.values(), key=lambda x: x['content_score'], reverse=True)
    for candidate in sorted_candidates[:5]:
        elem = candidate['elem']
        logging.debug("Top 5 : %6.3f %s" % (candidate['content_score'], describe(elem)))

    if len(sorted_candidates) == 0:
        return None

    best_candidate = sorted_candidates[0]
    return best_candidate

def reverse_tags(node, *tag_names):
    for tag_name in tag_names:
        for e in reversed(node.findall('.//%s' % tag_name)):
            yield e

def sanitize(node, candidates, options):
    for header in tags(node, "h1", "h2", "h3", "h4", "h5", "h6"):
        if class_weight(header) < 0 or get_link_density(header) > 0.33: 
            header.drop_tree()

    for elem in tags(node, "form", "iframe", "textarea"):
        elem.drop_tree()
    allowed = {}
    # Conditionally clean <table>s, <ul>s, and <div>s
    for el in reverse_tags(node, "table", "ul", "div"):
        if el in allowed:
            continue
        weight = class_weight(el)
        if el in candidates:
            content_score = candidates[el]['content_score']
            #print '!',el, '-> %6.3f' % content_score
        else:
            content_score = 0
        tag = el.tag

        if weight + content_score < 0:
            logging.debug("Cleaned %s with score %6.3f and weight %-3s" %
                (describe(el), content_score, weight, ))
            el.drop_tree()
        elif el.text_content().count(",") < 10:
            counts = {}
            for kind in ['p', 'img', 'li', 'a', 'embed', 'input']:
                counts[kind] = len(el.findall('.//%s' %kind))
            counts["li"] -= 100

            content_length = text_length(el) # Count the text length excluding any surrounding whitespace
            link_density = get_link_density(el)
            parent_node = el.getparent()
            if parent_node is not None:
                if parent_node in candidates:
                    content_score = candidates[parent_node]['content_score']
                else:
                    content_score = 0
            #if parent_node is not None:
                #pweight = class_weight(parent_node) + content_score
                #pname = describe(parent_node)
            #else:
                #pweight = 0
                #pname = "no parent"
            to_remove = False
            reason = ""

            #if el.tag == 'div' and counts["img"] >= 1:
            #    continue
            if counts["p"] and counts["img"] > counts["p"]:
                reason = "too many images (%s)" % counts["img"]
                to_remove = True
            elif counts["li"] > counts["p"] and tag != "ul" and tag != "ol":
                reason = "more <li>s than <p>s"
                to_remove = True
            elif counts["input"] > (counts["p"] / 3):
                reason = "less than 3x <p>s than <input>s"
                to_remove = True
            elif content_length < options['min_text_length'] and (counts["img"] == 0 or counts["img"] > 2):
                reason = "too short content length %s without a single image" % content_length
                to_remove = True
            elif weight < 25 and link_density > 0.2:
                    reason = "too many links %.3f for its weight %s" % (link_density, weight)
                    to_remove = True
            elif weight >= 25 and link_density > 0.5:
                reason = "too many links %.3f for its weight %s" % (link_density, weight)
                to_remove = True
            elif (counts["embed"] == 1 and content_length < 75) or counts["embed"] > 1:
                reason = "<embed>s with too short content length, or too many <embed>s"
                to_remove = True
            # if el.tag == 'div' and counts['img'] >= 1 and to_remove:
            #     imgs = el.findall('.//img')
            #     valid_img = False
            #     logging.debug(tounicode(el))
            #     for img in imgs:

            #         height = img.get('height')
            #         text_length = img.get('text_length')
            #         logging.debug ("height %s text_length %s" %(repr(height), repr(text_length)))
            #         if to_int(height) >= 100 or to_int(text_length) >= 100:
            #             valid_img = True
            #             logging.debug("valid image" + tounicode(img))
            #             break
            #     if valid_img:
            #         to_remove = False
            #         logging.debug("Allowing %s" %el.text_content())
            #         for desnode in tags(el, "table", "ul", "div"):
            #             allowed[desnode] = True

                #find x non empty preceding and succeeding siblings
                i, j = 0, 0
                x  = 1
                siblings = []
                for sib in el.itersiblings():
                    #logging.debug(sib.text_content())
                    sib_content_length = text_length(sib)
                    if sib_content_length:
                        i =+ 1
                        siblings.append(sib_content_length)
                        if i == x:
                            break
                for sib in el.itersiblings(preceding=True):
                    #logging.debug(sib.text_content())
                    sib_content_length = text_length(sib)
                    if sib_content_length:
                        j =+ 1
                        siblings.append(sib_content_length)
                        if j == x:
                            break
                #logging.debug(str(siblings))
                if siblings and sum(siblings) > 1000 :
                    to_remove = False
                    logging.debug("Allowing %s" % describe(el))
                    for desnode in tags(el, "table", "ul", "div"):
                        allowed[desnode] = True

            if to_remove:
                logging.debug("Cleaned %6.3f %s with weight %s cause it has %s." %
                    (content_score, describe(el), weight, reason))
                #print tounicode(el)
                #logging.debug("pname %s pweight %.3f" %(pname, pweight))
                el.drop_tree()

    # for el in ([node] + [n for n in node.iter()]):
    #     if not (self.options['attributes']):
    #         #el.attrib = {} #FIXME:Checkout the effects of disabling this
    #         pass

    return clean_attributes(tounicode(node))

def get_raw_article(candidates, best_candidate):
    # Now that we have the top candidate, look through its siblings for content that might also be related.
    # Things like preambles, content split by ads that we removed, etc.

    sibling_score_threshold = max([10, best_candidate['content_score'] * 0.2])
    article = B.DIV()
    article.attrib['id'] = 'page'
    best_elem = best_candidate['elem']
    for sibling in best_elem.getparent().getchildren():
        #if isinstance(sibling, NavigableString): continue#in lxml there no concept of simple text 
        append = False 
        if sibling is best_elem:
            append = True
        sibling_key = sibling #HashableElement(sibling)

        # Print out sibling information for debugging.
        if sibling_key in candidates:
            sibling_candidate = candidates[sibling_key]
            logging.debug(
                    "Sibling: %6.3f %s" %
                    (sibling_candidate['content_score'], describe(sibling))
                    )
        else:
            logging.debug("Sibling: %s" % describe(sibling))

        if sibling_key in candidates and candidates[sibling_key]['content_score'] >= sibling_score_threshold:
            append = True

        if sibling.tag == "p":
            link_density = get_link_density(sibling)
            node_content = sibling.text or ""
            node_length = len(node_content)

            if node_length > 80 and link_density < 0.25:
                append = True
            elif node_length < 80 and link_density == 0 and re.search('\.( |$)', node_content):
                append = True

        if append:
            article.append(sibling)

    #if article is not None: 
    #    article.append(best_elem)
    return article

def get_article(doc, options):
    try:
        ruthless = True
        while True:
            for i in tags(doc, 'script', 'style'):
                i.drop_tree()
            for i in tags(doc, 'body'):
                i.set('id', 'readabilityBody')
            if ruthless: 
                remove_unlikely_candidates(doc)
            transform_double_breaks_into_paragraphs(doc)
            transform_misused_divs_into_paragraphs(doc)
            candidates = score_paragraphs(doc, options)
            
            best_candidate = select_best_candidate(candidates)
            if best_candidate:
                confidence = best_candidate['content_score']
                article = get_raw_article(candidates, best_candidate)
            else:
                if ruthless:
                    logging.debug("ruthless removal did not work. ")
                    ruthless = False
                    logging.debug("ended up stripping too much - going for a safer parse")
                    # try again
                    continue
                else:
                    logging.debug("Ruthless and lenient parsing did not work. Returning raw html")
                    return Summary(0, None)

            unicode_cleaned_article = sanitize(article, candidates, options)
            cleaned_doc = fragment_fromstring(unicode_cleaned_article)
            cleaned_article = tostring(cleaned_doc)

            of_acceptable_length = len(cleaned_article or '') >= options['retry_length']
            if ruthless and not of_acceptable_length:
                ruthless = False
                continue # try again
            else:
                return Summary(confidence, cleaned_article)
    except StandardError as e:
        #logging.exception('error getting summary: ' + str(traceback.format_exception(*sys.exc_info())))
        logging.exception('error getting summary: ' )
        raise Unparseable(str(e)), None, sys.exc_info()[2]

def clean_segment_extension(segments, index, segment):
    if segment.find('.') == -1:
        return segment
    else:
        split_segment = segment.split('.')
        possible_type = split_segment[1]
        has_non_alpha = re.search(r'[^a-zA-Z]', possible_type)
        if has_non_alpha:
            return segment
        else:
            return split_segment[0]

def clean_segment_ewcms(segments, index, segment):
    """
    EW-CMS specific segment cleaning.  Quoth the original source:

        "EW-CMS specific segment replacement. Ugly.
         Example: http://www.ew.com/ew/article/0,,20313460_20369436,00.html"

    """
    return segment.replace(',00', '')

def clean_segment_page_number(segments, index, segment):
    # If our first or second segment has anything looking like a page number,
    # remove it.
    if index >= (len(segments) - 2):
        pattern = r'((_|-)?p[a-z]*|(_|-))[0-9]{1,2}$'
        cleaned = re.sub(pattern, '', segment, re.IGNORECASE)
        if cleaned == '':
            return None
        else:
            return cleaned
    else:
        return segment

def clean_segment_number(segments, index, segment):
    # If this is purely a number, and it's the first or second segment, it's
    # probably a page number.  Remove it.
    if index >= (len(segments) - 2) and re.search(r'^\d{1,2}$', segment):
        return None
    else:
        return segment

def clean_segment_index(segments, index, segment):
    if index == (len(segments) - 1) and segment.lower() == 'index':
        return None
    else:
        return segment

def clean_segment_short(segments, index, segment):
    # It is not clear to me what this is accomplishing.  The original
    # readability source just says:
    #
    #   "If our first or second segment is smaller than 3 characters, and the
    #    first segment was purely alphas, remove it."
    #
    # However, the code actually checks to make sure that there are no alphas
    # in the segment, rather than checking for purely alphas.
    alphas = re.search(r'[a-z]', segments[-1], re.IGNORECASE)
    if index >= (len(segments) - 2) and len(segment) < 3 and not alphas:
        return None
    else:
        return segment

def clean_segment(segments, index, segment):
    """
    Cleans a single segment of a URL to find the base URL.  The base URL is as
    a reference when evaluating URLs that might be next-page links.  Returns a
    cleaned segment string or None, if the segment should be omitted entirely
    from the base URL.
    """
    funcs = [
            clean_segment_extension,
            clean_segment_ewcms,
            clean_segment_page_number,
            clean_segment_number,
            clean_segment_index,
            clean_segment_short
            ]
    cleaned_segment = segment
    for func in funcs:
        if cleaned_segment is None:
            break
        cleaned_segment = func(segments, index, cleaned_segment)
    return cleaned_segment

def filter_none(seq):
    return [x for x in seq if x is not None]

def clean_segments(segments):
    cleaned = [
            clean_segment(segments, i, s)
            for i, s in enumerate(segments)
            ]
    return filter_none(cleaned)

def find_base_url(url):
    if url is None:
        return None
    parts = urlparse.urlsplit(url)
    segments = parts.path.split('/')
    cleaned_segments = clean_segments(segments)
    new_path = '/'.join(cleaned_segments)
    new_parts = (parts.scheme, parts.netloc, new_path, '', '')
    base_url = urlparse.urlunsplit(new_parts)
    logging.debug('url: %s' % url)
    logging.debug('base_url: %s' % base_url)
    return base_url

class NextPageCandidate():
    '''
    An object that tracks a single href that is a candidate for the location of
    the next page.  Note that this is distinct from the candidates used when
    trying to find the elements containing the article.
    '''

    def __init__(self, link_text, href):
        self.link_text = link_text
        self.href = href
        self.score = 0

def same_domain(lhs, rhs):
    split_lhs = urlparse.urlsplit(lhs)
    split_rhs = urlparse.urlsplit(rhs)
    if split_lhs.netloc == '' or split_rhs.netloc == '':
        return True
    else:
        return split_lhs.netloc == split_rhs.netloc

def strip_trailing_slash(s):
    return re.sub(r'/$', '', s)

def eval_href(parsed_urls, url, base_url, link):
    raw_href = link.get('href')
    if raw_href is None:
        return None, None, False

    href = strip_trailing_slash(raw_href)
    logging.debug('evaluating next page link: %s' % href)
        
    # If we've already seen this page, ignore it.
    if href == base_url or href == url or href in parsed_urls:
        logging.debug('rejecting %s: already seen page' % href)
        return raw_href, href, False

    # If it's on a different domain, skip it.
    if url is not None and not same_domain(url, href):
        logging.debug('rejecting %s: different domain' % href)
        return raw_href, href, False
    
    return raw_href, href, True

def eval_link_text(link):
    link_text = clean(link.text_content() or '')
    if REGEXES['extraneous'].search(link_text) or len(link_text) > 25:
        return link_text, False
    else:
        return link_text, True

def find_or_create_page_candidate(candidates, href, link_text):
    '''
    Finds or creates a candidate page object for a next-page href.  If one
    exists already, which happens if there are multiple links with the same
    href, it is just returned.  This returns the tuple: (<the found or created
    candidate>, <True iff the candidate was created, False if it already
    existed>).
    '''
    if href in candidates:
        return candidates[href], False
    else:
        candidate = NextPageCandidate(link_text, href)
        candidates[href] = candidate
        return candidate, True

def eval_possible_next_page_link(
            parsed_urls, url, base_url, candidates, link):

    raw_href, href, ok = eval_href(parsed_urls, url, base_url, link)
    if not ok:
        return

    link_text, ok = eval_link_text(link)
    if not ok:
        return

    # If the leftovers of the URL after removing the base URL don't contain any
    # digits, it's certainly not a next page link.
    if base_url is not None:
        href_leftover = href.replace(base_url, '')
        if not re.search(r'\d', href_leftover):
            return

    candidate, created = find_or_create_page_candidate(
            candidates,
            href,
            link_text
            )

    if not created:
        candidate.link_text += ' | ' + link_text

    link_class_name = link.get('class') or ''
    link_id = link.get('id') or ''
    link_data = ' '.join([link_text, link_class_name, link_id])
    logging.debug('link: %s' % tostring(link))
    logging.debug('link_data: %s' % link_data)

    if base_url is not None and href.find(base_url) != 0:
        logging.debug('no base_url')
        candidate.score -= 25

    if REGEXES['nextLink'].search(link_data):
        logging.debug('link_data nextLink regex match')
        candidate.score += 50

    if REGEXES['page'].search(link_data):
        logging.debug('link_data page regex match')
        candidate.score += 25

    if REGEXES['firstLast'].search(link_data):
        # If we already matched on "next", last is probably fine. If we didn't,
        # then it's bad.  Penalize.
        if not REGEXES['nextLink'].search(candidate.link_text):
            logging.debug('link_data matched last but not next')
            candidate.score -= 65

    neg_re = REGEXES['negativeRe']
    ext_re = REGEXES['extraneous']
    if neg_re.search(link_data) or ext_re.search(link_data):
        logging.debug('link_data negative/extraneous regex match')
        candidate.score -= 50

    if REGEXES['prevLink'].search(link_data):
        logging.debug('link_data prevLink match')
        candidate.score -= 200

    parent = link.getparent()
    positive_node_match = False
    negative_node_match = False
    while parent is not None:
        parent_class = parent.get('class') or ''
        parent_id = parent.get('id') or ''
        parent_class_and_id = ' '.join([parent_class, parent_id])
        if not positive_node_match:
            if REGEXES['page'].search(parent_class_and_id):
                logging.debug('positive ancestor match')
                positive_node_match = True
                candidate.score += 25
        if not negative_node_match:
            if REGEXES['negativeRe'].search(parent_class_and_id):
                if not REGEXES['positiveRe'].search(parent_class_and_id):
                    logging.debug('negative ancestor match')
                    negative_node_match = True
                    candidate.score -= 25
        parent = parent.getparent()

    if REGEXES['page'].search(href):
        logging.debug('href regex match')
        candidate.score += 25

    if REGEXES['extraneous'].search(href):
        logging.debug('extraneous regex match')
        candidate.score -= 15

    try:
        link_text_as_int = int(link_text)

        logging.debug('link_text looks like %d' % link_text_as_int)
        # Punish 1 since we're either already there, or it's probably before
        # what we want anyways.
        if link_text_as_int == 1:
            candidate.score -= 10
        else:
            candidate.score += max(0, 10 - link_text_as_int)
    except ValueError as e:
        pass

    logging.debug('final score is %d' % candidate.score)

def find_next_page_url(parsed_urls, url, elem):
    links = tags(elem, 'a')
    base_url = find_base_url(url)
    # candidates is a mapping from URLs to NextPageCandidate objects that
    # represent information used to determine if a URL points to the next page
    # in the article.
    candidates = {}
    for link in links:
        eval_possible_next_page_link(
                parsed_urls,
                url,
                base_url,
                candidates,
                link
                )
    top_page = None
    for url, page in candidates.items():
        logging.debug('next page score of %s: %s' % (url, page.score))
        if 50 <= page.score and (not top_page or top_page.score < page.score):
            top_page = page

    if top_page:
        logging.debug('next page link found: %s' % top_page.href)
        parsed_urls.add(top_page.href)
        return top_page.href
    else:
        return None

def page_id(i):
    return 'page-%d' % (i + 1)

def make_page_elem(page_index, elem):
    elem.attrib['id'] = page_id(page_index)
    elem.attrib['class'] = PAGE_CLASS

def first_paragraph(elem):
    paragraphs = elem.xpath('.//p')
    if len(paragraphs) > 0:
        return paragraphs[0]
    else:
        return None

def is_suspected_duplicate(doc, page_doc):
    page_p = first_paragraph(page_doc)
    if page_p is None:
        return False
    pages = doc.xpath('//*[contains(@class, $name)]', name = PAGE_CLASS)
    for existing_page in pages:
        existing_page_p = first_paragraph(existing_page)
        if existing_page_p is not None:
            page_p_content = page_p.xpath('string()')
            existing_page_p_content = existing_page_p.xpath('string()')
            if page_p_content == existing_page_p_content:
                return True
    return False

def append_next_page(parsed_urls, page_index, page_url, doc, options):
    logging.debug('appending next page: %s' % page_url)
    fetcher = options['urlfetch']
    try:
        html = fetcher.urlread(page_url)
    except Exception as e:
        logging.warning('exception fetching %s' % page_url, exc_info = True)
        return
    orig_page_doc = parse(html, page_url)
    next_page_url = find_next_page_url(parsed_urls, page_url, orig_page_doc)
    page_article = get_article(orig_page_doc, options)
    page_doc = fragment_fromstring(page_article.html)
    make_page_elem(page_index, page_doc)
    if not is_suspected_duplicate(doc, page_doc):
        doc.append(page_doc)
        if next_page_url is not None:
            append_next_page(
                    parsed_urls,
                    page_index + 1,
                    next_page_url,
                    doc,
                    options
                    )

def parse(input, url):
    logging.debug('parse url: %s', url)
    raw_doc = build_doc(input)
    doc = html_cleaner.clean_html(raw_doc)
    if url:
        doc.make_links_absolute(url, resolve_base_href=True)
    else:
        doc.resolve_base_href()
    
    return doc

class Unparseable(ValueError):
    pass

class Summary:
    '''
    The type of object returned by Document.summary().  This includes the
    confidence level we have in our summary.  If this is low (<35), our summary
    may not be valid, though we did our best.
    '''

    def __init__(self, confidence, html):
        self.confidence = confidence
        self.html = html

class Document:
    TEXT_LENGTH_THRESHOLD = 25
    RETRY_LENGTH = 250

    def __init__(self, input, **options):
        self.input = input
        self.options = defaultdict(lambda: None)

        # Set some defaults for the options before overwriting them with what's
        # passed in.
        self.options['urlfetch'] = urlfetch.UrlFetch()
        self.options['min_text_length'] = self.TEXT_LENGTH_THRESHOLD
        self.options['retry_length'] = self.RETRY_LENGTH

        logging.debug('options: %s' % options)

        for k, v in options.items():
            self.options[k] = v

        self.html = None

    def _html(self, force=False):
        if force or self.html is None:
            self.html = parse(self.input, self.options['url'])
        return self.html
    
    def content(self):
        return get_body(self._html(True))
    
    def title(self):
        return get_title(self._html(True))

    def short_title(self):
        return shorten_title(self._html(True))

    def summary(self):
        doc = self._html(True)
        parsed_urls = set()
        url = self.options['url']
        if url is not None:
            parsed_urls.add(url)
        next_page_url = find_next_page_url(parsed_urls, url, doc)
        page_0 = get_article(doc, self.options)
        page_0_doc = fragment_fromstring(page_0.html)
        page_index = 0
        make_page_elem(page_index, page_0_doc)
        article_doc = B.DIV(page_0_doc)
        article_doc.attrib['id'] = 'article'
        if next_page_url is not None:
            append_next_page(
                    parsed_urls,
                    page_index + 1,
                    next_page_url,
                    article_doc,
                    self.options
                    )
        return Summary(page_0.confidence, tostring(article_doc))

class HashableElement():
    def __init__(self, node):
        self.node = node
        self._path = None

    def _get_path(self):
        if self._path is None:
            reverse_path = []
            node = self.node
            while node is not None:
                node_id = (node.tag, tuple(node.attrib.items()), node.text)
                reverse_path.append(node_id)
                node = node.getparent()
            self._path = tuple(reverse_path)
        return self._path
    path = property(_get_path)

    def __hash__(self):
        return hash(self.path)

    def __eq__(self, other):
        return self.path == other.path

    def __getattr__(self, tag):
        return getattr(self.node, tag)

def pretty_print(html):
    doc = document_fromstring(html, remove_blank_text = True)
    print(tostring(doc, pretty_print = True))

def readability_main():
    from optparse import OptionParser
    parser = OptionParser(usage="%prog: [options] [file]")
    parser.add_option('-v', '--verbose', action='store_true')
    parser.add_option('-u', '--url', help="use URL instead of a local file")
    (options, args) = parser.parse_args()
    
    if not (len(args) == 1 or options.url):
        parser.print_help()
        sys.exit(1)
    logging.basicConfig(level=logging.INFO)

    file = None
    if options.url:
        import urllib
        file = urllib.urlopen(options.url)
    else:
        file = open(args[0])
    try:
        print Document(file.read(), debug=options.verbose).summary().html
    finally:
        file.close()

def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        if len(sys.argv) > 2 and sys.argv[2] == '--debug':
            del sys.argv[2]
            logging.basicConfig(level = logging.DEBUG)
        else:
            logging.basicConfig(level = logging.INFO)
        del sys.argv[1]
        unittest.main()
    else:
        logging.basicConfig(level = logging.INFO)
        readability_main()

if __name__ == '__main__':
    main()
