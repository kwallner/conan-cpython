import os
import glob
import subprocess
import shutil
from conans import ConanFile, VisualStudioBuildEnvironment, tools, errors, AutoToolsBuildEnvironment
    
class ConanProject(ConanFile):
    name        = "cpython"
    version     = "3.7.7"
    url         = "https://github.com/kwallner/conan-cpython"
    license     = "Python Software Foundation License Version 2"
    description = "Python Programming Language Version 3"
    settings = "os", "arch", "compiler"
    generators  = "txt"
    @property
    def python_interpreter(self):
        return "bin\\python.exe" if self.settings.os == "Windows" else "./bin/python3"

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
        tools.download("https://www.python.org/ftp/python/%s/Python-%s.tgz" % (self.version, self.version), "Python-%s.tgz" % self.version, sha256="8c8be91cd2648a1a0c251f04ea0bb4c2a5570feb9c45eaaa2241c785585b475a")
        tools.unzip("Python-%s.tgz" % self.version)
        if tools.os_info.is_windows:  
            with tools.chdir(os.path.join("Python-%s" % self.version, "PCBuild")):
                self.run("get_externals.bat")
        os.remove("Python-%s.tgz" % self.version)

    def build(self):
        if self.settings.os == "Windows":
            env_build = VisualStudioBuildEnvironment(self)
            with tools.environment_append(env_build.vars):
                with tools.chdir(os.path.join("Python-%s" % self.version, "PCBuild")):
                    vcvars = tools.vcvars_command(self.settings)
                    self.run("%s && cmd /C build.bat -p x64 -d" % vcvars)
                    self.run("%s && cmd /C build.bat -p x64" % vcvars)
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
            pcbuild_folder = os.path.join(self.build_folder, "Python-%s" % self.version, "PCBuild", out_folder)
            pc_folder = os.path.join(self.build_folder, "Python-%s" % self.version, "PC")
            self.copy(pattern="*.dll", dst="bin", src=pcbuild_folder, keep_path=False)
            self.copy(pattern="*.exe", dst="bin", src=pcbuild_folder, keep_path=False)
            self.copy(pattern="*.lib", dst="libs", src=pcbuild_folder, keep_path=False)
            self.copy(pattern="*.pyd", dst="DLLs", src=pcbuild_folder, keep_path=False)
            shutil.copytree(os.path.join(self.build_folder, "Python-%s" % self.version, "Include"), os.path.join(self.package_folder, "include"))
            self.copy(pattern="*.h", dst="include", src=pc_folder, keep_path=False)
            shutil.copytree(os.path.join(self.build_folder, "Python-%s" % self.version, "Lib"), os.path.join(self.package_folder, "Lib"))
            self.copy(pattern="LICENSE", dst=".", src=pcbuild_folder, keep_path=False)
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
