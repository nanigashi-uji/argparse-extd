#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pydoc
import sys
import pkgstruct
import argparse_extd

def main():
    # 1. Setting the default config-file name

    #   1.a Analyze directory tree and configuration file name using script-name as a default
    this_script_name = sys.argv[0].removesuffix('.py')
    pkg_info=pkgstruct.PkgStruct(script_path=this_script_name)
    config_name_default = pkg_info.script_basename+'.config.json'

    #   1.b Update directory tree and configuration file name when "--prefix" is specified
    #       Disable auto_help(add_help=False) because "parse_known_args()" will be used
    argprsr = argparse_extd.ArgumentParserExtd(add_help=False)
    argprsr.add_argument('-p', '--prefix', type=str, help='Directory Prefix')
    argprsr.add_argument('-c', '--default-config', type=str, default=config_name_default, help='Default config filename')
    #   Analyze argument once only for "--prefix" and "--default-config"
    opts,remains=argprsr.parse_known_args()
    pkg_info=pkgstruct.PkgStruct(prefix=opts.prefix, script_path=this_script_name)

    #   1.c Determine the configuration file path
    pkg_default_config=pkg_info.concat_path('pkg_statedatadir', 'config', opts.default_config)
    # 2 Load configuration file
    argprsr.load_config(pkg_default_config)

    # 3. Set optional argument to enable "auto_help"
    #    (Recovery of "add_help=False" at 1.b)
    argprsr.add_argument_help()
    # 4. Set optional argument "--config" to read settings from configuration file
    argprsr.add_argument_config()

    # 5. Set optional argument "--save-config" to save settings from configuration file, or specified file
    argprsr.add_argument_save_config(default_path=pkg_default_config)

    # 6. Equivalent to argprsr.add_argument('-v', '--verbose',
    #                                       action='store_true', help='show verbose messages')
    argprsr.add_argument_verbose()

    # 7. Equivalent to argprsr.add_argument('-q', '--quiet',
    #                                       action='store_false', dest='verbose', 
    #                                       help='supress verbose messages')
    argprsr.add_argument_quiet(dest='verbose')

    # 8. Add argumanets as usual argparse 
    argprsr.add_argument('-H', '--class-help', action='store_true',
                         help='Show help for ArgumentParserExtd classes')
    argprsr.add_argument('-s', '--skimmed-output',
                         action='store_true', help='Active status')
    argprsr.add_argument('-o', '--output', type=str, help='output filename') 
    argprsr.add_argument('-f', '--dump-format', type=str,
                         choices=argparse_extd.ArgumentParserExtd.CONFIG_FORMAT,
                         default='json', help='Output format')

    argprsr.add_argument('-x', '--first-property', type=str, help='CL option 1')
    argprsr.add_argument('-y', '--second-property', type=str, help='CL option 2')
    argprsr.add_argument('-z', '--third-property', action='store_true', help='CL option 3')

    argprsr.add_argument('argv', nargs='*', help='non-optional CL arguments')

    # 9. Select options that is not saved to configuration file putput 
    argprsr.append_write_config_exclude(('--prefix', '--default-config', 'verbose',
                                         '--skimmed-output', '--output', '--save-config', 'argv'))
    
    # 9. Analyze commandline as usual
    #    Call with 'action_help=True' because the constructor was called with 'add_help=False'.
    args = argprsr.parse_args(action_help=True)

    # CL option can be accessed by 2 way.
    #   A. properties of the output object from parse_args()
    #      ex.
    #      args    = argprsr.parse_args()
    #      flg_zzz = args.zzz
    #
    #   B. properties of the member object 'args' of the entity of ArgumentParserExtd.
    #      ex.
    #      flg_zzz = argprsr.args.zzz
    #

    if argprsr.args.class_help:
        pydoc.help = pydoc.Helper(output=sys.stdout)
        help(argparse_extd.ArgumentParserExtd)
        help(argparse_extd.ArgumentParserExtd.NamespaceExt)
        help(argparse_extd.ArgumentParserExtd.ConfigActionExt)
        sys.exit()

    #
    # 10. Output options to default configutation file.
    #
    argprsr.save_config_action()

    if argprsr.args.verbose:
        print('Prefix              : ', pkg_info.prefix)
        print('Default config      : ', argprsr.args.default_config)

    print('Default config path : ', pkg_default_config)

    print('Final Namespace: ', argprsr.args)
    print('Serialized %-4s:\n----\n%s\n----\n' % (argprsr.args.dump_format.upper(), 
                                                  (argprsr.skimmed_args_to_string(output_format=argprsr.args.dump_format)
                                                   if argprsr.args.skimmed_output
                                                   else argprsr.args_to_string(output_format=argprsr.args.dump_format))))
    #      
    # 11. Output options to specified file
    #
    argprsr.write_config(argprsr.args.output)

if __name__ == '__main__':
    main()
