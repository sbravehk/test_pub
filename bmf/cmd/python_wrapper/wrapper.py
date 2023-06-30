#!/usr/bin/env python

import os
import subprocess
import sys
import site
import glob
import re
from pathlib import PurePath

def find_file(filepath:str):
    filefullpath = ""
    found = False
    for package_root in site.getsitepackages():
        # Find the path of the real executable.
        filefullpath = os.path.join(package_root, filepath)

        if os.path.exists(filefullpath):
            found=True
            return found, filefullpath

    return found, ""

def exec_cmd(cmd:str, args):
    found, cmdpath = find_file(cmd)
    if found:
        # Execute it with all command line arguments.
        subprocess.call([cmdpath] + args)
    else:
        print("cannot find {}".format(os.path.basename(__file__)))
        exit(1)

def run_bmf_graph():
    exec_cmd(os.path.join("bmf", "bin", "run_bmf_graph"), sys.argv[1:])

def trace_format_log():
    exec_cmd(os.path.join("bmf", "bin", "trace_format_log"), sys.argv[1:])

def module_manager():
    exec_cmd(os.path.join("bmf", "bin", "module_manager"), sys.argv[1:])

def cpp_adapt():
    #if len(sys.argv) < 2:
    #    raise Exception("package name must be passed")
    #package_name = __package__
    #found, package_path = find_file(package_name.replace('.', os.sep))
    #package_root = PurePath(package_path).parent.parent.parent
    #if found:
    #    extensions_dir = package_root / (sys.argv[1]+".libs")
    #    for file_glob in ["bmf_module_sdk", "engine", "hmp"]:
    #        for lib_path in glob.glob(f"{extensions_dir}{os.sep}*{file_glob}*"):
    #            lib_file = os.path.basename(lib_path)

    #            pattern = r"(.*)"+file_glob+r".*?\.([^.]+)\.(.*)"
    #            match = re.search(pattern, lib_file)
    #            if match:
    #                lib_prefix = match.group(1)
    #                lib_suffix = match.group(2)
    #                lib_version  = match.group(3)

    #                symbol_path = os.path.join(extensions_dir, lib_prefix + file_glob + "." + lib_suffix)
    #                os.symlink(lib_path, symbol_path)
    #            else:
    #                raise Exception("pattern:{} not matched lib:{}".format(pattern, lib_path))

    #    print("please set environments to find BMF libraries, maybe you need to add it to you .bashrc or .zshrc:\n")
    #    print("export C_INCLUDE_PATH=${{C_INCLUDE_PATH}}:{}".format(os.path.join(package_root, "bmf", "include")))
    #    print("export CPLUS_INCLUDE_PATH=${{CPLUS_INCLUDE_PATH}}:{}".format(os.path.join(package_root, "bmf", "include")))
    #    print(f"export LIBRARY_PATH=${{LIBRARY_PATH}}:{extensions_dir}")

    libs_found, libs_path = find_file(os.path.join("bmf", "lib"))
    include_found, include_path = find_file(os.path.join("bmf", "include"))
    if libs_found and include_found:
        print("please set environments to find BMF libraries, maybe you need to add it to you .bashrc or .zshrc:\n")
        print(f"export C_INCLUDE_PATH=${{C_INCLUDE_PATH}}:{include_path}")
        print(f"export CPLUS_INCLUDE_PATH=${{CPLUS_INCLUDE_PATH}}:{include_path}")
        print(f"export LIBRARY_PATH=${{LIBRARY_PATH}}:{libs_path}")
        print(f"export LD_LIBRARY_PATH=${{LD_LIBRARY_PATH}}:{libs_path}")


#def cpp_restore():
#    if len(sys.argv) < 2:
#        raise Exception("package name must be passed")
#    package_name = __package__
#    found, package_path = find_file(package_name.replace('.', os.sep))
#    package_root = PurePath(package_path).parent.parent.parent
#    if found:
#        extensions_dir = package_root / (sys.argv[1]+".libs")
#        for file_glob in ["bmf_module_sdk", "engine", "hmp"]:
#            for lib_path in glob.glob(f"{extensions_dir}{os.sep}*{file_glob}*"):
#                if os.path.islink(lib_path):
#                    os.unlink(lib_path)
