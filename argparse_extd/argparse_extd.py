#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import argparse
import inspect
import io
import base64

import json
import bz2
import gzip
import lzma
import yaml
import toml
import configparser


class ArgumentParserExtd(argparse.ArgumentParser):
    """
    Class for set configuration by file contents and command-line options
    """
    INI_SECTION  = configparser.DEFAULTSECT
    TOML_SECTION = 'DEFAULT'

    CONFIG_FORMAT = ('ini', 'yaml', 'json', 'toml')
    COMPRESS_EXT  = ('.bz2', '.gz', '.xz')

    SERIALIZE_KEY_TYPE  = '__type__'
    SERIALIZE_KEY_VALUE = '__value__'
    SERIALIZE_DICT_KEYS = { SERIALIZE_KEY_TYPE, SERIALIZE_KEY_VALUE }

    class NamespaceExtd(argparse.Namespace):
        """
        Extended class of argparse.Namespace
        """
        def __init__(self, **kwds):
            super().__init__(**kwds)

        def __getattr__(self, name):
            if name in self.__dict__:
                return self.__dict__[name]
            raise AttributeError('%s object has no attribute %s' % (repr(self.__class__.__name__), repr(name)))

        def __setitem__(self, name, value):
            self.__dict__[name] = value

        def __getitem__(self, name):
            return self.__dict__[name]

        def to_json(self):
            __outer_scope__ = self.__class__.__qualname__.removesuffix('.'+self.__class__.__name__)
            return json.dumps(self.__dict__, indent=4, default=eval(__outer_scope__).json_custom_serializer)

        @classmethod
        def from_json(cls, json_str:str):
            return cls(**json.loads(json_str, object_hook=eval(__outer_scope__).json_custom_object_hook))

        def update_from_dict(self, data):
            for key, value in data.items():
                setattr(self, key, value)

        def to_dict(self):
            return self.__dict__.copy()

    @classmethod
    def json_custom_serializer(cls, obj):
        if isinstance(obj, bytes):
            return {cls.SERIALIZE_KEY_TYPE: 'bytes', 
                    cls.SERIALIZE_KEY_VALUE: base64.b64encode(obj).decode(encoding='utf-8') }
        if isinstance(obj, bytearray):
            return {cls.SERIALIZE_KEY_TYPE: 'bytearray',
                    cls.SERIALIZE_KEY_VALUE: base64.b64encode(bytes(obj)).decode(encoding='utf-8')}
        raise TypeError('Object of type %s is not JSON serializable' % (type(obj).__name__, ) )

    @classmethod
    def json_custom_object_hook(cls, obj):
        if isinstance(obj, dict) and cls.SERIALIZE_DICT_KEYS.issubset(obj):
            if obj[cls.SERIALIZE_KEY_TYPE] == 'bytes':
                return base64.b64decode(obj[cls.SERIALIZE_KEY_VALUE].encode(encoding='utf-8'))
            if obj[self.__class__.SERIALIZE_KEY_TYPE] == 'bytearray':
                return bytearray(base64.b64decode(obj[cls.SERIALIZE_KEY_VALUE].encode(encoding='utf-8')))
        return obj

    @classmethod
    def encode_byte_dict_key(cls, key, sep1='::', sep2='__', avoid_eq_in_key=False):
        if isinstance(key, (tuple, frozenset)):
            return (sep1+cls.__name__+sep1+sep2+type(key).__name__+sep2+sep1
                    +json.dumps([cls.encode_bytes_base64(i) for i in key], default=cls.json_custom_serializer))
        if avoid_eq_in_key:
            if isinstance(key, bytes):
                return (sep1+cls.__name__+sep1+sep2+type(key).__name__+sep2+sep1
                        +base64.b64encode(key).decode(encoding='utf-8').replace("=","@"))
            return key
            
        if isinstance(key, bytes):
            return (sep1+cls.__name__+sep1+sep2+type(key).__name__+sep2+sep1
                    +base64.b64encode(key).decode(encoding='utf-8'))
        return key

    @classmethod
    def decode_byte_dict_key(cls, key, sep1='::', sep2='__', avoid_eq_in_key=False):

        if not isinstance(key, str):
            if avoid_eq_in_key:
                return key
            return key

        type_hdr_b = sep1+cls.__name__+sep1+sep2+'bytes'+sep2+sep1
        if key.startswith(type_hdr_b) or key.startswith(type_hdr_b.lower()) :
            if avoid_eq_in_key:
                return base64.b64decode(key[len(type_hdr_b):].replace("@","=").encode(encoding='utf-8'))
            return base64.b64decode(key[len(type_hdr_b):].encode(encoding='utf-8'))

        type_hdr_t = sep1+cls.__name__+sep1+sep2+'tuple'+sep2+sep1
        if key.startswith(type_hdr_t) or key.startswith(type_hdr_t.lower()) :
            return tuple(json.loads(key[len(type_hdr_b):].encode(encoding='utf-8'),
                                    object_hook=cls.json_custom_object_hook))
        
        type_hdr_f = sep1+cls.__name__+sep1+sep2+'frozenset'+sep2+sep1
        if key.startswith(type_hdr_f) or key.startswith(type_hdr_f.lower()) :
            return frozenset(json.loads(key[len(type_hdr_f):].encode(encoding='utf-8'),
                                        object_hook=cls.json_custom_object_hook))
        if avoid_eq_in_key:
            return key
        return key
    
    @classmethod
    def encode_bytes_base64(cls, obj, sep1='::', sep2='__', avoid_eq_in_key=False):

        if isinstance(obj, (bytes, bytearray)):
            return {cls.SERIALIZE_KEY_TYPE: type(obj).__name__,
                    cls.SERIALIZE_KEY_VALUE: base64.b64encode(obj).decode(encoding='utf-8')}
        
        if isinstance(obj, (tuple, set, frozenset)):
            return {cls.SERIALIZE_KEY_TYPE: type(obj).__name__,
                    cls.SERIALIZE_KEY_VALUE: [ cls.encode_bytes_base64(i, sep1=sep1, sep2=sep2,
                                                                       avoid_eq_in_key=avoid_eq_in_key) for i in obj ]}

        if isinstance(obj, list):
            return [ cls.encode_bytes_base64(i, sep1=sep1, sep2=sep2,
                                              avoid_eq_in_key=avoid_eq_in_key) for i in obj ]

        if isinstance(obj, dict):
            return {cls.encode_byte_dict_key(k, sep1=sep1, sep2=sep2,
                                              avoid_eq_in_key=avoid_eq_in_key):
                    cls.encode_bytes_base64(v, sep1=sep1, sep2=sep2,
                                             avoid_eq_in_key=avoid_eq_in_key) for k,v in obj.items()}

        return obj

    @classmethod
    def decode_bytes_base64(cls, obj, sep1='::', sep2='__', avoid_eq_in_key=False):

        if isinstance(obj, dict) and cls.SERIALIZE_DICT_KEYS.issubset(obj):
            if obj[cls.SERIALIZE_KEY_TYPE] == 'bytes':
                return base64.b64decode(obj[cls.SERIALIZE_KEY_VALUE].encode(encoding='utf-8'))
            if obj[cls.SERIALIZE_KEY_TYPE] == 'bytearray':
                return bytearray(base64.b64decode(obj[cls.SERIALIZE_KEY_VALUE].encode(encoding='utf-8')))
            if obj[cls.SERIALIZE_KEY_TYPE] == 'tuple':
                return tuple([ cls.decode_bytes_base64(i, sep1=sep1, sep2=sep2, avoid_eq_in_key=avoid_eq_in_key) 
                               for i in obj[cls.SERIALIZE_KEY_VALUE]])
            if obj[cls.SERIALIZE_KEY_TYPE] == 'set':
                return set([ cls.decode_bytes_base64(i, sep1=sep1, sep2=sep2, avoid_eq_in_key=avoid_eq_in_key) 
                             for i in obj[cls.SERIALIZE_KEY_VALUE]])
            if obj[cls.SERIALIZE_KEY_TYPE] == 'frozenset':
                return frozenset([ cls.decode_bytes_base64(i, sep1=sep1, sep2=sep2, avoid_eq_in_key=avoid_eq_in_key) 
                                   for i in obj[cls.SERIALIZE_KEY_VALUE]])
            
        if isinstance(obj, list):
            return [ cls.decode_bytes_base64(i, sep1=sep1, sep2=sep2, avoid_eq_in_key=avoid_eq_in_key) for i in obj ]

        if isinstance(obj, dict):
            return {cls.decode_byte_dict_key(k, sep1=sep1, sep2=sep2, avoid_eq_in_key=avoid_eq_in_key):
                    cls.decode_bytes_base64(v, sep1=sep1, sep2=sep2, avoid_eq_in_key=avoid_eq_in_key) for k,v in obj.items()}

        return obj

    @classmethod
    def flatten_dict(cls, d:dict, parent_key:str='', sep:str='________')->dict:
        items = {}
        for k, v in d.items():
            new_key = ("%s%s%s" % (parent_key, sep, k)) if parent_key else k
            if isinstance(v, dict):
                items.update(cls.flatten_dict(v, new_key, sep=sep))
            else:
                items[new_key] = v if isinstance(v, str) else json.dumps(v, default=cls.json_custom_serializer) 
        return items

    @classmethod
    def unflatten_dict(cls, d:dict, sep:str='________')->dict:
        result = {}
        for flat_key, v in d.items():
            keys = flat_key.split(sep)
            current = result
            for part in keys[:-1]:
                current = current.setdefault(part, {})
            try:
                current[keys[-1]] = json.loads(v, object_hook=cls.json_custom_object_hook)
            except:
                current[keys[-1]] = v
        return result


    class ConfigActionExtd(argparse.Action):
        """
        class to read configuration file that is specified by commad line option
        """
        def __init__(self, option_strings, **kwds):
            super().__init__(option_strings, **kwds)

        def __call__(self, parser, namespace, values, option_string=None):
            if os.path.exists(values):
                __outer_scope__ = self.__class__.__qualname__.removesuffix('.'+self.__class__.__name__)
                conf_data = eval(__outer_scope__).read_config(values, 
                                                              ini_section=eval(__outer_scope__).INI_SECTION,
                                                              toml_section=eval(__outer_scope__).TOML_SECTION)
                namespace.update_from_dict(conf_data)
            else:
                parser.error('Config file %s not found.' % (values, ))

    def __init__(self, conf_path=None, exclude_save:str|list|set|tuple=None, 
                 json_indent=4, yaml_default_flow_style=False,
                 ini_section=INI_SECTION, toml_section=TOML_SECTION, **kwds):

        super().__init__(**kwds)
        self.option_key_alist        = {}
        self.namespace               = self.__class__.NamespaceExtd()
        self.json_indent             = json_indent 
        self.yaml_default_flow_style = yaml_default_flow_style
        self.load_config(conf_path)
        self.write_config_exclude_default = []
        self.append_write_config_exclude(options=exclude_save)
        
    def parse_args(self, args=None, action_help=True):
        ns = super().parse_args(args=args, namespace=self.namespace)
        if action_help:
            self.help_action()
        return ns

    @property
    def args(self):
        return self.namespace

    def append_write_config_exclude(self, options : str|list|tuple|set):
        for x in (options if isinstance(options, (list, tuple, set)) else (options, )):
            if (not isinstance(x, str)) or (not x):
                continue
            optname = (x[2:] if x.startswith('--') else (x[1:] if x.startswith('-') else x)).replace('-', '_')
            if not optname in self.write_config_exclude_default:
                self.write_config_exclude_default.append(optname)

    @classmethod
    def list_opt_arg(cls, short_opt:str=None, long_opt:str=None, dest:str=None):
        cargs   = []
        opt_key = None
        if isinstance(short_opt,str) and short_opt:
            cargs.append(short_opt[:2] if short_opt.startswith('-') else '-'+short_opt[:1])
            opt_key = (short_opt[1:] if short_opt.startswith('-') else short_opt)
        if isinstance(long_opt,str) and long_opt:
            cargs.append(long_opt if long_opt.startswith('--') else '--'+long_opt)
            opt_key = (long_opt[2:] if long_opt.startswith('--') else long_opt).replace('-', '_')
        if isinstance(dest,str) and dest:
            opt_key = (dest[2:] if dest.startswith('--') else
                       (dest[1:] if dest.startswith('-') else dest)).replace('-', '_')
        return (opt_key, cargs)

    def add_argument_help(self, short_opt:str='-h', long_opt:str='--help',
                          help_text='show this help message and exit', **kwds):
        self.option_key_alist['help'], cargs = self.__class__.list_opt_arg(short_opt=short_opt,
                                                                           long_opt=long_opt, dest=kwds.get('dest'))
        if len(cargs)>0:
            self.add_argument(*cargs, action=kwds.get('action', 'store_true'), help=help_text, 
                              **{k:v for k,v in kwds.items() if not k in ('action', 'help') })
        if isinstance(self.option_key_alist['help'], str) and self.option_key_alist['help']:
            self.append_write_config_exclude(options=self.option_key_alist['help'])

    def help_action(self):
        if self.option_key_alist['help'] is not None and self.namespace[self.option_key_alist['help']]:
            self.print_help()
            sys.exit(0)

    def add_argument_verbose(self, 
                             short_opt:str='-v', long_opt:str='--verbose',
                             help_text='show verbose messages', **kwds):
        self.option_key_alist['verbose'], cargs = self.__class__.list_opt_arg(short_opt=short_opt,
                                                                              long_opt=long_opt, dest=kwds.get('dest'))
        if len(cargs)>0:
            self.add_argument(*cargs, action=kwds.get('action', 'store_true'), help=help_text,
                              **{k:v for k,v in kwds.items() if not k in ('action', 'help') })
        if isinstance(self.option_key_alist['verbose'], str) and self.option_key_alist['verbose']:
            self.append_write_config_exclude(options=self.option_key_alist['verbose'])

    def add_argument_quiet(self, 
                           short_opt:str='-q', long_opt:str='--quiet',
                           help_text='supress verbose messages', **kwds):
        opt_dest = kwds.get('dest')
        self.option_key_alist['quiet'], cargs = self.__class__.list_opt_arg(short_opt=short_opt, long_opt=long_opt, dest=opt_dest)
        if len(cargs)>0:
            self.add_argument(*cargs, action=kwds.get('action', 
                                                      'store_false' if isinstance(opt_dest,str) and opt_dest else 'store_true'),
                              help=help_text, **{k:v for k,v in kwds.items() if not k in ('action', 'help') })
        if isinstance(self.option_key_alist['quiet'], str) and self.option_key_alist['quiet']:
            self.append_write_config_exclude(options=self.option_key_alist['quiet'])


    def add_argument_config(self, short_opt:str='-C', long_opt:str='--config',
                            help_txt:str='path of the configuration file to be loaded', **kwds):
        self.option_key_alist['configfile'], cargs = self.__class__.list_opt_arg(short_opt=short_opt,
                                                                    long_opt=long_opt, dest=kwds.get('dest'))
        if len(cargs)>0:
            self.add_argument(*cargs, type=str, action=self.__class__.ConfigActionExtd,
                              help=help_txt,
                              **{k:v for k,v in kwds.items() if not k in ('action', 'help', 'type') })

        if isinstance(self.option_key_alist['configfile'], str) and self.option_key_alist['configfile']:
            self.append_write_config_exclude(options=self.option_key_alist['configfile'])

    def add_argument_save_config(self, short_opt:str='-S', long_opt:str='--save-config', short_opt_def:str=None, 
                                 default_path:str=None, help_txt:str='path of the configuration file to be saved', **kwds):
        self.option_key_alist['save_configfile'], cargs = self.__class__.list_opt_arg(short_opt=short_opt,
                                                                                      long_opt=long_opt, dest=kwds.get('dest'))
        if len(cargs)>0:
            self.add_argument(*cargs, type=str, nargs='?', default=None, const=default_path, help=help_txt,
                              **{k:v for k,v in kwds.items() if not k in ('type', 'nargs', 'default', 'help')})

        if isinstance(self.option_key_alist['save_configfile'], str) and self.option_key_alist['save_configfile']:
            self.append_write_config_exclude(options=self.option_key_alist['save_configfile'])
            dest_def=str(self.option_key_alist['save_configfile'])
            def_keywords = '-default'
            if isinstance(short_opt_def,str) and short_opt_def.startswith('-'):
                self.add_argument(short_opt_def, "--"+dest_def.replace('_', '-')+def_keywords,
                                  dest=dest_def, action='store_const', const=default_path, 
                                  help=help_txt+("(Use default: %s )" % (default_path,)))
            else:
                self.add_argument("--"+dest_def.replace('_', '-')+def_keywords,
                                  dest=dest_def, action='store_const', const=default_path, 
                                  help=help_txt+("(Use default: %s )" % (default_path,)))
            self.append_write_config_exclude(options=self.option_key_alist['save_configfile']+def_keywords.replace('-', '_'))

    def save_config_action(self, exclude_keys:list|tuple|set|dict=[],
                           f_mode=0o644, mk_dir:bool=True, d_mode=0o755, **kwds):

        save_path=self.namespace[self.option_key_alist['save_configfile']]
        if isinstance(save_path,str) and save_path:
            self.write_config(f_path=save_path, 
                              exclude_keys=exclude_keys,
                              f_mode=f_mode, mk_dir=mk_dir, d_mode=d_mode, **kwds)


    @classmethod
    def load_configfile(cls, namespace, conf_path, verbose=False,
                        ini_section=INI_SECTION, toml_section=TOML_SECTION):
        if isinstance(conf_path,str) and conf_path and os.path.exists(conf_path):
            namespace.update_from_dict(data=cls.read_config(conf_path,
                                                            ini_section=ini_section,
                                                            toml_section=toml_section))
        else:
            if verbose:
                sys.stderr.write('[%s.%s:%d] File not exists: %s\n'
                                 % (cls.__name__, inspect.currentframe().f_code.co_name,
                                    inspect.currentframe().f_lineno, conf_path))

    def load_config(self, conf_path, verbose=False):
        self.__class__.load_configfile(self.namespace, conf_path, verbose=verbose,
                                       ini_section=self.__class__.INI_SECTION, toml_section=self.__class__.TOML_SECTION)

    @classmethod
    def read_config(cls, file_path:str, ini_section=INI_SECTION, toml_section=TOML_SECTION) -> dict:
        bn,ext = os.path.splitext(file_path)
        if ext.lower() in cls.COMPRESS_EXT:
            with cls.open_compressed(file_path, 'rt', encoding='utf-8') as f:
                content = f.read()
        else:
            bn = file_path
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

                if bn.endswith('.json'):
                    return json.loads(content, object_hook=cls.json_custom_object_hook)
                elif bn.endswith(('.yaml', '.yml')):
                    return cls.decode_bytes_base64(yaml.safe_load(content))
                elif bn.endswith('.ini'):
                    config = configparser.ConfigParser(allow_unnamed_section=True)
                    config.optionxform = str
                    config.read_string(content)

                    # return {s: dict(config.items(s)) for s in config.sections() if s==ini_section}

                    raw_contents = {}
                    if isinstance(ini_section,str) and ini_section:
                        flaten = dict(config[ini_section])
                        raw_contents[ini_section] = cls.decode_bytes_base64(cls.unflatten_dict(flaten),
                                                                            sep1='$$', sep2='%%', avoid_eq_in_key=True)
                        return raw_contents.get(ini_section, {})

                    for k in config.sections():
                        flaten = dict(config[k])
                        raw_contents[k] = cls.decode_bytes_base64(cls.unflatten_dict(flaten),
                                                                  sep1='$$', sep2='%%', avoid_eq_in_key=True)
                    return raw_contents

                elif bn.endswith('.toml'):

                    config = toml.loads(content)
                    # return {s: dict(s.items()) for s in config.items() if s==toml_section}

                    raw_contents = cls.decode_bytes_base64(config)

                    if isinstance(toml_section,str) and toml_section:
                        # return {s: raw_contents[s] for s in config.items() if s==toml_section}
                        if isinstance(raw_contents[toml_section], dict):
                            return { k: v for k,v in raw_contents[toml_section].items() }
                        else:
                            return {}
                    return {s: raw_contents[s] for s in config.items()}

                else:
                    raise ValueError('Unsupported config file format: %s' % (file_path, ))


    @classmethod
    def open_compressed(cls, f_path, mode, encoding=None):
        if f_path.endswith('.bz2'):
            return bz2.open(f_path, mode, encoding=encoding)
        elif f_path.endswith('.gz'):
            return gzip.open(f_path, mode, encoding=encoding)
        elif f_path.endswith('.xz'):
            return lzma.open(f_path, mode, encoding=encoding)
        else:
            return open(f_path, mode, encoding=encoding)

    @classmethod
    def path_format_extsplit(cls, path):
        bn0,ext0 = os.path.splitext(path)
        bn1,ext1,ext0 = (os.path.splitext(bn0)+(ext0, )) if ext0 in cls.COMPRESS_EXT else (os.path.splitext(path)+('', ))
        bn,ext   = (bn1,ext1) if ext1[1:] in cls.CONFIG_FORMAT else (bn1+ext1, '')
        return (bn,
                ext[1:]  if ext.startswith('.')  else ext,
                ext0[1:] if ext0.startswith('.') else ext0)
        
    @classmethod
    def write_configfile(cls, f_path:str, data:dict, exclude_keys:list|tuple|set|dict=[],
                         f_mode=0o644, mk_dir:bool=True, d_mode=0o755,
                         json_indent=4, yaml_default_flow_style=False, ini_section='DEFAULT', toml_section='DEFAULT'):
        if (not isinstance(f_path, str)) or len(f_path)<1:
            return

        if mk_dir:
            d_path = os.path.dirname(f_path)
            if isinstance(d_path,str) and d_path:
                os.makedirs(d_path, mode=d_mode, exist_ok=True)
            
        bn,ext = os.path.splitext(f_path)

        if not ext.lower() in cls.COMPRESS_EXT:
            bn = f_path
            
        content = cls.dict_to_string(data=data,exclude_keys=exclude_keys,
                                     output_format=os.path.splitext(bn)[1],
                                     json_indent=json_indent,
                                     yaml_default_flow_style=yaml_default_flow_style,
                                     ini_section=ini_section, toml_section=toml_section)

        with cls.open_compressed(f_path, 'wt', encoding='utf-8') as f:
            f.write(content)
        os.chmod(f_path, f_mode)

    @classmethod
    def dict_to_string(cls, data:dict={}, exclude_keys:list|tuple|set|dict=[],
                       output_format:str='json', json_indent=4,
                       yaml_default_flow_style=False, ini_section=INI_SECTION, toml_encoder=None, toml_section=TOML_SECTION):

        exclude_keys = exclude_keys.keys() if isinstance(exclude_keys,dict) else exclude_keys
        skim_data = {k: v for k, v in data.items() if k not in exclude_keys}

        if output_format.endswith('json'):
            content = json.dumps(skim_data, indent=json_indent, default=cls.json_custom_serializer)
        elif output_format.endswith(('yaml', 'yml')):
            content = yaml.dump(cls.encode_bytes_base64(skim_data), default_flow_style=yaml_default_flow_style)
        elif output_format.endswith(('ini')):
            sio = io.StringIO()
            config = configparser.ConfigParser(allow_unnamed_section=True)
            config.optionxform = str
            config[ini_section] = { str(k) : str(v) for k, v 
                                    in cls.flatten_dict(cls.encode_bytes_base64(skim_data, sep1='$$', sep2='%%',
                                                                                avoid_eq_in_key=True)).items() }
            #for k, v in skim_data.items():
            #    # config[ini_section][k] = str(v)
            #    config[ini_section][str(k)] = { str(key): str(value)
            #                                    for key, value in cls.flatten_dict(cls.encode_bytes_base64(v, sep1='$$', sep2='%%',
            #                                                                                               avoid_eq_in_key=True)).items()}
            config.write(sio)
            content = sio.getvalue()
            sio.close()

        elif output_format.endswith(('toml')):
            # content = toml.dumps({toml_section : skim_data}, encoder=toml_encoder)

            content = toml.dumps(cls.encode_bytes_base64({toml_section : skim_data}),
                                 encoder=toml_encoder)
        else:
            content = repr(skim_data)
            # raise ValueError('Unsupported config file format: %s' % (output_format, ))


        return content

    def args_to_string(self, exclude_keys:list|tuple|set|dict=[],
                       output_format:str='json'):
        return self.__class__.dict_to_string(data=self.namespace.to_dict(),
                                             exclude_keys=exclude_keys,
                                             output_format=output_format, json_indent=self.json_indent,
                                             yaml_default_flow_style=self.yaml_default_flow_style,
                                             ini_section=self.__class__.INI_SECTION, toml_section=self.__class__.TOML_SECTION)

    def skimmed_args_to_string(self, exclude_keys:list|tuple|set|dict=[],
                               output_format:str='json'):
        return self.__class__.dict_to_string(data=self.namespace.to_dict(),
                                             exclude_keys=(self.write_config_exclude_default
                                                           + (exclude_keys.keys()
                                                              if isinstance(exclude_keys,dict)
                                                              else exclude_keys)),
                                             output_format=output_format, json_indent=self.json_indent,
                                             yaml_default_flow_style=self.yaml_default_flow_style,
                                             ini_section=self.__class__.INI_SECTION, toml_section=self.__class__.TOML_SECTION)

    def write_config(self, f_path:str, exclude_keys:list|tuple|set|dict=[],
                     f_mode=0o644, mk_dir:bool=True, d_mode=0o755, **kwds):
        self.__class__.write_configfile(f_path=f_path, data=self.namespace.to_dict(), 
                                        exclude_keys=(self.write_config_exclude_default
                                                      + (exclude_keys.keys()
                                                         if isinstance(exclude_keys,dict)
                                                         else exclude_keys)),
                                        f_mode=f_mode, mk_dir=mk_dir, d_mode=d_mode,
                                        json_indent=self.json_indent,
                                        yaml_default_flow_style=self.yaml_default_flow_style,
                                        ini_section=self.__class__.INI_SECTION, 
                                        toml_section=self.__class__.TOML_SECTION)
        
if __name__ == '__main__':

    import pkgstruct
    this_script_name = sys.argv[0].removesuffix('.py')
    pkg_info=pkgstruct.PkgStruct(script_path=this_script_name)
    
    argprsr = ArgumentParserExtd(add_help=False)
    argprsr.add_argument('-p', '--prefix', type=str, help='Directory Prefix')
    argprsr.add_argument('-c', '--default-config', type=str, default=(pkg_info.script_basename+'.config.json'), help='Default config filename')

    opts,remains=argprsr.parse_known_args()
    pkg_info=pkgstruct.PkgStruct(prefix=opts.prefix, script_path=this_script_name)
    pkg_default_config=pkg_info.concat_path('pkg_statedatadir', 'config', opts.default_config)

    argprsr.load_config(pkg_default_config)
    argprsr.add_argument_help()
    argprsr.add_argument_config()
    argprsr.add_argument_save_config(default_path=pkg_default_config)

    argprsr.add_argument_verbose()
    # Equivalent to argprsr.add_argument('-v', '--verbose', action='store_true', help='show verbose messages')
    argprsr.add_argument_quiet(dest='verbose')
    # Equivalent to argprsr.add_argument('-q', '--quiet', action='store_false', dest='verbose', help='supress verbose messages')

    argprsr.add_argument('-H', '--class-help', action='store_true', help='Show help for ArgumentParserExtd classes')


    argprsr.add_argument('-k', '--skimmed-output', action='store_true', help='Active status')
    argprsr.add_argument('-o', '--output', type=str, help='output filename') 
    argprsr.add_argument('-f', '--dump-format', type=str, choices=ArgumentParserExtd.CONFIG_FORMAT, default='json', help='Output format')


    argprsr.add_argument('-x', '--first-property', type=str, help='CL option 1')
    argprsr.add_argument('-y', '--second-property', type=str, help='CL option 2')
    argprsr.add_argument('-z', '--third-property', action='store_true', help='CL option 3')

    argprsr.add_argument('argv', nargs='*', help='non-optional CL arguments')

    argprsr.append_write_config_exclude(('--prefix', '--default-config', 'verbose',
                                         '--skimmed-output', '--output', '--save-config', 'argv'))

    args = argprsr.parse_args(action_help=True)

    if argprsr.args.class_help:
        import pydoc,sys
        pydoc.help = pydoc.Helper(output=sys.stdout)
        help(ArgumentParserExtd)
        help(ArgumentParserExtd.NamespaceExt)
        help(ArgumentParserExtd.ConfigActionExt)
        sys.exit()

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

    argprsr.write_config(argprsr.args.output)

