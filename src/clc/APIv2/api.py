# -*- coding: utf-8 -*-
"""Private class that executes API calls."""

import requests
import xml.etree.ElementTree
import clc
import os
import sys


class API():
	
	# requests module includes cacert.pem which is visible when run as installed module.
	# pyinstall single-file deployment needs cacert.pem packaged along and referenced.
	# This module proxies between the two based on whether the cacert.pem exists in
	# the expected runtime directory.
	#
	# https://github.com/kennethreitz/requests/issues/557
	# http://stackoverflow.com/questions/7674790/bundling-data-files-with-pyinstaller-onefile
	#
	@staticmethod
	def _ResourcePath(relative):
		if os.path.isfile(os.path.join(getattr(sys, '_MEIPASS', os.path.abspath(".")),relative)):
			# Pyinstall packaged windows file
			return(os.path.join(getattr(sys, '_MEIPASS', os.path.abspath(".")),relative))
		else:
			return(True)


	@staticmethod
	def _DebugRequest(request,response):
		print('{}\n{}\n{}\n\n{}\n'.format(
			'-----------REQUEST-----------',
			request.method + ' ' + request.url,
			'\n'.join('{}: {}'.format(k, v) for k, v in request.headers.items()),
			request.body,
		))

		print('{}\n{}\n\n{}'.format(
			'-----------RESPONSE-----------',
			'status: ' + str(response.status_code),
			response.text
		))


	@staticmethod
	def _Login():
		"""Login to retrieve bearer token and set default accoutn and location aliases."""
		if not clc.v2.V2_API_USERNAME or not clc.v2.V2_API_PASSWD:
			clc.v1.output.Status('ERROR',3,'V2 API username and password not provided')
			raise(clc.APIV2NotEnabled)
			
		r = requests.post("%s%s" % (clc.defaults.ENDPOINT_URL_V2,"authentication/login"), 
						  data={"username": clc.v2.V2_API_USERNAME, "password": clc.v2.V2_API_PASSWD},
						  verify=API._ResourcePath('clc/cacert.pem'))

		if r.status_code == 200:
			clc._LOGIN_TOKEN_V2 = r.json()['bearerToken']
			clc.ALIAS = r.json()['accountAlias']
			clc.LOCATION = r.json()['locationAlias']
		elif r.status_code == 400:
			raise(Exception("Invalid V2 API login.  %s" % (r.json()['message'])))
		else:
			raise(Exception("Error logging into V2 API.  Response code %s. message %s" % (r.status_code,r.json()['message'])))


	@staticmethod
	def Call(method,url,payload={},debug=False):
		"""Execute v2 API call.

		:param url: URL paths associated with the API call
		:param payload: dict containing all parameters to submit with POST call

		:returns: decoded API json result
		"""
		if not clc._LOGIN_TOKEN_V2:  API._Login()

		# If executing refs provided in API they are abs paths,
		# Else refs we build in the sdk are relative
		if url[0]=='/':  "%s%s" % (clc.defaults.ENDPOINT_URL_V2,url)
		else:  "%s/v2/%s" % (clc.defaults.ENDPOINT_URL_V2,url)

		headers = {'Authorization': "Bearer %s" % clc._LOGIN_TOKEN_V2}
		if type(payload) is str:  headers['content-type'] = "Application/json" # added for server ops with str payload

		if method=="GET":
			r = requests.request(method,"%s%s" % (clc.defaults.ENDPOINT_URL_V2,url), 
								 headers=headers,
			                     params=payload, 
								 verify=API._ResourcePath('clc/cacert.pem'))
		else:
			r = requests.request(method,"%s%s" % (clc.defaults.ENDPOINT_URL_V2,url), 
								 headers=headers,
			                     data=payload, 
								 verify=API._ResourcePath('clc/cacert.pem'))

		if debug:  
			API._DebugRequest(request=requests.Request(method,"%s%s" % (clc.defaults.ENDPOINT_URL_V2,url),data=payload,
			                                           headers={'Authorization': "Bearer %s" % clc._LOGIN_TOKEN_V2}).prepare(),
			                  response=r)

		if r.status_code>=200 and r.status_code<300:
			try:
				return(r.json())
			except:
				return({})
		else:
			try:
				e = clc.APIFailedResponse("Response code %s.  %s. %s %s" % 
				                          (r.status_code,r.json()['message'],method,"%s%s" % (clc.defaults.ENDPOINT_URL_V2,url)))
				e.response_status_code = r.status_code
				e.response_json = r.json()
				e.response_text = r.text
				raise(e)
			except clc.APIFailedResponse:
				pass
			except:
				e = clc.APIFailedResponse("Response code %s. %s. %s %s" % 
				                         (r.status_code,r.text,method,"%s%s" % (clc.defaults.ENDPOINT_URL_V2,url)))
				e.response_status_code = r.status_code
				e.response_json = {}	# or should this be None?
				e.response_text = r.text
				raise(e)


