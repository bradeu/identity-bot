{ pkgs }: {
  deps = [
    pkgs.zip
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.python311Packages.setuptools
    pkgs.python311Packages.wheel
    pkgs.redis
    pkgs.rsync
    pkgs.nodejs
    pkgs.lsof
    pkgs.k6
  ];
}