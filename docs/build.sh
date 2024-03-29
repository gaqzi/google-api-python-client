#!/bin/bash
#
# Copyright 2007 Google Inc.
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
#
# Author: jcgregorio@google.com (Joe Gregorio)
#
# Creates the documentation set for the library by
# running pydoc on all the files in apiclient.
#
# Notes: You may have to update the location of the
#        App Engine library for your local system.

export GOOGLE_APPENGINE=$HOME/projects/google_appengine/
export DJANGO_SETTINGS_MODULE=fakesettings
export PYTHONPATH=`pwd`/..:$GOOGLE_APPENGINE
epydoc --output epy --graph classtree --docformat plaintext apiclient oauth2client
