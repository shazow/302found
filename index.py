from django.utils import simplejson

import logging

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

from google.appengine.api import urlfetch
from urllib import urlencode

API_URL = 'http://ajax.googleapis.com/ajax/services/search/web?v=1.0&%s'

# Redirect response stolen from Google
REDIRECT_TEMPLATE = """
<HTML><HEAD><meta http-equiv="content-type" content="text/html;charset=utf-8">
<TITLE>302 Moved</TITLE></HEAD><BODY>
<H1>302 Moved</H1>
The document has moved
<A HREF="%(redirect_to)s">here</A>.
</BODY></HTML>
""".strip()

INFO_TEMPLATE = """
<HTML><HEAD><meta http-equiv="content-type" content="text/html;charset=utf-8">
<TITLE>302Found - Simple Redirection</TITLE></HEAD><BODY>

<H1>Improved <EM>I'm Feeling Lucky</EM></H1>
<P>Query Google and redirect to the first result. Doesn't discriminate by the referrer, even when there's few results (unlike Google). If no results are found, <CODE>fallback</CODE> is used.</P>
<FORM METHOD="GET" ACTION="/">
    Query: <INPUT TYPE="text" NAME="q" /><BR />
    Fallback (Optional): <INPUT TYPE="text" NAME="fallback" /><BR />
    <INPUT TYPE="submit" value="I'm Feeling Lucky" />
</FORM>

<H1>URL Redirect</H1>
<P>Great for hiding the referrer.</P>
<FORM METHOD="GET" ACTION="/">
    URL: <INPUT TYPE="text" NAME="url"><BR />
    <INPUT TYPE="submit" value="Redirect" />
</FORM>

</BODY></HTML>
""".strip()

class Redirector(webapp.RequestHandler):
    def _first_google(self, q):
        "Query Google for ``q``, return the first result if there is one."
        params = {'q': q, 'rsz': 'small'}
        url = API_URL % urlencode(params)

        # Query Google
        response = urlfetch.fetch(url)
        if response.status_code != 200:
            logging.error("Google Query failed with code %d: %s" % (response.status_code, response.content))
            return

        # Parse response
        try:
            data = simplejson.loads(response.content)
            results = data['responseData']['results']

            if results:
                logging.info("Google returned %s results for: %s" % (data['responseData']['cursor'].get('estimatedResultCount'), q))
                return results[0]['unescapedUrl']

        except (ValueError, KeyError), e:
            logging.error("Couldn't parse Google response due to %r: %s" % (e, response.content))
            return

        logging.info("Google returned 0 results for: %s" % q)

    def get(self):
        fallback = self.request.get('fallback')
        q = self.request.get('q')
        url = self.request.get('url')

        if not any([q, url, fallback]):
            logging.info("Empty query, showing instructions.")
            self.response.out.write(INFO_TEMPLATE)
            return

        redirect_to = None
        if q:
            redirect_to = self._first_google(q)
        elif url:
            logging.info("Redirecting to URL: %s" % url)
            redirect_to = url

        if not redirect_to:
            # No redirect found, need to fall back to something...
            if fallback:
                redirect_to = fallback
            elif q:
                redirect_to = "http://www.google.com/search?q=%s" % q
            else:
                redirect_to = "/"
            logging.info("Falling back to: %s" % redirect_to)

        # Redirect...
        self.response.set_status(302)
        self.response.headers.add_header('Location', redirect_to)
        self.response.out.write(REDIRECT_TEMPLATE % {'redirect_to': redirect_to})

def main():
  logging.getLogger().setLevel(logging.DEBUG)
  application = webapp.WSGIApplication([('/', Redirector)], debug=True)
  run_wsgi_app(application)

if __name__ == "__main__":
  main()