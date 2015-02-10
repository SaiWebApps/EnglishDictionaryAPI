# Python English Dictionary API

<h2>High-Level Overview</h2>
For any given English word, this API provides callers with the ability to fetch the definitions, origins, synonyms, antonyms, other word-relations, and rhyming words. Since the API uses Merriam-Webster and Thesaurus.com as the primary source of information, please note that the word must be a valid entry in both websites.

<h2> Dependencies </h2>
- lxml and requests: See <a href="http://docs.python-guide.org/en/latest/scenarios/scrape/">http://docs.python-guide.org/en/latest/scenarios/scrape/</a> for an introduction. According to the cited source, requests + lxml are more efficient than the in-built urllib2 module, which is why I used these libraries.
- merriam-webster.com
- thesaurus.com
