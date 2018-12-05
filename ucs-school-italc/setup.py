import os
import subprocess
import sipconfig
from PyQt5 import QtCore

sip_inc_dir = '/usr/share/sip/PyQt5'
qt_inc_dir = '/usr/include/x86_64-linux-gnu/qt5'
veyon_inc_dir = os.path.join(os.getcwd(), 'libveyon')
build_file = 'italc.sbf'

config = sipconfig.Configuration()

subprocess.call(
    [config.sip_bin, '-c', '.', '-b', build_file, '-I', sip_inc_dir] +
    QtCore.PYQT_CONFIGURATION['sip_flags'].split() +
    ['italc.sip']
)

installs = [
    ['italc.sip', '/usr/share/sip/italc'],
]

makefile = sipconfig.SIPModuleMakefile(config, build_file, installs=installs)
extraFlags = '-std=c++11 -I{0} -I{0}/QtCore -I{0}/QtGui'.format(qt_inc_dir)
makefile.extra_cflags = [extraFlags]
makefile.extra_cxxflags = [extraFlags]
makefile.extra_include_dirs.extend(['/usr/include', '/usr/include/Qca-qt5/QtCrypto', veyon_inc_dir])
makefile.extra_libs = ['ItalcCore']
makefile.generate()
