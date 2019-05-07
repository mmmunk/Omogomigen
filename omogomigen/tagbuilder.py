# Tag Builder, Copyright (C) Thomas Munk, Version 0.8.0 - 2019-03-22
# This file contains free software released into the public domain.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

def escape_tag_str(s):
	s = str(s)
	for c in s:
		if c in '&<>':
			return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
	return s


class Tag:

	def __init__(self, tagname, tagcontent=None, **kwargs):
		self.name = tagname
		self.content = []
		self.add(tagcontent)
		self.attributes = []
		for k, v in kwargs.items():
			if k.endswith('_'):
				k = k[:-1]
			if v in (False, None):
				continue
			elif v == True and type(v) == bool:
				self.attributes.append(k)
			else:
				self.attributes.append('%s="%s"' % (k, str(v).replace('"', '&quot;')))

	def add(self, tagcontent):
		if isinstance(tagcontent, (list, tuple)):
			for item in tagcontent:
				self.add(item)
		else:
			if tagcontent != None:
				self.content.append(tagcontent)

	def render(self, output, preamble=None):
		if preamble:
			output(preamble)
		output('<')
		output(self.name)
		for item in self.attributes:
			output(' ')
			output(item)
		if len(self.content) > 0:
			output('>')
			for item in self.content:
				if isinstance(item, Tag):
					item.render(output)
				else:
					if isinstance(self, TagE):
						output(escape_tag_str(item))
					else:
						output(str(item))
			output('</')
			output(self.name)
			output('>')
		else:
			output('/>')


class TagE(Tag):
	pass
