#!/usr/bin/env python
from cleaners import html_cleaner, clean_attributes
from collections import defaultdict
from htmls import build_doc, get_body, get_title, shorten_title, tags, clean, parse
from lxml.etree import tostring, tounicode
from lxml.html import fragment_fromstring, document_fromstring
from lxml.html import builder as B
from lxml.html.diff import htmldiff
from multi_page import append_next_page, find_next_page_url, make_page_elem
from regexes import REGEXES
import difflib
import logging
import os
import re
import sys
import tempfile
import urlfetch
import urllib
import urlparse
import webbrowser

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

def text_length(i):
    return len(clean(i.text_content() or ""))

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
            cleaned_article = tounicode(cleaned_doc)

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
        page_0 = get_article(doc, self.options)
        if page_0.html:
            # we fetch page_0 only for now.
            return Summary(page_0.confidence, page_0)
        next_page_url = find_next_page_url(parsed_urls, url, doc)
        page_0_doc = fragment_fromstring(page_0.html)
        page_index = 0
        make_page_elem(page_index, page_0_doc)
        article_doc = B.DIV(page_0_doc)
        article_doc.attrib['id'] = 'article'
        if next_page_url is not None:
            append_next_page(
                    get_article,
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

def parse_args():
    from optparse import OptionParser

    parser = OptionParser(usage = '%prog: [options]')
    parser.add_option('-v', '--verbose', action = 'store_true')
    parser.add_option('-u', '--url', help = 'load from URL')
    parser.add_option('-f', '--file', help = 'load from file at path')
    
    parser.add_option(
            '-o',
            '--open-browser',
            action = 'store_true',
            help = 'try to open the result in a browser'
            )

    options, args = parser.parse_args()
    return parser, options, args

def check_options(options):
    return options.file or options.url

def file_from_options(options):
    if options.url:
        import urllib
        try:
            return urllib.urlopen(options.url), options.url, None
        except IOError as e:
            err = 'Failed to open \'%s\' with error:\n%s' % (options.url, e)
            return None, None, err
    elif options.file:
        return open(options.file), None, None
    else:
        raise Exception('either file or url must be set')

DISPLAY_CSS = '''
#article {
    margin: 0 auto;
    max-width: 705px;
    min-width: 225px;
    font-family: Georgia, 'Times New Roman', serif;
    font-size: 19px;
    line-height: 29px;
}

#article p {
    font-size: 19px;
    line-height: 29px;
    margin: 19px 0px 19px 0px;
}

h1.articleTitle {
    text-align: center;
}
'''

def full_html_from_doc(doc):
    article_element = fragment_fromstring(doc.summary().html)
    html_element = B.HTML(
            B.HEAD(
                B.TITLE(doc.title()),
                B.STYLE(DISPLAY_CSS, type = 'text/css')
                ),
            B.BODY(
                B.H1(doc.title(), {'class': 'articleTitle'}),
                article_element
                )
            )
    return tostring(html_element)

def open_in_browser(doc):
    html = full_html_from_doc(doc)
    fd, path = tempfile.mkstemp(suffix = '.html')
    file = os.fdopen(fd, 'w')
    file.write(html)
    url = 'file://%s' % urllib.pathname2url(path)
    logging.debug(url)
    webbrowser.open(url)

def show_results(options, doc):
    if options.open_browser:
        open_in_browser(doc)
    else:
        print doc.summary().html

def make_doc(file, url, options):
    doc_options = {
            'debug': options.verbose
            }
    if url:
        doc_options['url'] = url
    return Document(file.read(), **doc_options)

def setup_logging(options):
    if options.verbose:
        logging.basicConfig(level = logging.DEBUG)
    else:
        logging.basicConfig(level = logging.INFO)

def readability_main():
    parser, options, _ = parse_args()
    setup_logging(options)
    if not check_options(options):
        parser.print_help()
        sys.exit(1)
    file, url, err = file_from_options(options)
    if not file:
        print err
        sys.exit(1)
    doc = make_doc(file, url, options)
    show_results(options, doc)

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
        readability_main()

if __name__ == '__main__':
    main()
