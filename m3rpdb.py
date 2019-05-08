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
# Missense Mutations Mapper and Randomizer for PDB files (M3R-PDB)
# ------------------------------------------------------------------------------
import argparse
import collections
import copy
import os
import random
import sys

import contrib.parse as parse
import contrib.yaml as yaml
from contrib.alignment.sequence import Sequence
from contrib.alignment.vocabulary import Vocabulary
from contrib.alignment.sequencealigner import SimpleScoring
from contrib.alignment.sequencealigner import StrictGlobalSequenceAligner

import m3r.messages as vm
from m3r.cosmic import COSMICDatabase
from m3r.ncbi import NCBIDatabase
from m3r.pdbfile import PDBFile

SCRIPT_NAME = "M3R-PDB Tool"
SCRIPT_VERSION = 1.0
CONFIG_DIRECTORY = "config"
SETTINGS_FILE = os.path.join( CONFIG_DIRECTORY, "settings.yaml" )


def LoadYAML( stream, loader=yaml.Loader ):
  class OrderedLoader( loader ):
    pass
  def ConstructMapping( loader, node ):
    loader.flatten_mapping( node )
    return collections.OrderedDict( loader.construct_pairs( node ) )
  OrderedLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    ConstructMapping )
  return yaml.load( stream, OrderedLoader )


def LoadSettingsFromFile( settings_filename=SETTINGS_FILE ):
  settings_data = None
  vm.Info( "Loading \"%s\"..." % SETTINGS_FILE )
  with open( settings_filename ) as stream:
    settings_data = LoadYAML( stream )
  return settings_data


def BuildEstimatedFASTA( fasta_size, mutation_list ):
  fasta = list( "-" * fasta_size )
  for mut in mutation_list:
    mut_info = parse.parse( "p.{}{:d}{}", mut )
    fasta[mut_info[1]-1] = mut_info[0]
  return "".join( fasta ).rstrip( "-" )


def CompareFASTA( ref_fasta, estimated_fasta ):
  ref_fasta_size = len( ref_fasta )
  estimated_fasta_size = len( estimated_fasta )
  if ref_fasta_size < estimated_fasta_size:
    return False
  for idx in range( estimated_fasta_size ):
    if estimated_fasta[idx] == "-":
      continue
    if ref_fasta[idx] != estimated_fasta[idx]:
      return False
  return True


def Main():
  vm.Info( "Initializing..." )
  genename = None
  pdbname = None
  nummodels = 0

  parser = argparse.ArgumentParser()
  parser.add_argument( "-g", "--gene", help="gene name to lookup" )
  parser.add_argument( "-p", "--pdb", help="source PDB file" )
  parser.add_argument( "-n", "--nummodels",
                       help="maximum number of models to generate" )
  args = parser.parse_args()

  # Possible gene names: OGG1, UNG, etc.
  genename = args.gene
  if not genename:
    vm.Error( "Gene name not set, use --gene as a command-line option" )
    return 1
  pdbname = args.pdb
  if not pdbname:
    vm.Error( "Source PDB name not set, use --pdb as a command-line option" )
    return 1
  try:
    nummodels = int( args.nummodels )
  except TypeError:
    nummodels = 0
  if not nummodels:
    vm.Error( "Number of output models not set, use --nummodels as a " \
              "command-line option" )
    return 1

  settings = None
  try:
    settings = LoadSettingsFromFile()
  except IOError as e:
    vm.Error( "Couldn't read settings file." )
    vm.Error( str( e ) )

  vm.Info( "Logging in to COSMIC database, please wait..." )
  cosmic_login = None
  cosmic_password = None
  try:
    cosmic_settings = settings["cosmic"]
    cosmic_login = cosmic_settings["email"]
    cosmic_password = cosmic_settings["password"]
  except ( TypeError, KeyError ):
    vm.Error( "No COSMIC login information present in settings file." )
  cosmic_database = COSMICDatabase()
  cosmic_database.Login( cosmic_login, cosmic_password )
  cosmic_login = None
  cosmic_password = None
  vm.Info( "Login successful." )

  # Connect to COSMIC database and get the list of missence mutations for the
  # gene.
  vm.Info( "Getting info for %s..." % genename )
  geneid = cosmic_database.FindGeneID( genename )
  vm.Info( "COSMIC %s gene ID = '%i'." % ( genename, geneid ) )
  vm.Info( "Getting missense mutations for %s..." % genename )
  mutations = cosmic_database.GetMissenseMutations( geneid )

  # Connect to NCBI database and get ref. sequences for the gene, along with
  # their FASTA sequences.
  ncbi_database = NCBIDatabase()
  geneid = ncbi_database.FindGeneID( genename )
  vm.Info( "NCBI %s gene ID = '%i'." % ( genename, geneid ) )
  refseq = ncbi_database.GetRefSequences( geneid )
  fastas = ncbi_database.GetFASTA( refseq )
  vm.Info( "%i FASTA sequences fetched." % len( fastas ) )

  # Build estimated FASTA sequence to compare with ref. sequences, to find which
  # ref. sequence our mutations are mapped onto.
  max_fasta_size = 0
  for _, fasta in fastas.iteritems():
    fasta_size = len( fasta )
    if fasta_size > max_fasta_size:
      max_fasta_size = fasta_size
  estimated_fasta = BuildEstimatedFASTA( max_fasta_size, \
                                         mutations["AA Mutation"] )
  matching_fasta_name = None
  for key, value in fastas.iteritems():
    if CompareFASTA( value, estimated_fasta ):
      matching_fasta_name = key
      break
  if not matching_fasta_name:
    vm.Error( "No matching ref. sequences found for %s." % genename )
    return 1
  vm.Info( "COSMIC mutations are mapped onto %s ref. sequence \"%s\"." % \
           ( genename, matching_fasta_name ) )

  # Load the PDB file.
  if not pdbname.endswith( ".pdb" ):
    pdbname += ".pdb"
  vm.Info( "Loading \"%s\"..." % pdbname )
  pdbfile = PDBFile( pdbname )

  # Align our estimated sequence and the sequence loaded from PDB.
  vm.Info( "Aligning sequences, please wait..." )
  vocab = Vocabulary()
  ref_encoded = vocab.encodeSequence( Sequence( fastas[matching_fasta_name] ) )
  pdb_encoded = vocab.encodeSequence( Sequence( pdbfile.GetFASTA() ) )
  aligner = StrictGlobalSequenceAligner( SimpleScoring( 2, -1 ), -2 )
  score, encodeds = aligner.align( ref_encoded, pdb_encoded, backtrace=True )
  if len( encodeds ) < 1:
    vm.Error( "Sequence alignment failed." )
    return 1
  vm.Info( "Sequence alignment succeeded (score = %.2f)." % score )
  aligned_fasta = "".join( str( letter ) for letter in \
                           vocab.decodeSequence( encodeds[0].second ).elements )

  # Generate "real" residue numbers.
  real_resid = []
  real_position = 0
  base_offset = pdbfile.GetResidueBaseOffset()
  for letter in aligned_fasta:
    if letter == "-":
      real_resid.append( 0 )
      continue
    real_position = real_position + 1
    real_resid.append( base_offset + real_position )

  # Build a list of mutations that can be mapped onto our aligned sequence.
  pdb_mutation_info = {}
  mutation_counter = 0
  for mut in mutations["AA Mutation"]:
    mut_source, mut_number, mut_target = parse.parse( "p.{}{:d}{}", mut )
    if aligned_fasta[mut_number-1] == mut_source:
      mut_name = mut_source + str( mut_number ) + mut_target
      mut_dict_index = "{:08d}{}".format( mut_number, mut_target )
      if mut_dict_index in pdb_mutation_info:
        # vm.Warn( "Skipping duplicate mutation info for '%s'." % mut_name )
        continue
      if not pdbfile.ResidueExists( real_resid[mut_number-1] ):
        vm.Warn( "Skipping mutation of missing residue '%s'." % mut_name )
        continue
      pdb_mutation_info[mut_dict_index] = {
        "name" : mut_name,
        "resid" : real_resid[mut_number-1],
        "from" : mut_source,
        "to" : mut_target,
        "status" : mutations["Somatic Status"][mutation_counter],
        "transcript" : mutations["Transcript"][mutation_counter],
        "zygosity" : mutations["Zygosity"][mutation_counter],
        "tissue" : mutations["Primary Tissue"][mutation_counter],
        "histology" : mutations["Histology"][mutation_counter]
      }
    mutation_counter = mutation_counter + 1
  pdb_mutation_info = collections.OrderedDict( \
      sorted( pdb_mutation_info.iteritems() ) ).values()
  num_pdb_mutations = len( pdb_mutation_info )
  vm.Info( "%i mutations can be applied to the PDB file." % num_pdb_mutations )

  # Save PDB files with mutations.
  # Pick N randomly selected, if too many.
  mutation_index_list = list( range( 0, num_pdb_mutations ) )
  if num_pdb_mutations > nummodels:
    vm.Info( "Randomly picking %i mutations out of %i." % \
            ( nummodels, num_pdb_mutations ) )
    random.shuffle( mutation_index_list )
    mutation_index_list = mutation_index_list[:nummodels]
    mutation_index_list.sort()
  filename, fileext = os.path.splitext( pdbname )
  progname = SCRIPT_NAME + " " + str( SCRIPT_VERSION )
  for index in mutation_index_list:
    mut = pdb_mutation_info[index]
    output_name = filename + "." + mut["name"].lower() + fileext
    vm.Info( "Saving: %s" % output_name )
    pdbfile_mutated = copy.deepcopy( pdbfile )
    pdbfile_mutated.MutateAA( mut )
    pdbfile_mutated.Save( output_name, progname )

  vm.Print( "All done." )
  return 0


if __name__ == "__main__":
  vm.Banner( SCRIPT_NAME, SCRIPT_VERSION )
  SCRIPT_ERROR_CODE = 1
  try:
    SCRIPT_ERROR_CODE = Main()
  except RuntimeError as e:
    vm.Error( str( e ) )
  sys.exit( SCRIPT_ERROR_CODE )
