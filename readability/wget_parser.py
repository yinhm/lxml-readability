import logging
import re
import sys
import unittest

WGET_URL_RE = re.compile(r'--\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}--  (.*)')
WGET_RESULT_RE = re.compile(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} (.*)')
WGET_SUCCESS_RE = re.compile(r'\(.+\) - \xe2\x80\x9c(.*)\xe2\x80\x9d')

class WgetParser():

    START, FETCHING = range(2)

    def __init__(self, url_map):
        self._url_map = url_map
        self._state = self.START
        self._current_urls = []
        self._handlers = {
                self.START: self._process_start,
                self.FETCHING: self._process_fetching
                }

    def _process_start(self, line):
        logging.debug('_process_start(%s)' % line)
        url_match = WGET_URL_RE.match(line)
        if url_match is not None:
            self._current_urls.append(url_match.group(1))
            self._state = self.FETCHING
            return

        result_match = WGET_RESULT_RE.match(line)
        if result_match is not None:
            raise Exception('unexpected result line: %s' % line)
    
    def _process_fetching(self, line):
        logging.debug('_process_fetching(%s)' % line)
        result_match = WGET_RESULT_RE.match(line)
        if result_match is not None:
            result = result_match.group(1)
            logging.debug('  result: %s' % result)
            success_match = WGET_SUCCESS_RE.match(result)
            if success_match is not None:
                logging.debug('    success match')
                for url in self._current_urls:
                    self._url_map[url] = success_match.group(1)
            self._state = self.START
            del self._current_urls[:]

        url_match = WGET_URL_RE.match(line)
        if url_match is not None:
            self._current_urls.append(url_match.group(1))
            return

    def parse(self, wget_output):
        lines = wget_output.splitlines()
        for line in lines:
            self._handlers[self._state](line)

###############################################################################
#
# Unit Tests
#
###############################################################################
class TestUrlRe(unittest.TestCase):

    def test_positive(self):
        line = '--2011-07-29 10:02:51--  http://foo.com/bar/narf'
        match = WGET_URL_RE.match(line)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), 'http://foo.com/bar/narf')

    def test_negative(self):
        negatives = [
                'Reusing existing connection to static.arstechnica.net:80.',
                '2011-07-29 10:02:51 (446 KB/s) - \xe2\x80\x9cstatic.arstechnica.net/public/v6/styles/light/images/footer/footer-mobile-badge.png\xe2\x80\x9d saved [6635/6635]'
                ]
        for negative in negatives:
            match = WGET_URL_RE.match(negative)
            self.assertIsNone(match)

class TestResultRe(unittest.TestCase):

    def test_positive(self):
        positives = [
                (
                    '2011-07-29 10:02:51 (61.0 MB/s) - \xe2\x80\x9chttp://foo.com/bar/narf\xe2\x80\x9d saved [512/512]',
                    '(61.0 MB/s) - \xe2\x80\x9chttp://foo.com/bar/narf\xe2\x80\x9d saved [512/512]'
                ),
                (
                    '2011-07-29 10:02:51 ERROR 404: Not Found.',
                    'ERROR 404: Not Found.'
                )
                ]
        for line, status in positives:
            match = WGET_RESULT_RE.match(line)
            self.assertIsNotNone(match, line)
            self.assertEqual(match.group(1), status)

    def test_negative(self):
        negatives = [
                'Reusing existing connection to static.arstechnica.net:80.'
                'Resolving graphics8.nytimes.com (graphics8.nytimes.com)...  63.80.138.75, 63.80.138.64'
                ]
        for negative in negatives:
            match = WGET_RESULT_RE.match(negative)
            self.assertIsNone(match)

class TestSuccessRe(unittest.TestCase):

    def test_positive(self):
        positives = [
                (
                    '(61.0 MB/s) - \xe2\x80\x9chttp://foo.com/bar/narf\xe2\x80\x9d saved [512/512]',
                    'http://foo.com/bar/narf'
                ),
                (
                    '(395 KB/s) - \xe2\x80\x9chttp://foo.com/bar/narf\xe2\x80\x9d saved [512/512]',
                    'http://foo.com/bar/narf'
                )
                ]
        for line, url in positives:
            match = WGET_SUCCESS_RE.match(line)
            self.assertIsNotNone(match, line)
            self.assertEqual(match.group(1), url)

    def test_negative(self):
        negatives = [
                'ERROR 404: Not Found.'
                ]
        for negative in negatives:
            match = WGET_SUCCESS_RE.match(negative)
            self.assertIsNone(match)

class TestWgetParser(unittest.TestCase):

    EXPECTED_URL_MAP = {
            'http://ad.doubleclick.net/robots.txt': 'ad.doubleclick.net/robots.txt',
            'http://ads.pointroll.com/robots.txt': 'ads.pointroll.com/robots.txt',
            'http://graphics8.nytimes.com/ads/marketing/mm09/verticalst/nytimes.gif': 'graphics8.nytimes.com/ads/marketing/mm09/verticalst/nytimes.gif',
            'http://graphics8.nytimes.com/ads/marketing/mm09/verticalst/verticals_movies.gif': 'graphics8.nytimes.com/ads/marketing/mm09/verticalst/verticals_movies.gif',
            'http://graphics8.nytimes.com/ads/marketing/mm11/movies_072911.jpg': 'graphics8.nytimes.com/ads/marketing/mm11/movies_072911.jpg',
            'http://graphics8.nytimes.com/adx/images/ADS/24/26/ad.242614/90x79_newspaper.gif': 'graphics8.nytimes.com/adx/images/ADS/24/26/ad.242614/90x79_newspaper.gif',
            'http://graphics8.nytimes.com/adx/images/ADS/26/68/ad.266879/120x60_10k.gif': 'graphics8.nytimes.com/adx/images/ADS/26/68/ad.266879/120x60_10k.gif',
            'http://graphics8.nytimes.com/adx/images/ADS/27/09/ad.270928/11-0922_HDGenericD2_336x79.jpg': 'graphics8.nytimes.com/adx/images/ADS/27/09/ad.270928/11-0922_HDGenericD2_336x79.jpg',
            'http://graphics8.nytimes.com/adx/images/ADS/27/14/ad.271444/11-0220_AudienceDev_86x60_farm.jpg': 'graphics8.nytimes.com/adx/images/ADS/27/14/ad.271444/11-0220_AudienceDev_86x60_farm.jpg',
            'http://graphics8.nytimes.com/css/0.1/screen/article/abstract.css': 'graphics8.nytimes.com/css/0.1/screen/article/abstract.css',
            'http://graphics8.nytimes.com/css/0.1/screen/article/upnext.css': 'graphics8.nytimes.com/css/0.1/screen/article/upnext.css',
            'http://graphics8.nytimes.com/css/0.1/screen/build/article/2.0/styles.css': 'graphics8.nytimes.com/css/0.1/screen/build/article/2.0/styles.css',
            'http://graphics8.nytimes.com/css/0.1/screen/common/ads.css': 'graphics8.nytimes.com/css/0.1/screen/common/ads.css',
            'http://graphics8.nytimes.com/css/0.1/screen/common/article.css': 'graphics8.nytimes.com/css/0.1/screen/common/article.css',
            'http://graphics8.nytimes.com/css/0.1/screen/common/global.css': 'graphics8.nytimes.com/css/0.1/screen/common/global.css',
            'http://graphics8.nytimes.com/css/0.1/screen/common/googleads.css': 'graphics8.nytimes.com/css/0.1/screen/common/googleads.css',
            'http://graphics8.nytimes.com/css/0.1/screen/common/insideNYTimes.css': 'graphics8.nytimes.com/css/0.1/screen/common/insideNYTimes.css',
            'http://graphics8.nytimes.com/css/0.1/screen/common/layout.css': 'graphics8.nytimes.com/css/0.1/screen/common/layout.css',
            'http://graphics8.nytimes.com/css/0.1/screen/common/macros.css': 'graphics8.nytimes.com/css/0.1/screen/common/macros.css',
            'http://graphics8.nytimes.com/css/0.1/screen/common/masthead.css': 'graphics8.nytimes.com/css/0.1/screen/common/masthead.css',
            'http://graphics8.nytimes.com/css/0.1/screen/common/modules.css': 'graphics8.nytimes.com/css/0.1/screen/common/modules.css',
            'http://graphics8.nytimes.com/css/0.1/screen/common/modules/articletools.css': 'graphics8.nytimes.com/css/0.1/screen/common/modules/articletools.css',
            'http://graphics8.nytimes.com/css/0.1/screen/common/modules/readercomments.css': 'graphics8.nytimes.com/css/0.1/screen/common/modules/readercomments.css',
            'http://graphics8.nytimes.com/css/0.1/screen/common/modules/sharetools.css': 'graphics8.nytimes.com/css/0.1/screen/common/modules/sharetools.css',
            'http://graphics8.nytimes.com/css/0.1/screen/common/mostpopular.css': 'graphics8.nytimes.com/css/0.1/screen/common/mostpopular.css',
            'http://graphics8.nytimes.com/css/0.1/screen/common/navigation.css': 'graphics8.nytimes.com/css/0.1/screen/common/navigation.css',
            'http://graphics8.nytimes.com/css/0.1/screen/common/shell.css': 'graphics8.nytimes.com/css/0.1/screen/common/shell.css',
            'http://graphics8.nytimes.com/css/0.1/screen/section/travel/modules/expedia.css': 'graphics8.nytimes.com/css/0.1/screen/section/travel/modules/expedia.css',
            'http://graphics8.nytimes.com/css/common/global.css': 'graphics8.nytimes.com/css/common/global.css',
            'http://graphics8.nytimes.com/css/standalone/regilite/screen/regiLite.css': 'graphics8.nytimes.com/css/standalone/regilite/screen/regiLite.css',
            'http://graphics8.nytimes.com/images/2011/07/10/magazine/10bad1/mag-10Bad-t_CA1-articleInline.jpg': 'graphics8.nytimes.com/images/2011/07/10/magazine/10bad1/mag-10Bad-t_CA1-articleInline.jpg',
            'http://graphics8.nytimes.com/images/2011/07/10/magazine/10bad2/10bad2-thumbWide.jpg': 'graphics8.nytimes.com/images/2011/07/10/magazine/10bad2/10bad2-thumbWide.jpg',
            'http://graphics8.nytimes.com/images/2011/07/10/magazine/10bad_span/10bad_span-articleLarge.jpg': 'graphics8.nytimes.com/images/2011/07/10/magazine/10bad_span/10bad_span-articleLarge.jpg',
            'http://graphics8.nytimes.com/images/global/buttons/go.gif': 'graphics8.nytimes.com/images/global/buttons/go.gif',
            'http://graphics8.nytimes.com/images/membercenter/icon_delivers.png': 'graphics8.nytimes.com/images/membercenter/icon_delivers.png',
            'http://graphics8.nytimes.com/images/membercenter/signup.png': 'graphics8.nytimes.com/images/membercenter/signup.png',
            'http://graphics8.nytimes.com/images/misc/nytlogo152x23.gif': 'graphics8.nytimes.com/images/misc/nytlogo152x23.gif',
            'http://graphics8.nytimes.com/js/app/analytics/trackingTags_v1.1.js': 'graphics8.nytimes.com/js/app/analytics/trackingTags_v1.1.js',
            'http://graphics8.nytimes.com/js/app/article/articleCommentCount.js': 'graphics8.nytimes.com/js/app/article/articleCommentCount.js',
            'http://graphics8.nytimes.com/js/app/article/outbrain.js': 'graphics8.nytimes.com/js/app/article/outbrain.js',
            'http://graphics8.nytimes.com/js/app/article/upNext.js': 'graphics8.nytimes.com/js/app/article/upNext.js',
            'http://graphics8.nytimes.com/js/app/recommendations/recommendationsModule.js': 'graphics8.nytimes.com/js/app/recommendations/recommendationsModule.js',
            'http://graphics8.nytimes.com/js/article/articleShare.js': 'graphics8.nytimes.com/js/article/articleShare.js',
            'http://graphics8.nytimes.com/js/article/comments/crnrXHR.js': 'graphics8.nytimes.com/js/article/comments/crnrXHR.js',
            'http://graphics8.nytimes.com/js/common.js': 'graphics8.nytimes.com/js/common.js',
            'http://graphics8.nytimes.com/js/common/screen/DropDown.js': 'graphics8.nytimes.com/js/common/screen/DropDown.js',
            'http://graphics8.nytimes.com/js/common/screen/altClickToSearch.js': 'graphics8.nytimes.com/js/common/screen/altClickToSearch.js',
            'http://graphics8.nytimes.com/js/util/tooltip.js': 'graphics8.nytimes.com/js/util/tooltip.js',
            'http://graphics8.nytimes.com/robots.txt': 'graphics8.nytimes.com/robots.txt.html',
            'http://i1.nyt.com/images/2011/07/29/arts/29MOTH_HALS/29MOTH_HALS-moth.jpg': 'i1.nyt.com/images/2011/07/29/arts/29MOTH_HALS/29MOTH_HALS-moth.jpg',
            'http://i1.nyt.com/images/2011/07/29/movies/29MOTH_COWBOY/29MOTH_COWBOY-moth.jpg': 'i1.nyt.com/images/2011/07/29/movies/29MOTH_COWBOY/29MOTH_COWBOY-moth.jpg',
            'http://i1.nyt.com/images/2011/07/29/opinion/29moth_opchart/29moth_opchart-moth.jpg': 'i1.nyt.com/images/2011/07/29/opinion/29moth_opchart/29moth_opchart-moth.jpg',
            'http://i1.nyt.com/images/2011/07/29/sports/29moth_basketball/29moth_basketball-moth.jpg': 'i1.nyt.com/images/2011/07/29/sports/29moth_basketball/29moth_basketball-moth.jpg',
            'http://i1.nyt.com/images/2011/07/29/world/29moth_baghdad/29moth_baghdad-moth.jpg': 'i1.nyt.com/images/2011/07/29/world/29moth_baghdad/29moth_baghdad-moth.jpg',
            'http://i1.nyt.com/images/global/buttons/moth_forward.gif': 'i1.nyt.com/images/global/buttons/moth_forward.gif',
            'http://i1.nyt.com/images/global/buttons/moth_reverse.gif': 'i1.nyt.com/images/global/buttons/moth_reverse.gif',
            'http://i1.nyt.com/robots.txt': 'i1.nyt.com/robots.txt.html',
            'http://js.nyt.com/js/app/moth/moth.js': 'js.nyt.com/js/app/moth/moth.js',
            'http://js.nyt.com/robots.txt': 'js.nyt.com/robots.txt.html',
            'http://up.nytimes.com/?d=0/15/&t=2&s=0&ui=0&r=&u=www%2enytimes%2ecom%2f2011%2f07%2f10%2fmagazine%2fthe%2ddark%2dart%2dof%2dbreaking%2dbad%2ehtml%3f%5fr%3d1': 'up.nytimes.com/index.html?d=0%2F15%2F&t=2&s=0&ui=0&r=&u=www.nytimes.com%2F2011%2F07%2F10%2Fmagazine%2Fthe-dark-art-of-breaking-bad.html?_r=1',
            'http://wt.o.nytimes.com/dcsym57yw10000s1s8g0boozt_9t1x/njs.gif?dcsredirect=126&dcstlh=0&dcstlv=0&dcsuri=/nojavascript&WT.js=No&WT.tv=1.0.7': 'wt.o.nytimes.com/dcsym57yw10000s1s8g0boozt_9t1x/njs.gif?dcsredirect=126&dcstlh=0&dcstlv=0&dcsuri=%2Fnojavascript&WT.js=No&WT.tv=1.0.7',
            'http://wt.o.nytimes.com/dcsym57yw10000s1s8g0boozt_9t1x/njs.gif?dcsuri=/nojavascript&WT.js=No&WT.tv=1.0.7': 'wt.o.nytimes.com/dcsym57yw10000s1s8g0boozt_9t1x/njs.gif?dcsredirect=126&dcstlh=0&dcstlv=0&dcsuri=%2Fnojavascript&WT.js=No&WT.tv=1.0.7',
            'http://www.nytimes.com/2011/07/10/magazine/the-dark-art-of-breaking-bad.html': 'www.nytimes.com/2011/07/10/magazine/the-dark-art-of-breaking-bad.html?_r=1.html',
            'http://www.nytimes.com/2011/07/10/magazine/the-dark-art-of-breaking-bad.html?_r=1': 'www.nytimes.com/2011/07/10/magazine/the-dark-art-of-breaking-bad.html?_r=1.html',
            'http://www.nytimes.com/glogin?URI=http://www.nytimes.com/2011/07/10/magazine/the-dark-art-of-breaking-bad.html&OQ=_rQ3D1&OP=6d0756d4Q2FQ20vEkQ20,(Q7BqQ3E((sQ2BQ20Q2B@Q3BQ3BQ20@jQ20Q3B@Q20a_c_-hQ24EQ20sQ23EY,_Q3EwY_Q3EsY(dYkQ3EE_whQ24cYk_,Q22Q23saQ7E': 'www.nytimes.com/2011/07/10/magazine/the-dark-art-of-breaking-bad.html?_r=1.html',
            'http://www.nytimes.com/gst/litesub_insert.html?product=LT&size=336X90': 'www.nytimes.com/gst/litesub_insert.html?product=LT&size=336X90.html',
            'http://www.nytimes.com/robots.txt': 'www.nytimes.com/robots.txt'
            }

    def test_parse(self):
        url_map = dict()
        parser = WgetParser(url_map)
        with open('test_data/nytimes-wget-log.txt', 'r') as f:
            wget_output = f.read()
        parser.parse(wget_output)
        self.assertEquals(url_map, self.EXPECTED_URL_MAP)

def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--debug':
        del sys.argv[1]
        logging.basicConfig(level = logging.DEBUG)
    else:
        logging.basicConfig(level = logging.INFO)
    unittest.main()

if __name__ == '__main__':
    main()
