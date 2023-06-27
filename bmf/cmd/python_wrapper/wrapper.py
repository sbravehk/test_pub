#!/usr/bin/env python

import os
import subprocess
import sys
import site;

def main():
    args = sys.argv[1:]

    exe_path = ""
    exe_found = False
    for package_root in site.getsitepackages():
        # Find the path of the real executable.
        exe_path = os.path.join(package_root, "bmf", "bin", os.path.basename(__file__))

        if not os.path.exists(exe_path):
            continue
        exe_found=True

    if exe_found:
        # Execute it with all command line arguments.
        subprocess.call([exe_path] + args)
    else:
        print("cannot find {}".format(os.path.basename(__file__)))
        exit(1)

if __name__ == '__main__':
    main()

