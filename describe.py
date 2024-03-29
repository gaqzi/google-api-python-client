#!/usr/bin/env python
#
# Copyright 2012 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Create documentation for generate API surfaces.

Command-line tool that creates documentation for all APIs listed in discovery.
The documentation is generated from a combination of the discovery document and
the generated API surface itself.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'

import os
import re
import sys
import httplib2

from string import Template

from apiclient.discovery import build
from oauth2client.anyjson import simplejson
import uritemplate


BASE = 'docs/dyn'

CSS = """<style>

body, h1, h2, h3, div, span, p, pre, a {
  margin: 0;
  padding: 0;
  border: 0;
  font-weight: inherit;
  font-style: inherit;
  font-size: 100%;
  font-family: inherit;
  vertical-align: baseline;
}

body {
  font-size: 13px;
  padding: 1em;
}

h1 {
  font-size: 26px;
  margin-bottom: 1em;
}

h2 {
  font-size: 24px;
  margin-bottom: 1em;
}

h3 {
  font-size: 20px;
  margin-bottom: 1em;
  margin-top: 1em;
}

pre, code {
  line-height: 1.5;
  font-family: Monaco, 'DejaVu Sans Mono', 'Bitstream Vera Sans Mono', 'Lucida Console', monospace;
}

pre {
  margin-top: 0.5em;
}

h1, h2, h3, p {
  font-family: Arial, sans serif;
}

h1, h2, h3 {
  border-bottom: solid #CCC 1px;
}

.toc_element {
  margin-top: 0.5em;
}

.firstline {
  margin-left: 2 em;
}

.method  {
  margin-top: 1em;
  border: solid 1px #CCC;
  padding: 1em;
  background: #EEE;
}

.details {
  font-weight: bold;
  font-size: 14px;
}

</style>
"""

DISCOVERY_URI = ('https://www.googleapis.com/discovery/v1/apis/'
                 '{api}/{apiVersion}/rest')

METHOD_TEMPLATE = """<div class="method">
    <code class="details" id="$name">$name($params)</code>
  <pre>$doc</pre>
</div>
"""

COLLECTION_LINK = """<p class="toc_element">
  <code><a href="$href">$name()</a></code>
</p>
<p class="firstline">Returns the $name Resource.</p>
"""

METHOD_LINK = """<p class="toc_element">
  <code><a href="#$name">$name($params)</a></code></p>
<p class="firstline">$firstline</p>"""


def safe_version(version):
  """Create a safe version of the verion string.

  Needed so that we can distinguish between versions
  and sub-collections in URIs. I.e. we don't want
  adsense_v1.1 to refer to the '1' collection in the v1
  version of the adsense api.

  Args:
    version: string, The version string.
  Returns:
    The string with '.' replaced with '_'.
  """

  return version.replace('.', '_')


def unsafe_version(version):
  """Undoes what safe_version() does.

  See safe_version() for the details.


  Args:
    version: string, The safe version string.
  Returns:
    The string with '_' replaced with '.'.
  """

  return version.replace('_', '.')


def method_params(doc):
  """Document the parameters of a method.

  Args:
    doc: string, The method's docstring.

  Returns:
    The method signature as a string.
  """
  doclines = doc.splitlines()
  if 'Args:' in doclines:
    begin = doclines.index('Args:')
    if 'Returns:' in doclines[begin+1:]:
      end = doclines.index('Returns:', begin)
      args = doclines[begin+1: end]
    else:
      args = doclines[begin+1:]

    parameters = []
    for line in args:
      m = re.search('^\s+([a-zA-Z0-9_]+): (.*)', line)
      if m is None:
        continue
      pname = m.group(1)
      desc = m.group(2)
      if '(required)' not in desc:
        pname = pname + '=None'
      parameters.append(pname)
    parameters = ', '.join(parameters)
  else:
    parameters = ''
  return parameters


def method(name, doc):
  """Documents an individual method.

  Args:
    name: string, Name of the method.
    doc: string, The methods docstring.
  """

  params = method_params(doc)
  return Template(METHOD_TEMPLATE).substitute(name=name, params=params, doc=doc)


def breadcrumbs(path, root_discovery):
  """Create the breadcrumb trail to this page of documentation.

  Args:
    path: string, Dot separated name of the resource.
    root_discovery: Deserialized discovery document.

  Returns:
    HTML with links to each of the parent resources of this resource.
  """
  parts = path.split('.')

  crumbs = []
  accumulated = []

  for i, p in enumerate(parts):
    prefix = '.'.join(accumulated)
    # The first time through prefix will be [], so we avoid adding in a
    # superfluous '.' to prefix.
    if prefix:
      prefix += '.'
    display = p
    if i == 0:
      display = root_discovery.get('title', display)
    crumbs.append('<a href="%s.html">%s</a>' % (prefix + p, display))
    accumulated.append(p)

  return ' . '.join(crumbs)


def document_collection(resource, path, root_discovery, discovery, css=CSS):
  """Document a single collection in an API.

  Args:
    resource: Collection or service being documented.
    path: string, Dot separated name of the resource.
    root_discovery: Deserialized discovery document.
    discovery: Deserialized discovery document, but just the portion that
      describes the resource.
    css: string, The CSS to include in the generated file.
  """
  collections = []
  methods = []
  resource_name = path.split('.')[-2]
  html = [
      '<html><body>',
      css,
      '<h1>%s</h1>' % breadcrumbs(path[:-1], root_discovery),
      '<h2>Instance Methods</h2>'
      ]

  # Which methods are for collections.
  for name in dir(resource):
    if not name.startswith('_') and callable(getattr(resource, name)):
      if hasattr(getattr(resource, name), '__is_resource__'):
        collections.append(name)
      else:
        methods.append(name)


  # TOC
  if collections:
    for name in collections:
      if not name.startswith('_') and callable(getattr(resource, name)):
        href = path + name + '.html'
        html.append(Template(COLLECTION_LINK).substitute(href=href, name=name))

  if methods:
    for name in methods:
      if not name.startswith('_') and callable(getattr(resource, name)):
        doc = getattr(resource, name).__doc__
        params = method_params(doc)
        firstline = doc.splitlines()[0]
        html.append(Template(METHOD_LINK).substitute(
            name=name, params=params, firstline=firstline))

  if methods:
    html.append('<h3>Method Details</h3>')
    for name in methods:
      dname = name.rsplit('_')[0]
      html.append(method(name, getattr(resource, name).__doc__))

  html.append('</body></html>')

  return '\n'.join(html)


def document_collection_recursive(resource, path, root_discovery, discovery):

  html = document_collection(resource, path, root_discovery, discovery)

  f = open(os.path.join(BASE, path + 'html'), 'w')
  f.write(html)
  f.close()

  for name in dir(resource):
    if (not name.startswith('_')
        and callable(getattr(resource, name))
        and hasattr(getattr(resource, name), '__is_resource__')):
      dname = name.rsplit('_')[0]
      collection = getattr(resource, name)()
      document_collection_recursive(collection, path + name + '.', root_discovery,
               discovery['resources'].get(dname, {}))

def document_api(name, version):
  """Document the given API.

  Args:
    name: string, Name of the API.
    version: string, Version of the API.
  """
  service = build(name, version)
  response, content = http.request(
      uritemplate.expand(
          DISCOVERY_URI, {
              'api': name,
              'apiVersion': version})
          )
  discovery = simplejson.loads(content)

  version = safe_version(version)

  document_collection_recursive(
      service, '%s_%s.' % (name, version), discovery, discovery)


if __name__ == '__main__':
  http = httplib2.Http()
  resp, content = http.request(
      'https://www.googleapis.com/discovery/v1/apis?preferred=true',
      headers={'X-User-IP': '0.0.0.0'})
  if resp.status == 200:
    directory = simplejson.loads(content)['items']
    for api in directory:
      document_api(api['name'], api['version'])
  else:
    sys.exit("Failed to load the discovery document.")
