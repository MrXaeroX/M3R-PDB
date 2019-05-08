﻿# -*- coding: utf-8;
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
_AA_MAP = {
  "ALA": "A",
  "ARG": "R",
  "ASN": "N",
  "ASH": "D",
  "ASP": "D",
  "ASX": "B",
  "CYM": "C",
  "CYS": "C",
  "GLH": "E",
  "GLU": "E",
  "GLN": "Q",
  "GLX": "Z",
  "GLY": "G",
  "HID": "H",
  "HIE": "H",
  "HIP": "H",
  "HIS": "H",
  "ILE": "I",
  "LEU": "L",
  "LYN": "K",
  "LYS": "K",
  "MET": "M",
  "PHE": "F",
  "PRH": "P",
  "PRO": "P",
  "SER": "S",
  "THR": "T",
  "TRP": "W",
  "TYR": "Y",
  "VAL": "V"
}
_AA_MAP_INVERSE = {
  "A" : "ALA",
  "R" : "ARG",
  "N" : "ASN",
  "D" : "ASP",
  "C" : "CYS",
  "E" : "GLU",
  "Q" : "GLN",
  "G" : "GLY",
  "H" : "HIE",
  "I" : "ILE",
  "L" : "LEU",
  "K" : "LYS",
  "M" : "MET",
  "F" : "PHE",
  "P" : "PRO",
  "S" : "SER",
  "T" : "THR",
  "W" : "TRP",
  "Y" : "TYR",
  "V" : "VAL"
}
_AA_BACKBONE = [ " N  ", " C  ", " CA ", " O  " ]

class PDBFile( object ):
  """This class implements PDB file interface. It supports reading, writing,
  getting FASTA, etc."""

  def __init__( self, filename=None ):
    self.atoms = {}
    self.residues = {}
    self.remarks = []
    self._chain_index = 0
    self._min_resid = 99999999
    self._max_resid = 0
    self._filename = ""
    self._linecount = 0
    if filename:
      self.Load( filename )

  def Load( self, filename ):
    self._filename = filename
    self._linecount = 1
    with open( filename, "r" ) as file_object:
      line = file_object.readline()
      while line:
        header = line[:6].rstrip()
        if header == "ATOM":
          self._ParseAtomDesc( line )
        elif header == "TER":
          self._chain_index = self._chain_index + 1
        elif header == "END":
          break
        self._linecount = self._linecount + 1
        line = file_object.readline()

  def Save( self, filename, progname=None ):
    self._filename = filename
    self._linecount = 1
    with open( filename, "w" ) as file_object:
      if progname:
        file_object.write( "REMARK Generated by %s\n" % progname )
        self._linecount = self._linecount + 1
      for remark in self.remarks:
        file_object.write( "REMARK %s\n" % remark )
        self._linecount = self._linecount + 1
      current_serial = 0
      current_chain = None
      for _, value in self.atoms.iteritems():
        line = ""
        if current_chain != value["chain"]:
          if current_chain:
            line += "{:6}{:5d}\n".format( "TER", current_serial )
          current_chain = value["chain"]
        current_serial = current_serial + 1
        line += "{:6}{:5d}".format( "ATOM", current_serial )
        line += " {:.4}{:1}".format( value["title"], value["atloc"] )
        line += "{:.3} {:.1}{:4d}    ".format( value["residue"], current_chain,
                                               value["resid"] )
        for j in range( 0, 3 ):
          line += "{:8.3f}".format( value["coords"][j] )
        line += "{}\n".format( value["extra"] )
        self._linecount = self._linecount + 1
        file_object.write( line )
      file_object.write( "{:6}{:5d}\nEND\n".format( "TER", current_serial ) )

  def GetFASTA( self ):
    fasta = ""
    for resid in range( 1, self._max_resid + 1 ):
      if resid not in self.residues:
        fasta += "-"
      elif self.residues[resid] in _AA_MAP:
        fasta += _AA_MAP[self.residues[resid]]
      else:
        break  # End of protein.
    return fasta

  def GetResidueBaseOffset( self ):
    return self._min_resid - 1

  def ResidueExists( self, resid ):
    return resid in self.residues

  def MutateAA( self, mutation_info ):
    resid = mutation_info["resid"]
    aafrom_1let = mutation_info["from"]
    aato_3let = _AA_MAP_INVERSE[mutation_info["to"]]
    if not resid in self.residues:
      raise RuntimeError( "%s: missing residue %i." % \
                         ( self._filename, resid ) )
    if _AA_MAP[self.residues[resid]] != aafrom_1let:
      raise RuntimeError( "%s: residue %s-%i is not %s." % \
                         ( self._filename, self.residues[resid], resid,
                           aafrom_1let ) )
    self.residues[resid] = aato_3let
    # Remove AA atoms, except the backbone.
    stale_serials = []
    for key, value in self.atoms.iteritems():
      if value["resid"] != resid:
        continue
      atom_title = value["title"]
      # Remove non-backbone atoms. Also try to preserve beta-carbon, if possible.
      if atom_title not in _AA_BACKBONE and \
         not ( atom_title == " CB " and aato_3let != "GLY" ):
        stale_serials.append( key )
        continue
      value["residue"] = aato_3let
    if stale_serials:
      for stale_serial in stale_serials:
        del self.atoms[stale_serial]
    self.remarks.append( "Mutation: %s" % mutation_info["name"] )
    self.remarks.append( "Tissue: %s" % mutation_info["tissue"] )
    self.remarks.append( "Histology: %s" % mutation_info["histology"] )
    self.remarks.append( "Zygosity: %s" % mutation_info["zygosity"] )
    self.remarks.append( "Somatic status: %s" % mutation_info["status"] )
    self.remarks.append( "Transcript: %s" % mutation_info["transcript"] )

  def _ParseAtomDesc( self, line ):
    atom_desc = {}
    serial = int( line[6:11] )
    if serial in self.atoms:
      raise RuntimeError( "%s@%i: duplicate atom %i." % \
                          ( self._filename, self._linecount, serial ) )
    resid = int( line[22:26] )
    resname = line[17:20]
    if resid < self._min_resid:
      self._min_resid = resid
    if resid > self._max_resid:
      self._max_resid = resid
    if resid not in self.residues:
      self.residues[resid] = resname.strip().upper()
    atom_desc["title"] = line[12:16]
    atom_desc["atloc"] = line[16]
    atom_desc["residue"] = resname
    atom_desc["chain"] = chr( ord( "A" ) + self._chain_index )
    atom_desc["resid"] = resid
    atom_desc["coords"] = [ float( line[30:38] ),
                            float( line[38:46] ),
                            float( line[46:54] ) ]
    atom_desc["extra"] = line[54:79]
    self.atoms[serial] = atom_desc
