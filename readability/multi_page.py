"""
This module implements multi-page article handling.
"""

from htmls import clean, parse, tags
from lxml.html import fragment_fromstring
from lxml.etree import tostring
from regexes import REGEXES
import logging
import re
import urlparse

# The maximum number of pages that we will append.  There are cases where the
# algorithm incorrectly identifies next page links that would lead it to crawl
# many, many, many pages.
MAX_PAGES = 10

# Each page is added as a separate div to the article document.  This is the
# class used for each of those divs.
PAGE_CLASS = 'article-page'

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
    EW-CMS specific segment cleaning.
    
    Quoth the original source:

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
    Cleans a single segment of a URL in finding the base URL.
    
    The base URL is used as a reference when evaluating URLs that might be
    next-page links.  This is done by evaluating each path segment of the
    original URL.  This function returns a cleaned segment string or None, if
    the segment should be omitted entirely from the base URL.
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
        logging.debug('link with no href')
        return None, None, False

    logging.debug('evaluating href: %s' % raw_href)
    href = strip_trailing_slash(raw_href)
        
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
        logging.debug('rejecting: href not ok')
        return

    link_text, ok = eval_link_text(link)
    if not ok:
        logging.debug('rejecting: link text not ok')
        return

    # If the leftovers of the URL after removing the base URL don't contain any
    # digits, it's certainly not a next page link.
    if base_url is not None:
        href_leftover = href.replace(base_url, '')
        if not re.search(r'\d', href_leftover):
            logging.debug('rejecting: no digits')
            return

    candidate, created = find_or_create_page_candidate(
            candidates,
            href,
            link_text
            )

    if not created:
        logging.debug('found existing with score %d' % candidate.score)
        candidate.link_text += ' | ' + link_text

    link_class_name = link.get('class') or ''
    link_id = link.get('id') or ''
    link_data = ' '.join([link_text, link_class_name, link_id])
    logging.debug('link_data: %s' % link_data)

    if base_url is not None and href.find(base_url) != 0:
        logging.debug('no base_url (%s, %s)' % (base_url, href))
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
        logging.debug('link: %s' % tostring(link))
        eval_possible_next_page_link(
                parsed_urls,
                url,
                base_url,
                candidates,
                link
                )
    top_candidate = None
    for url, candidate in candidates.items():
        score = candidate.score
        logging.debug('next page score of %s: %s' % (url, candidate.score))
        if 50 <= score and (not top_candidate or top_candidate.score < score):
            top_candidate = candidate

    if top_candidate:
        logging.debug('next page link found: %s' % top_candidate.href)
        parsed_urls.add(top_candidate.href)
        return top_candidate.href
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

def append_next_page(
        get_article_func,
        parsed_urls,
        page_index,
        page_url,
        doc,
        options
        ):
    logging.debug('appending next page: %s' % page_url)

    if page_index >= MAX_PAGES:
        return

    fetcher = options['urlfetch']
    try:
        html = fetcher.urlread(page_url)
    except Exception as e:
        logging.warning('exception fetching %s' % page_url, exc_info = True)
        return
    orig_page_doc = parse(html, page_url)
    next_page_url = find_next_page_url(parsed_urls, page_url, orig_page_doc)
    page_article = get_article_func(orig_page_doc, options)
    page_doc = fragment_fromstring(page_article.html)
    make_page_elem(page_index, page_doc)
    if not is_suspected_duplicate(doc, page_doc):
        doc.append(page_doc)
        if next_page_url is not None:
            append_next_page(
                    get_article_func,
                    parsed_urls,
                    page_index + 1,
                    next_page_url,
                    doc,
                    options
                    )
