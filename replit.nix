{pkgs}: {
  deps = [
    pkgs.hdf5
    pkgs.rustc
    pkgs.pkg-config
    pkgs.openssl
    pkgs.libiconv
    pkgs.cargo
    pkgs.pandoc
    pkgs.libyaml
    pkgs.tesseract
    pkgs.poppler_utils
    pkgs.imagemagickBig
    pkgs.ffmpeg-full
    pkgs.glibcLocales
    pkgs.zlib
    pkgs.tk
    pkgs.tcl
    pkgs.openjpeg
    pkgs.libxcrypt
    pkgs.libwebp
    pkgs.libtiff
    pkgs.libjpeg
    pkgs.libimagequant
    pkgs.lcms2
    pkgs.freetype
  ];
}
