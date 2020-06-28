import os
import glob
import subprocess
import shutil
from conans import ConanFile, VisualStudioBuildEnvironment, tools, errors, AutoToolsBuildEnvironment
    
class ConanProject(ConanFile):
    name        = "cpython"
    version     = "3.7.8"
    _sha356_checksum = "0e25835614dc221e3ecea5831b38fa90788b5389b99b675a751414c858789ab0"
    url         = "https://github.com/kwallner/conan-cpython"
    license     = "Python Software Foundation License Version 2"
    description = "Python Programming Language Version 3"
    settings = "os", "arch", "compiler"
    generators  = "txt"
    options = { "with_tkinter" : [False,True] }
    default_options = { "with_tkinter" : False }

    def configure(self):
        if self.settings.os == "Windows":
            if self.settings.compiler != "Visual Studio" or self.settings.compiler.version != "15":
                raise errors.ConanInvalidConfiguration("Compiler is not supported.")

    def system_requirements(self):
        if self.settings.os == "Linux":
            pack_name = self.name
            installer = tools.SystemPackageTool()
            installer.install("libffi-dev") 
    
    def source(self):
        tools.download("https://www.python.org/ftp/python/%s/Python-%s.tgz" % (self.version, self.version), "Python-%s.tgz" % self.version, sha256=self._sha356_checksum)
        tools.unzip("Python-%s.tgz" % self.version)
        if tools.os_info.is_windows:  
            with tools.chdir(os.path.join("Python-%s" % self.version, "PCBuild")):
                if self.options.with_tkinter:
                    self.run("get_externals.bat --tkinter-src")
                else:
                    self.run("get_externals.bat")
            if self.options.with_tkinter:
                with tools.chdir(os.path.join("Python-%s" % self.version, "externals")):
                    for filename in glob.glob(os.path.join("**", "X.h"), recursive=True):
                        tools.replace_in_file(filename, '''#ifndef X_H''', '''
#include <windows.h>
#ifndef X_H''')              
        os.remove("Python-%s.tgz" % self.version)

    def build(self):
        if self.settings.os == "Windows":
            env_build = VisualStudioBuildEnvironment(self)
            with tools.environment_append(env_build.vars):
                with tools.chdir(os.path.join("Python-%s" % self.version, "PCBuild")):
                    with tools.vcvars(self.settings):
                        if self.options.with_tkinter:
                            self.run("prepare_tcltk.bat")
                        self.run("build.bat -p x64 -d")
                        self.run("build.bat -p x64")
        else:
            with tools.chdir("Python-%s" % self.version):
                os.chmod("configure", 
                    stat.S_IRUSR |
                    stat.S_IWUSR |
                    stat.S_IXUSR |
                    stat.S_IRGRP |
                    stat.S_IWGRP |
                    stat.S_IXGRP |
                    stat.S_IROTH |
                    stat.S_IXOTH 
                    )
                atools = AutoToolsBuildEnvironment(self)
                args = [] # ["--enable-shared"] if self.options.shared else []
                atools.configure(args=args)
                atools.make()
                atools.install()
        
    def package(self):
        if self.settings.os == "Windows":
            out_folder = {"x86_64": "amd64", "x86": "win32"}.get(str(self.settings.arch))
            python_folder = os.path.join(self.build_folder, "Python-%s" % self.version)
            pcbuild_folder = os.path.join(python_folder, "PCBuild", out_folder)
            pc_folder = os.path.join(python_folder, "PC")
            self.copy(pattern="*.dll", dst="bin", src=pcbuild_folder, keep_path=False)
            self.copy(pattern="*.exe", dst="bin", src=pcbuild_folder, keep_path=False)
            self.copy(pattern="*.lib", dst="libs", src=pcbuild_folder, keep_path=False)
            self.copy(pattern="*.pyd", dst="DLLs", src=pcbuild_folder, keep_path=False)
            shutil.copytree(os.path.join(self.build_folder, "Python-%s" % self.version, "Include"), os.path.join(self.package_folder, "include"))
            self.copy(pattern="*.h", dst="include", src=pc_folder, keep_path=False)
            shutil.copytree(os.path.join(self.build_folder, "Python-%s" % self.version, "Lib"), os.path.join(self.package_folder, "Lib"))
            self.copy(pattern="LICENSE", dst=".", src=python_folder, keep_path=False)
            if self.options.with_tkinter:
                from distutils.dir_util import copy_tree
                copy_tree(os.path.join(self.build_folder, "Python-%s" % self.version, "externals", "tcltk-8.6.9.0", "amd64"), self.package_folder)
        # Remove python compiled files
        for filename in glob.glob(os.path.join(self.package_folder, "**", "*.pyc"), recursive=True):
            os.remove(filename)
        for filename in glob.glob(os.path.join(self.package_folder, "**", "__pycache__"), recursive=True):
            os.rmdir(filename)

    def package_id(self):
        del self.info.settings.compiler
        
    def package_info(self):
        self.cpp_info.includedirs = ['include']
        self.cpp_info.libdirs = ['libs']
        self.cpp_info.bindirs = ['bin']
