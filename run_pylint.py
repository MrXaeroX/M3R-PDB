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
# Purpose: runs pylint on the project directory.
import os
import re
import sys
import time

import m3r.messages as vm
from pylint import lint

SCRIPT_NAME = "M3R-PDB"
SCRIPT_VERSION = 1.0
PROJECT_DIR = os.path.dirname( os.path.abspath( __file__ ) )


def RunLinter():
  rcfile = os.path.join( PROJECT_DIR, "pylint", ".pylintrc" )
  old_cwd = os.getcwd()
  os.chdir( PROJECT_DIR )
  is_quiet_mode = False

  linter_args = [ "--rcfile", rcfile ]
  ignore_dirs = [ "pylint", "contrib" ]  # Directories/modules to ignore.
  ignore_modules = [ "cpplint.py" ]

  py_modules = []
  project_path_re = re.compile( r'project[\/](.*)' )
  for argstr in sys.argv[1:]:
    if argstr == "--githook":
      is_quiet_mode = True
      linter_args.append( "--score=n" )
    else:
      re_check = project_path_re.match( argstr )
      if re_check:  # If path contains project.
        py_modules.append( re_check.group( 1 ) )
      else:  # Otherwise add to linter arguments as is.
        linter_args.append( argstr )

  if not py_modules:
    vm.Print( "Building a list of python modules...", end=" " )
    for dirpath, _, filenames in os.walk( "./" ):
      dir_list = os.path.normpath( dirpath ).split( os.sep )
      if any( ignore_dir in dir_list for ignore_dir in ignore_dirs ):
        continue
      for filename in filenames:
        if filename.endswith( ".py" ) and filename not in ignore_modules:
          py_modules.append( os.path.join( dirpath, filename ) )
    vm.Print( "{} modules found.".format( len( py_modules ) ) )

  if not py_modules:
    vm.Print( "Nothing to do." )
    return 0

  linter_args.extend( py_modules )
  start_time = time.time()
  result = lint.Run( linter_args, exit=False )
  elapsed_time = time.time() - start_time

  os.chdir( old_cwd )
  if not is_quiet_mode:
    if elapsed_time >= 60:
      vm.HeadPrint( "All done: %i minutes %i seconds elapsed" % \
                    ( elapsed_time / 60, elapsed_time % 60 ) )
    else:
      vm.HeadPrint( "All done: %i seconds elapsed" % elapsed_time )
  return result.linter.msg_status


if __name__ == "__main__":
  vm.Banner( "%s Tool PyLint Runner" % SCRIPT_NAME, SCRIPT_VERSION )
  sys.exit( RunLinter() )
