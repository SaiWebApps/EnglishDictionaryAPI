#!/usr/bin/python

import blockspring
from lxml import html
import re
import requests

def _trim(text):
	''' 
		Return a version of text that does not contain any leading/trailing
		whitespace or raw unicode characters (\x80 - \xff).
	'''
	text = re.sub(u'[\x80-\xff]', '', text)
	alpha_only = re.sub('\W', '', text)
	return text.strip() if alpha_only else str()


# BEGIN HTML PARSER HELPER FUNCTIONS

# All of these helpers take in a tree as an argument. This tree contains the
# parsed results of a Merriam-Webster page for a certain word.
# They are all invoked by get_info(word), which synthesizes their results into
# a single dictionary of word information.
def _get_definitions(tree):
	'''
		Return the list of word definitions using the info in "tree."
		The final results will not contain any of the intermediate results' raw 
		unicode characters.
	'''
	XPATH = '//span[@class="ssens"]'
	definitions = tree.xpath(XPATH + '/text()') + tree.xpath(XPATH + '/a/text()')
	# Filtering out leading/trailing whitespace + raw unicode characters
	return [_trim(elem) for elem in definitions if _trim(elem)]


def _get_rhyming_words(tree):
	XPATH = '//div[@class="rhyming-dictionary"]/div[@id="rhm-content"]/a/text()'
	return [_trim(elem) for elem in tree.xpath(XPATH) if _trim(elem)]


def _get_synonyms(tree):
	XPATH = '//div[@class="synonyms-reference"]/div/dl/dd/a/text()'
	return [_trim(elem) for elem in tree.xpath(XPATH) if _trim(elem)]


def _get_related_words(tree):
	XPATH = '//div[@id="related-to-more"]/dl/dd/a/text()'
	return [_trim(elem) for elem in tree.xpath(XPATH) if _trim(elem)]


def _get_origin(tree):
	'''
		Return a dictionary with the year in which the word was first used and
		a broader description of its origins.
	'''
	# Some words use XPATH1 to segway into the origins section, but some use
	# XPATH2 instead. We will need to account for both.
	XPATH1 = '//div[@class="etymology"]/div//text()'
	XPATH2 = '//div[@class="first-use"]/div/text()'
	DATE_PREFIX = 'First Known Use:' # prefixes date/year in XPATH1
	
	initial = tree.xpath(XPATH1)
	alternate = tree.xpath(XPATH2)
	# Usual processing
	origin = [_trim(elem) for elem in initial + alternate if _trim(elem)]
	origin_results = {'origin_date': set(), 'origin_description': set()}

	for detail in origin:
		# Date if prefixed by 'First Known Use:' (XPATH1) or if value is
		# in XPATH2's results
		if DATE_PREFIX in detail or detail in alternate:
			origin_results['origin_date'].add(detail.strip(DATE_PREFIX))
		# If not date, then origin textual description
		else:
			origin_results['origin_description'].add(detail)

	return origin_results

# END HTML PARSER HELPER FUNCTIONS


# BEGIN RETRIEVAL AND INTEGRATION HELPER FUNCTIONS

def _get_info_from_merriam_webster(request):
	'''
		Return a dict with details about the given word, provided helpfully by
		Merriam-Webster. "request" might also contain "exclude_*" flags, which
        specify what details to return and what to exclude.
	'''
	# Retrieve page's HTML and store in tree for parsing.
	word = request.params['word']
	url = ''.join(['http://www.merriam-webster.com/dictionary/', word])
	page = requests.get(url)
	tree = html.fromstring(page.text)

	# Parse and assemble results in dict. Add the word attribute/detail
    # only if the user has not asked us to exclude it.
	mw_info = {}
	if not request.params.get('exclude_definition', None):
		mw_info['definition'] = _get_definitions(tree)
	if not request.params.get('exclude_synonyms', None):
		mw_info['synonyms'] = _get_synonyms(tree)
	if not request.params.get('exclude_related_words', None):
		mw_info['related_words'] = _get_related_words(tree)
	if not request.params.get('exclude_rhyming_words', None):
		mw_info['rhyming_words'] = _get_rhyming_words(tree)
        
    # If the user wants either the origin date or the origin description,
    # then invoke _get_origin, and add the requested word detail/attribute
    # to mw_info.
	exclude_origin_date = request.params.get('exclude_origin_date', None)
	exclude_origin_descr = request.params.get('exclude_origin_description', None)
	if not exclude_origin_descr or not exclude_origin_date:
		origin_info = _get_origin(tree)
		if not exclude_origin_descr:
			mw_info['origin_description'] = list(origin_info['origin_description'])
		if not exclude_origin_date:
			mw_info['origin_date'] = list(origin_info['origin_date'])
            
	return mw_info


def _add_antonyms_from_thesaurus_com(request, word_info_map):
	'''
		Given a word_info_map with the Merriam-Webster results for word, fetch the
		word's antonyms from thesaurus.com and add to word_info_map.
		Note that we couldn't do this in _get_info_from_merriam_webster since Merriam-
		Webster does not provide antonyms on the same page w/ the other info. Also,
		thesaurus.com appears to have a more detailed list of antonyms.
	'''
    # If user has requested us to exclude antonyms from results, stop now.
	if request.params.get('exclude_antonyms', None):
		return
    
	# Otherwise, get antonyms from thesaurus.com, and add them to "word_info_map".
	word = request.params['word']
	XPATH = '//section[@class="container-info antonyms"]/div[@class="list-holder"]/ul \
			/li/a/span[@class="text"]/text()'
	url = ''.join(['http://www.thesaurus.com/browse/', word])
	page = requests.get(url)
	tree = html.fromstring(page.text)
	word_info_map['antonyms'] = tree.xpath(XPATH)

# END RETRIEVAL AND INTEGRATION HELPER FUNCTIONS


# BEGIN CLIENT-FACING (API) FUNCTIONS

def	block(request, response):
	'''
		Write information about the specified word (provided in "request")
		to "response." "request" may also contain filters that specify which
		information should/should not be included in the "response."
	'''
	# Collect all of the information for the specified word.
	word_info = _get_info_from_merriam_webster(request)
	_add_antonyms_from_thesaurus_com(request, word_info)

	response.addOutput('Information About ' + request.params['word'], word_info)
	response.end()

blockspring.define(block)

# END CLIENT-FACING (API) FUNCTIONS

