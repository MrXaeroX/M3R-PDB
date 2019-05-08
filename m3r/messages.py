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
from __future__ import print_function

import sys

import contrib.colorama as colorama

HR_LINE = "-" * 64
NO_BANNER = False


def Error( message, **kwargs ):
  print( colorama.Fore.RED + colorama.Style.BRIGHT + "ERROR: " + \
        colorama.Style.RESET_ALL + str( message ), **kwargs )
  sys.stdout.flush()


def Warn( message, **kwargs ):
  print( colorama.Fore.YELLOW + colorama.Style.BRIGHT + "WARNING: " + \
        colorama.Style.RESET_ALL + str( message ), **kwargs )
  sys.stdout.flush()


def Info( message, **kwargs ):
  print( colorama.Fore.GREEN + colorama.Style.BRIGHT + "INFO: " + \
        colorama.Style.RESET_ALL + str( message ), **kwargs )
  sys.stdout.flush()


def Print( message, **kwargs ):
  print( message, **kwargs )
  sys.stdout.flush()


def HeadPrint( message, **kwargs ):
  first_space = message.find( ":" )
  the_rest = message
  if first_space >= 0:
    print( colorama.Style.BRIGHT + message[:first_space] + \
           colorama.Style.RESET_ALL, end='' )
    the_rest = message[first_space:]
  print( the_rest, **kwargs )
  sys.stdout.flush()


def Banner( program_name, program_version, **kwargs ):
  if "--nobanner" in sys.argv:
    global NO_BANNER
    NO_BANNER = True
    sys.argv.remove( "--nobanner" )
  if NO_BANNER:
    return
  color_prefix = colorama.Style.BRIGHT + colorama.Fore.CYAN
  cyan_line = color_prefix + HR_LINE
  program_info = color_prefix + program_name + " " + str( program_version )
  copy_right_info = color_prefix + "Copyright (c) 2018-2019, Alexander V. Popov"
  message = "\n".join( ( cyan_line, program_info, copy_right_info, cyan_line ) )
  print( message + colorama.Style.RESET_ALL, **kwargs )
  sys.stdout.flush()
