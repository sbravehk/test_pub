import os
import re
import glob
import ctypes
import platform
import subprocess
import sys
import sysconfig
import shutil
from pathlib import Path

from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext

# ref: https://github.com/pybind/cmake_example

# Convert distutils Windows platform specifiers to CMake -A arguments
PLAT_TO_CMAKE = {
    "win32": "Win32",
    "win-amd64": "x64",
    "win-arm32": "ARM",
    "win-arm64": "ARM64",
}

package_name="BabitMF"
package_version="0.0.4"
build_temp=Path("build") / "temp"

if "DEVICE" in os.environ and os.environ["DEVICE"] == "gpu":
    package_name="BabitMF-GPU"


# A CMakeExtension needs a sourcedir instead of a file list.
# The name must be the _single_ output extension from the CMake build.
# If you need multiple extensions, see scikit-build.
class CMakeExtension(Extension):
    def __init__(self, name: str, sourcedir: str = "") -> None:
        super().__init__(name, sources=[])
        self.sourcedir = os.fspath(Path(sourcedir).resolve())


class CMakeBuild(build_ext):
    def build_extension(self, ext: CMakeExtension) -> None:
        # Must be in this form due to bug in .resolve() only fixed in Python 3.10+
        ext_fullpath = Path.cwd() / self.get_ext_fullpath(ext.name)
        extdir = ext_fullpath.parent.resolve()

        # Using this requires trailing slash for auto-detection & inclusion of
        # auxiliary "native" libs

        debug = int(os.environ.get("DEBUG", 0)) if self.debug is None else self.debug
        cfg = "Debug" if debug else "Release"

        # CMake lets you override the generator - we need to check this.
        # Can be set with Conda-Build, for example.
        cmake_generator = os.environ.get("CMAKE_GENERATOR", "")

        sha = os.environ.get("GIT_SHA")
        short_sha = sha[:7]

        # Set Python_EXECUTABLE instead if you use PYBIND11_FINDPYTHON
        # EXAMPLE_VERSION_INFO shows you how to pass a value into the C++ code
        # from Python.
        cmake_args = [
            f"-DPYTHON_EXECUTABLE={sys.executable}",
            f"-DCMAKE_BUILD_TYPE={cfg}",  # not used on MSVC, but no harm
            f"-DBMF_ENABLE_TEST=OFF",
            f"-DPYTHON_INCLUDE_DIR={sysconfig.get_path('include')}",
            f"-DPYTHON_LIBRARY={sysconfig.get_config_var('LIBDIR')}",
            f"-DBMF_PYENV={'{}.{}'.format(sys.version_info.major, sys.version_info.minor)}",
            f"-DBMF_BUILD_VERSION={package_version}",
            f"-DBMF_BUILD_COMMIT={short_sha}",
        ]

        build_args = []
        # Adding CMake arguments set as environment variable
        # (needed e.g. to build for ARM OSx on conda-forge)
        if "CMAKE_ARGS" in os.environ:
            cmake_args += [item for item in os.environ["CMAKE_ARGS"].split(" ") if item]

        # In this example, we pass in the version to C++. You might not need to.
        cmake_args += [f"-DEXAMPLE_VERSION_INFO={self.distribution.get_version()}"]

        if self.compiler.compiler_type != "msvc":
            # Using Ninja-build since it a) is available as a wheel and b)
            # multithreads automatically. MSVC would require all variables be
            # exported for Ninja to pick it up, which is a little tricky to do.
            # Users can override the generator with CMAKE_GENERATOR in CMake
            # 3.15+.
            if not cmake_generator or cmake_generator == "Ninja":
                try:
                    import ninja

                    ninja_executable_path = Path(ninja.BIN_DIR) / "ninja"
                    cmake_args += [
                        "-GNinja",
                        f"-DCMAKE_MAKE_PROGRAM:FILEPATH={ninja_executable_path}",
                    ]
                except ImportError:
                    pass

        else:
            # Single config generators are handled "normally"
            single_config = any(x in cmake_generator for x in {"NMake", "Ninja"})

            # CMake allows an arch-in-generator style for backward compatibility
            contains_arch = any(x in cmake_generator for x in {"ARM", "Win64"})

            # Specify the arch if using MSVC generator, but only if it doesn't
            # contain a backward-compatibility arch spec already in the
            # generator name.
            if not single_config and not contains_arch:
                cmake_args += ["-A", PLAT_TO_CMAKE[self.plat_name]]

            # Multi-config generators have a different way to specify configs
            if not single_config:
                cmake_args += [
                    f"-DCMAKE_ARCHIVE_OUTPUT_DIRECTORY_{cfg.upper()}={extdir}{os.sep}lib"
                ]
                build_args += ["--config", cfg]

        if sys.platform.startswith("darwin"):
            # Cross-compile support for macOS - respect ARCHFLAGS if set
            archs = re.findall(r"-arch (\S+)", os.environ.get("ARCHFLAGS", ""))
            if archs:
                cmake_args += ["-DCMAKE_OSX_ARCHITECTURES={}".format(";".join(archs))]
            cmake_args += ["-DCMAKE_OSX_DEPLOYMENT_TARGET=10.15"]

        # Set CMAKE_BUILD_PARALLEL_LEVEL to control the parallel build level
        # across all generators.
        if "CMAKE_BUILD_PARALLEL_LEVEL" not in os.environ:
            # self.parallel is a Python 3 only way to set parallel jobs by hand
            # using -j in the build_ext call, not supported by pip or PyPA-build.
            if hasattr(self, "parallel") and self.parallel:
                # CMake 3.12+ only.
                build_args += [f"-j{self.parallel}"]

        #build_temp = Path(self.build_temp) / ext.name
        self.build_temp = build_temp
        if not build_temp.exists():
            build_temp.mkdir(parents=True)

        print("running cmake configure:{} {} {}, cwd:{}".format("cmake", ext.sourcedir, cmake_args, build_temp))
        subprocess.run(
            ["cmake", ext.sourcedir, *cmake_args], cwd=build_temp, check=True
        )
        print("running cmake build:{} {} {} {}, cwd:{}".format("cmake", "--build", ".", build_args, build_temp))
        subprocess.run(
            ["cmake", "--build", ".", *build_args], cwd=build_temp, check=True
        )

        # We have two output extensions (_bmf and _hmp), two module loaders (py_module_loader and go_module_loader),
        # builtin_modules, and their respective dependencies. _bmf and _hmp need to be installed in the bmf/lib directory.
        # The bmf_module_sdk, engine and hmp libraries that these two extensions depend on will be automatically
        # packaged into the BabitMF.libs directory by `auditwheel repair`, so there is no need to manually copy them.
        # Hower, since py_loader_module and go_loader_module are dynamically loaded through dlopen, they will be ignored
        # by `auditwheel repair`, so they need to be manually copied to the BabitMF.libs directory.

        # This CMake building support only single output, and scikit-build using pyproject.toml which is
        # a static config file. Obviously, setup.py is more convenient than pyproject.toml, so we manually copy
        # _bmf, _hmp, py_module_loader, go_module_loader and builtin_moduls before repair, instead of
        # the entire lib directory. the build directory is temporary, so we need to copy it here, instead of package_data.
        #src_dir = os.path.join(build_temp, "output", "bmf", "lib")
        #extensions_dst_dir = os.path.join(extdir, "bmf", "lib")
        #depends_dst_dir = os.path.join(extdir, package_name + ".libs") # command `auditwheel repair` store libraries into .libs
        #if not os.path.exists(extensions_dst_dir):
        #    os.mkdir(extensions_dst_dir)
        #if not os.path.exists(depends_dst_dir):
        #    os.mkdir(depends_dst_dir)

        #for lib in glob.glob(f"{src_dir}{os.sep}_*"):
        #    shutil.copy(lib, extensions_dst_dir)
        #for file_glob in ["go_loader", "py_loader", "builtin_modules"]:
        #    for lib in glob.glob(f"{src_dir}{os.sep}*{file_glob}*"):
        #        shutil.copy(lib, depends_dst_dir)
        #for file in ["BUILTIN_CONFIG.json"]:
        #   shutil.copyfile(os.path.join(src_dir, file), os.path.join(depends_dst_dir, file))

        shutil.copytree(os.path.join(build_temp, "output", "bmf", "bin"), os.path.join(extdir, "bmf", "bin"))
        shutil.copytree(os.path.join(build_temp, "output", "bmf", "lib"), os.path.join(extdir, "bmf", "lib"))
        shutil.copytree(os.path.join(build_temp, "output", "bmf", "include"), os.path.join(extdir, "bmf", "include"))



# The information here can also be placed in setup.cfg - better separation of
# logic and declaration, and simpler if you include description/version in a file.
setup(
    name=package_name,
    version=package_version,
    author="",
    author_email="",
    python_requires='>= 3.6',
    description="Babit Multimedia Framework",
    long_description=open('README.md').read(),
    url="https://github.com/BabitMF/bmf",
    install_requires=[
        "numpy >= 1.19.5"
    ],
    #zip_safe=False,
    extras_require={"test": ["pytest"]},
    packages=[
        'bmf',
        'bmf.builder',
        'bmf.cmd.python_wrapper',
        'bmf.ffmpeg_engine',
        'bmf.hml.hmp',
        'bmf.modules',
        'bmf.python_sdk',
        'bmf.server',
    ],
    ext_modules=[CMakeExtension("bmf")],
    cmdclass={"build_ext": CMakeBuild},
    entry_points={
        'console_scripts': [
           'run_bmf_graph = bmf.cmd.python_wrapper.wrapper:run_bmf_graph',
           'trace_format_log = bmf.cmd.python_wrapper.wrapper:trace_format_log',
           'module_manager = bmf.cmd.python_wrapper.wrapper:module_manager',
           "bmf_cpp_adapt = bmf.cmd.python_wrapper.wrapper:cpp_adapt",
           #"bmf_cpp_restore = bmf.cmd.python_wrapper.wrapper:cpp_restore",
        ],
    }
)
