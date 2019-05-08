# -*- coding: utf-8;
# ------------------------------------------------------------------------------
# Copyright (C) 2019 Alexander V. Popov.
#
# This source code is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or (at your option) any later version.
#
# This source code is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
# ------------------------------------------------------------------------------
import cookielib
import csv
import ssl
import urllib
import urllib2

try:
  from StringIO import StringIO
except ImportError:
  from io import StringIO

from contrib.bs4 import BeautifulSoup

_COSMIC_LOGIN_URL = "https://cancer.sanger.ac.uk/cosmic/login"
_COSMIC_SEARCH_URL = "https://cancer.sanger.ac.uk/cosmic/gene/analysis?ln=%s"
_COSMIC_MMUT_URL = "https://cancer.sanger.ac.uk/cosmic/gene/positive?all_data" \
                   "=&id=%i&mut=substitution_missense&src=gene"


class COSMICDatabase( object ):
  """This class implements access to COSMIC database. It supports logging in,
  retrieving gene data, mutations lists, etc."""

  def __init__( self ):
    self._is_loggedin = False
    self._context = ssl.SSLContext( ssl.PROTOCOL_TLSv1 )
    self._cookies = cookielib.CookieJar()
    self._opener = urllib2.build_opener(
      urllib2.HTTPRedirectHandler(),
      urllib2.HTTPHandler( debuglevel=0 ),
      urllib2.HTTPSHandler( debuglevel=0, context=self._context ),
      urllib2.HTTPCookieProcessor( self._cookies )
    )
    if self._opener is not None:
      self._opener.addheaders = [ ( "User-agent", "Mozilla/5.0" ) ]

  def Login( self, login, password ):
    # Don't login twice.
    if not self._is_loggedin:
      if not login:
        raise RuntimeError( self._errmsg_cannot_login + " " +
                            self._errmsg_empty_email )
      if not password:
        raise RuntimeError( self._errmsg_cannot_login + " " +
                            self._errmsg_empty_pass )
      login_data = urllib.urlencode( {
        "email" : login,
        "pass" : password
      } )
      response = self._opener.open( _COSMIC_LOGIN_URL, login_data )
      htmldata = BeautifulSoup( response.read(), features="html.parser" )
      login_info = htmldata.find( "dd", { "class": "login-error" } )
      if login_info is not None:
        vispass = None if not password else "*" * len( password )
        errormsg = self._errmsg_cannot_login + " " + \
          ( self._errmsg_credentials % ( login, vispass ) )
        servermsg = ""
        for msg in htmldata.find_all( "h3" ):
          servermsg += msg.string + "."
        if servermsg is not None:
          errormsg += " " + ( self._errmsg_servermsg % servermsg )
        raise RuntimeError( errormsg )
      self._is_loggedin = True

  def FindGeneID( self, name ):
    if not self._is_loggedin:
      raise RuntimeError( self._errmsg_no_login )
    if name is None:
      raise RuntimeError( self._errmsg_empty_gene )
    data = self._opener.open( _COSMIC_SEARCH_URL % name )
    htmldata = BeautifulSoup( data.read(), features="html.parser" )
    ids = htmldata.find_all( "input", { "name": "id", "type": "hidden" } )
    lns = htmldata.find_all( "input", { "name": "ln", "type": "hidden" } )
    id_count = len( ids )
    if id_count == 0:
      raise RuntimeError( self._errmsg_invalid_gene )
    for i in range( id_count ):
      if lns[i].get( "value" ) != name:
        continue
      return int( ids[i].get( "value" ) )
    raise RuntimeError( self._errmsg_parse_error )

  def GetMissenseMutations( self, gene_id ):
    if not self._is_loggedin:
      raise RuntimeError( self._errmsg_no_login )
    if gene_id <= 0:
      raise RuntimeError( self._errmsg_invalid_gene )
    data = self._opener.open( _COSMIC_MMUT_URL % gene_id )
    csvdata = data.read()
    if len( csvdata ) <= 1:
      raise RuntimeError( self._errmsg_parse_error )
    csvdata_io = StringIO( csvdata )
    csvreader = csv.reader( csvdata_io, delimiter="\t" )
    csvheaders = next( csvreader, None )
    csvparsed = {}
    for hdr in csvheaders:
      csvparsed[hdr] = []
    for row in csvreader:
      for hdr, var in zip( csvheaders, row ):
        csvparsed[hdr].append( var )
    return csvparsed


  _errmsg_no_login = "Not logged in."
  _errmsg_empty_gene = "Gene name is not specified."
  _errmsg_invalid_gene = "Gene name/id is not valid."
  _errmsg_parse_error = "Couldn't parse COSMIC response."
  _errmsg_cannot_login = "Couldn't login to COSMIC database."
  _errmsg_empty_email = "Email is empty."
  _errmsg_empty_pass = "Password is empty."
  _errmsg_credentials = "Email is \"%s\", password is \"%s\"."
  _errmsg_servermsg = "Server responded with the message(s): %s"
