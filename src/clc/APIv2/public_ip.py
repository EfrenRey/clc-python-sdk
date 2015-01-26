"""
PublicIP related functions.  

PublicIPs object variables:

	public_ips.public_ips - list of PublicIP objects

PublicIP object variables:

	public_ip.id - alias of public
	public_ip.public
	public_ip.internal
	public_ip.ports - list of port/protocol dicts

"""

# vCur:
# TODO - ports
# TODO - sourcerestriction
# TODO - Update public IP

# vNext:
# TODO - PublicIPs search by port and source restriction
# TODO - Access PublicIPs by index - map directly to public_ips.public_ipds list


import re
import time
import json
import clc


class PublicIPs(object):

	def __init__(self,server,public_ips_lst):
		self.server = server
		self.public_ips = []
		for public_ip in public_ips_lst:
			if 'public' in public_ip:  self.public_ips.append(PublicIP(id=public_ip['public'],parent=self,public_ip_obj=public_ip))


	def Get(self,key):
		"""Get public_ip by providing either the public or the internal IP address."""

		for public_ip in self.public_ips:
			if public_ip.id == key:  return(public_ip)
			elif key == public_ip.internal:  return(public_ip)


	def Add(self,ports,source_restrictions=None,private_ip=None):
		"""Add new public_ip.

		Specify one or more ports using a list of dicts with the following keys:

			protocol - TCP, UDP, or ICMP
			port - int 0-65534
			port_to - (optional) if specifying a range of ports then the rqange end.  int 0-65534
		
		Optionally specify one or more source restrictions using a list of dicts with the following keys:

			cidr - string with CIDR notation for the subnet (e.g. "132.200.20.0/24")

		private_ip is the existing private IP address to NAT to (optional)

		# New public IP with single port
		>>> p = clc.v2.Server(alias='BTDI',id='WA1BTDIX03').PublicIPs()
		>>> p.Add(ports=[{"protocol": "TCP","port":5}]).WaitUntilComplete()
		0

		# New public IP with port range
		>>> p.Add([{"protocol": "UDP","port":10,"port_to":50}]).WaitUntilComplete()
		0

		# Map existing private IP to single port
		>>> p.Add(ports=[{"protocol": "TCP","port":22}],k
		          source_restrictions=[{'cidr': "132.200.20.0/24"}],
				  private_ip="10.80.148.13").WaitUntilComplete()
		0

		* Note this API is subject to revision to make ports and source restrictions access to parallel
		  that used for accessors.

		"""

		payload = {'ports': []}
		for port in ports:
			if 'port_to' in port:  payload['ports'].append({'protocol':port['protocol'], 'port':port['port'], 'portTo':port['port_to']})
			else:  payload['ports'].append({'protocol':port['protocol'], 'port':port['port']})
		if source_restrictions:  payload['sourceRestrictions'] = source_restrictions
		if private_ip:  payload['internalIPAddress'] = private_ip

		return(clc.v2.Requests(clc.v2.API.Call('POST','servers/%s/%s/publicIPAddresses' % (self.server.alias,self.server.id),json.dumps(payload))))



class PublicIP(object):

	def __init__(self,id,parent,public_ip_obj=None):
		"""Create PublicIP object."""

		self.id = id
		self.internal = public_ip_obj['internal']
		self.parent = parent
		self.data = None
		self.source_restrictions = None


	def _Load(self,cached=True):
		"""Performs a full load of all PublicIP metadata."""

		if not self.data or not cached:  
			self.data = clc.v2.API.Call('GET','servers/%s/%s/publicIPAddresses/%s' % (self.parent.server.alias,self.parent.server.id,self.id))

			# build ports
			self.data['_ports'] = self.data['ports']
			self.data['ports'] = []
			for port in self.data['_ports']:  
				if 'portTo' in port:  self.ports.append(Port(port['protocol'],port['port'],port['portTo']))
				else:  self.ports.append(Port(port['protocol'],port['port']))

			# build source restriction

		return(self.data)


	def Delete(self):
		"""Delete public IP.  

		>>> clc.v2.Server("WA1BTDIX01").PublicIPs().public_ips[0].Delete().WaitUntilComplete()
		0

		"""

		public_ip_set = [{'public_ipId': o.id, 'sizeGB': o.size} for o in self.parent.public_ips if o!=self]
		self.parent.public_ips = [o for o in self.parent.public_ips if o!=self]
		return(clc.v2.Requests(clc.v2.API.Call('DELETE','servers/%s/%s/publicIPAddresses/%s' % (self.parent.server.alias,self.parent.server.id,self.id))))


	def AddPort(self,protocol,port,port_to=None):  
		self.ports.append(Port(self,protocol,port,port_to))


	def AddPorts(self,protocol,port,port_to=None):  
		for port in ports:  
			if 'port_to' in port:  self.AddPort(Port(port['protocol'],port['port'],port['port_to']))
			else:  self.AddPort(Port(port['protocol'],port['port']))


	#def SourceRestrictions(self):
	#	if 


	def __getattr__(self,var):
		if var[0] != "_": key = re.sub("_(.)",lambda pat: pat.group(1).upper(),var)
		else:  key = var

		if not self.data:  self._Load()

		if key in self.data:  return(self.data[key])
		else:  raise(AttributeError("'%s' instance has no attribute '%s'" % (self.__class__.__name__,key)))


	def __str__(self):
		return(self.id)



class Port(object):

	def __init__(self,public_ip,protocol,port,port_to=None):
		self.public_ip = public_ip
		self.protocol = protocol
		self.port = port
		self.port_to = port_to


	def Delete(self):
		self.public_ip.ports = [o for o in self.public_ip.ports if o!=self]
		self.public_ip.Update()


	def ToDict(self):
		d = {'protocol': self.protocol,'port': self.port}
		if self.port_to:  d['portTo'] = self.port_to

		return(d)


	def __str__(self):
		if self.port_to:  return("%s-%s/%s" % (self.port,self.port_to,self.protocol))
		else:  return("%s/%s" % (self.port,self.protocol))

