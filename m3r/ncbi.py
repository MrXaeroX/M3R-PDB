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
import json
import ssl
import urllib2

_NCBI_GENE_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/" \
                        "esearch.fcgi?db=gene&term=%s&retmax=1&retmode=json" \
                        "&sort=relevance"
_NCBI_RSEQ_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/" \
                        "elink.fcgi?id=%i&linkname=gene_protein_refseq" \
                        "&retmode=json"
_NCBI_RSEQ_FASTA_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/" \
                        "efetch.fcgi?db=sequences&id=%s&rettype=fasta"


class NCBIDatabase( object ):
  """This class implements access to NCBI database. It supports logging in,
  retrieving gene data, mutations lists, etc."""

  def __init__( self ):
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

  def FindGeneID( self, name ):
    if name is None:
      raise RuntimeError( self._errmsg_empty_gene )
    data = self._opener.open( _NCBI_GENE_SEARCH_URL % name )
    jsondata = json.loads( data.read() )
    if not "esearchresult" in jsondata:
      raise RuntimeError( self._errmsg_parse_error )
    id_count = int( jsondata["esearchresult"]["count"] )
    if id_count == 0:
      raise RuntimeError( self._errmsg_invalid_gene )
    id_value = jsondata["esearchresult"]["idlist"][0]
    if id_value:
      return int( id_value )
    raise RuntimeError( self._errmsg_parse_error )

  def GetRefSequences( self, gene_id ):
    if gene_id <= 0:
      raise RuntimeError( self._errmsg_invalid_gene )
    data = self._opener.open( _NCBI_RSEQ_SEARCH_URL % gene_id )
    jsondata = json.loads( data.read() )
    if not "linksets" in jsondata:
      raise RuntimeError( self._errmsg_parse_error )
    for linkset in jsondata["linksets"]:
      if not "ids" in linkset or int( linkset["ids"][0] ) != gene_id:
        continue
      for linksetdb in linkset["linksetdbs"]:
        if linksetdb["linkname"] != "gene_protein_refseq":
          continue
        return linksetdb["links"]
    raise RuntimeError( self._errmsg_parse_error )

  def GetFASTA( self, refseq_ids ):
    if not refseq_ids:
      raise RuntimeError( self._errmsg_empty_refseq )
    refseq_string = ""
    for refseq_id in refseq_ids:
      if refseq_id <= 0:
        raise RuntimeError( self._errmsg_invalid_refseq )
      if refseq_string:
        refseq_string += ","
      refseq_string += str( refseq_id )
    data = self._opener.open( _NCBI_RSEQ_FASTA_URL % refseq_string )
    fastas = data.read().split( "\n\n" )
    result = {}
    for fasta in fastas:
      lines = fasta.splitlines()
      if not lines or lines[0][0] != '>':
        continue
      fasta_value = "".join( lines[1:] )
      # Ignore duplicate sequences.
      if fasta_value not in result.values():
        result[lines[0][1:]] = fasta_value
    return result


  _errmsg_empty_gene = "Gene name is not specified."
  _errmsg_invalid_gene = "Gene name/id is not valid."
  _errmsg_empty_refseq = "RefSequence list is empty."
  _errmsg_invalid_refseq = "RefSequence id is not valid."
  _errmsg_parse_error = "Couldn't parse NCBI response."
