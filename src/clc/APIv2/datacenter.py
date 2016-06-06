"""
Datacenter related functions.

These datacenter related functions generally align one-for-one with published API calls categorized in the account category

API v2 - https://t3n.zendesk.com/forums/21613140-Datacenters

Datacenter object variables:

	datacenter.id (alias for location)
	datacenter.name
	datacenter.location
	datacenter.supports_premium_storage
	datacenter.supports_shared_load_balancer

"""

# TODO - init link to billing, statistics, scheduled activities
# TODO - accounts link?

import re
import clc

class Datacenter:

	@staticmethod
	def Datacenters(alias=None, token=None):
		"""Return all cloud locations available to the calling alias.

		>>> clc.v2.Datacenter.Datacenters(alias=None)
		[<clc.APIv2.datacenter.Datacenter instance at 0x101462fc8>, <clc.APIv2.datacenter.Datacenter instance at 0x101464320>]

		"""
		if not alias:  alias = clc.v2.Account.GetAlias()

		datacenters = []
		for r in clc.v2.API.Call('GET','datacenters/%s' % alias, {}, token=self.token):
			datacenters.append(Datacenter(location=r['id'], name=r['name'], alias=alias, token=self.token))

		return datacenters


	def __init__(self, location=None, name=None, alias=None, token=None):
		"""Create Datacenter object.

		If parameters are populated then create object location.
		Else if only id is supplied issue a Get Policy call

		https://t3n.zendesk.com/entries/31026420-Get-Data-Center-Group

		"""

		self.deployment_capabilities = None
		self.token = token
		self.alias = alias if alias else clc.v2.Account.GetAlias()
		self.location = location if location else clc.v2.Account.GetLocation()

		r = clc.v2.API.Call('GET', 'datacenters/%s/%s' % (self.alias, self.location), {'GroupLinks': 'true'}, token=self.token)
		self.id = self.location
		self.name = r['name']
		self.root_group_id = [obj['id'] for obj in r['links'] if obj['rel'] == "group"][0]
		self.root_group_name = [obj['name'] for obj in r['links'] if obj['rel'] == "group"][0]


	def RootGroup(self):
		"""Returns group object for datacenter root group.

		>>> clc.v2.Datacenter().RootGroup()
		<clc.APIv2.group.Group object at 0x105feacd0>
		>>> print _
		WA1 Hardware

		"""

		return clc.v2.Group(id=self.root_group_id, alias=self.alias, token=self.token)


	def Groups(self):
		"""Returns groups object rooted at this datacenter.

		>>> wa1 = clc.v2.Datacenter.Datacenters()[0]
		>>> wa1.Groups()
		<clc.APIv2.group.Groups object at 0x10144f290>

		"""

		return self.RootGroup().Subgroups()


	def _DeploymentCapabilities(self, cached=True):
		if not self.deployment_capabilities or not cached:
			self.deployment_capabilities = clc.v2.API.Call(
				'GET',
				'datacenters/%s/%s/deploymentCapabilities' % (self.alias, self.location),
				token=self.token)

		return self.deployment_capabilities


	def Networks(self, forced_load=False):
		if forced_load:
			return clc.v2.Networks(alias=self.alias, location=self.location, token=self.token)
		else:
			return clc.v2.Networks(networks_lst=self._DeploymentCapabilities()['deployableNetworks'], token=self.token)


	def Templates(self):
		return clc.v2.Templates(templates_lst=self._DeploymentCapabilities()['templates'], token=self.token)


	def __getattr__(self, var):
		key = re.sub("_(.)", lambda pat: pat.group(1).upper(), var)

		if key in ("supportsPremiumStorage", "supportsSharedLoadBalancer"):
			return self._DeploymentCapabilities()[key]

		raise AttributeError("'%s' instance has no attribute '%s'" % (self.__class__.__name__,var))


	def __str__(self):
		return(self.location)
