#!/usr/bin/env python
from cleaners import html_cleaner, clean_attributes
from collections import defaultdict
from htmls import build_doc, get_body, get_title, shorten_title
from lxml.etree import tostring, tounicode
from lxml.html import fragment_fromstring, document_fromstring
from lxml.html import builder as B
import logging
import re
import sys
import unittest
import urlfetch
import urlparse

logging.basicConfig(level=logging.DEBUG)

REGEXES = {
    'unlikelyCandidatesRe': re.compile('combx|comment|community|disqus|extra|foot|header|menu|remark|rss|shoutbox|sidebar|sponsor|ad-break|agegate|pagination|pager|popup|tweet|twitter',re.I),
    'okMaybeItsACandidateRe': re.compile('and|article|body|column|main|shadow',re.I),
    'positiveRe': re.compile('article|body|content|entry|hentry|main|page|pagination|post|text|blog|story',re.I),
    'negativeRe': re.compile('combx|comment|com-|contact|foot|footer|footnote|masthead|media|meta|outbrain|promo|related|scroll|shoutbox|sidebar|sponsor|shopping|tags|tool|widget',re.I),
    'extraneous': re.compile(r'print|archive|comment|discuss|e[\-]?mail|share|reply|all|login|sign|single', re.I),
    'divToPElementsRe': re.compile('<(a|blockquote|dl|div|img|ol|p|pre|table|ul)',re.I),
    'nextLink': re.compile(r'(next|weiter|continue|>[^\|]|$)', re.I), # Match: next, continue, >, >>, but not >|, as those usually mean last.
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

def transform_misused_divs_into_paragraphs(doc):
    for elem in tags(doc, 'div'):
        # transform <div>s that do not contain other block elements into <p>s
        if not REGEXES['divToPElementsRe'].search(unicode(''.join(map(tostring, list(elem))))):
            logging.debug("Altering %s to p" % (describe(elem)))
            elem.tag = "p"
            #print "Fixed element "+describe(elem)
            
    for elem in tags(doc, 'div'):
        if elem.text and elem.text.strip():
            p = fragment_fromstring('<p/>')
            p.text = elem.text
            elem.text = None
            elem.insert(0, p)
            logging.debug("Appended %s to %s" % (tounicode(p), describe(elem)))
            #print "Appended "+tounicode(p)+" to "+describe(elem)
        
        for pos, child in reversed(list(enumerate(elem))):
            if child.tail and child.tail.strip():
                p = fragment_fromstring('<p/>')
                p.text = child.tail
                child.tail = None
                elem.insert(pos + 1, p)
                logging.debug("Inserted %s to %s" % (tounicode(p), describe(elem)))
                #print "Inserted "+tounicode(p)+" to "+describe(elem)
            if child.tag == 'br':
                #print 'Dropped <br> at '+describe(elem) 
                child.drop_tree()

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

def score_paragraphs(doc, min_text_len):
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
        if inner_text_len < min_text_len:
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

def sanitize(node, candidates, min_text_len):
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
            elif content_length < (min_text_len) and (counts["img"] == 0 or counts["img"] > 2):
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
    article.attrib['id'] = 'article'
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

def get_article(doc, min_text_len, retry_len):
    try:
        ruthless = True
        while True:
            for i in tags(doc, 'script', 'style'):
                i.drop_tree()
            for i in tags(doc, 'body'):
                i.set('id', 'readabilityBody')
            if ruthless: 
                remove_unlikely_candidates(doc)
            transform_misused_divs_into_paragraphs(doc)
            candidates = score_paragraphs(doc, min_text_len)
            
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

            unicode_cleaned_article = sanitize(
                    article,
                    candidates,
                    min_text_len
                    )
            cleaned_doc = fragment_fromstring(unicode_cleaned_article)
            cleaned_article = tostring(cleaned_doc)

            of_acceptable_length = len(cleaned_article or '') >= retry_len
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
    return urlparse.urlunsplit(new_parts)

class CandidatePage():
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

def find_or_create_page(candidates, href, link_text):
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
        candidate = CandidatePage(link_text, href)
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

    candidate, created = find_or_create_page(candidates, href, link_text)
    if not created:
        candidate.link_text += ' | ' + link_text

    link_class_name = link.get('class') or ''
    link_id = link.get('id') or ''
    link_data = ' '.join([link_text, link_class_name, link_id])

    if base_url is not None and href.find(base_url) != 0:
        candidate.score -= 25

    if REGEXES['nextLink'].search(link_data):
        candidate.score += 50

    if REGEXES['page'].search(link_data):
        candidate.score += 25

    if REGEXES['firstLast'].search(link_data):
        if not REGEXES['nextLink'].search(candidate.link_text):
            candidate.score -= 65

    neg_re = REGEXES['negativeRe']
    ext_re = REGEXES['extraneous']
    if neg_re.search(link_data) or ext_re.search(link_data):
        candidate.score -= 50

    if REGEXES['prevLink'].search(link_data):
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
                positive_node_match = True
                candidate.score += 25
        if not negative_node_match:
            if REGEXES['negativeRe'].search(parent_class_and_id):
                if not REGEXES['positiveRe'].search(parent_class_and_id):
                    negative_node_match = True
                    candidate.score -= 25
        parent = parent.getparent()

    if REGEXES['page'].search(href):
        candidate.score += 25

    if REGEXES['extraneous'].search(href):
        candidate.score -= 15

    try:
        link_text_as_int = int(link_text)

        # Punish 1 since we're either already there, or it's probably before
        # what we want anyways.
        if link_text_as_int == 1:
            candidate.score -= 10
        else:
            candidate.score += max(0, 10 - link_text_as_int)
    except ValueError as e:
        pass

def find_next_page_link(parsed_urls, url, elem):
    links = tags(elem, 'a')
    base_url = find_base_url(url)
    # candidates is a mapping from URLs to CandidatePage objects that represent
    # information used to determine if a URL points to the next page in the
    # article.
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

def append_next_page(fetcher, next_page_link, doc):
    # html = fetcher.urlread(next_page_link)
    # page_doc = parse(html, next_page_link)
    pass

def parse(input, url):
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
        for k, v in options.items():
            self.options[k] = v
        if not self.options['urlfetch']:
            self.options['urlfetch'] = urlfetch.UrlFetch()
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
        next_page_link = find_next_page_link(parsed_urls, url, doc)
        if next_page_link is not None:
            fetcher = self.options['urlfetch']
            append_next_page(fetcher, next_page_link, doc)
        min_text_len = self.options.get(
                'min_text_length',
                self.TEXT_LENGTH_THRESHOLD
                )
        retry_len = self.options.get('retry_length', self.RETRY_LENGTH)
        return get_article(doc, min_text_len, retry_len)

    def debug(self, *a):
        #if self.options['debug']:
            logging.debug(*a)

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

class TestFindBaseUrl(unittest.TestCase):

    def setUp(self):
        self.longMessage = True

    def _assert_url(self, url, expected_base_url, msg = None):
        actual_base_url = find_base_url(url)
        self.assertEqual(expected_base_url, actual_base_url, msg)

    def _run_urls(self, specs):
        """
        Asserts expected results on a sequence of specs, where each spec is a
        pair: (URL, expected base URL).
        """
        for spec in specs:
            url = spec[0]
            expected = spec[1]
            if len(spec) > 2:
                msg = spec[2]
            else:
                msg = None
            self._assert_url(url, expected, msg)

    def test_none(self):
        self._assert_url(None, None)

    def test_no_change(self):
        url = 'http://foo.com/article'
        self._assert_url(url, url)

    def test_extension_stripping(self):
        specs = [
                (
                'http://foo.com/article.html',
                'http://foo.com/article',
                'extension should be stripped'
                ),
                (
                'http://foo.com/path/to/article.html',
                'http://foo.com/path/to/article',
                'extension should be stripped'
                ),
                (
                'http://foo.com/article.123not',
                'http://foo.com/article.123not',
                '123not is not extension'
                ),
                (
                'http://foo.com/path/to/article.123not',
                'http://foo.com/path/to/article.123not',
                '123not is not extension'
                )
                ]
        self._run_urls(specs)

    def test_ewcms(self):
        self._assert_url(
                'http://www.ew.com/ew/article/0,,20313460_20369436,00.html',
                'http://www.ew.com/ew/article/0,,20313460_20369436'
                )

    def test_page_numbers(self):
        specs = [
                (
                'http://foo.com/page5.html',
                'http://foo.com',
                'page number should be stripped'
                ),
                (
                'http://foo.com/path/to/page5.html',
                'http://foo.com/path/to',
                'page number should be stripped'
                ),
                (
                'http://foo.com/article-5.html',
                'http://foo.com/article',
                'page number should be stripped'
                )
                ]
        self._run_urls(specs)

    def test_numbers(self):
        specs = [
                (
                'http://foo.com/5.html',
                'http://foo.com',
                'number should be stripped'
                ),
                (
                'http://foo.com/path/to/5.html',
                'http://foo.com/path/to',
                'number should be stripped'
                )
                ]
        self._run_urls(specs)

    def test_index(self):
        specs = [
                (
                'http://foo.com/index.html',
                'http://foo.com',
                'index should be stripped'
                ),
                (
                'http://foo.com/path/to/index.html',
                'http://foo.com/path/to',
                'index should be stripped'
                )
                ]
        self._run_urls(specs)

    def test_short(self):
        specs = [
                (
                'http://foo.com/en/1234567890',
                'http://foo.com/1234567890',
                'short segment should be stripped'
                ),
                (
                'http://foo.com/en/de/1234567890',
                'http://foo.com/en/1234567890',
                'short segment should be stripped'
                )
                ]
        self._run_urls(specs)

class TestFindNextPageLink(unittest.TestCase):

    def _test_page(self, url, html_path, expected):
        with open(html_path, 'r') as f:
            html = f.read()
        doc = parse(html, url)
        parsed_urls = {url}
        actual = find_next_page_link(parsed_urls, url, doc)
        self.assertEqual(expected, actual)

    def test_basic(self):
        self._test_page(
                'http://basic.com/article.html',
                'test_data/basic-multi-page.html',
                'http://basic.com/article.html?pagewanted=2'
                )

    def test_nytimes(self):
        # This better work for the New York Times.
        self._test_page(
                'http://www.nytimes.com/2011/07/10/magazine/the-dark-art-of-breaking-bad.html',
                'test_data/nytimes-next-page.html',
                'http://www.nytimes.com/2011/07/10/magazine/the-dark-art-of-breaking-bad.html?pagewanted=2&_r=1'
                )

class TestMultiPage(unittest.TestCase):
    '''
    Tests the full path of generating a readable page for a multi-page article.
    The test article is very simple, so this test should be resilient to tweaks
    of the algorithm.
    '''

    def _make_basic_urldict(self):
        url_fmt = 'http://basic.com/article.html?pagewanted=%s'
        file_fmt = 'test_data/basic-multi-page-%s.html'
        pairs = [(url_fmt % i, file_fmt % i) for i in ['2', '3']]
        return dict(pairs)

    def test_basic(self):
        with open('test_data/basic-multi-page.html', 'r') as f:
            html = f.read()
        urldict = self._make_basic_urldict()
        fetcher = urlfetch.MockUrlFetch(urldict)
        options = {
                'url': 'http://basic.com/article.html',
                'urlfetch': fetcher
                }
        doc = Document(html, **options)
        summary = doc.summary()

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
    if len(sys.argv) == 2 and sys.argv[1] == 'test':
        del sys.argv[1]
        unittest.main()
    else:
        readability_main()

if __name__ == '__main__':
    main()
