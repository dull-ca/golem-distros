{ pkgs, inputs, ... }:

let
  golem = inputs.golem.packages.${pkgs.stdenv.system};
in
{
  packages = [
    pkgs.awscli2
    pkgs.bashInteractive
    pkgs.cdrkit
    pkgs.coreutils
    pkgs.curl
    pkgs.git
    pkgs.guestfs-tools
    pkgs.libguestfs
    pkgs.libguestfs-appliance
    pkgs.qemu
    pkgs.rclone
    pkgs.secretspec
    pkgs.util-linux
  ];

  languages.python = {
    enable = true;
    venv.enable = true;
    uv = {
      enable = true;
      sync.enable = true;
    };
  };

  env = {
    GOLEM_DISTROS_GOLEMD = "${golem.golemd}/bin/golemd";

    LIBGUESTFS_PATH = "${pkgs.libguestfs-appliance}/";
    LIBGUESTFS_BACKEND = "direct";

    SECRETSPEC_PROFILE = "default";
  };

  scripts.golem-distros.exec = ''
    cd "$DEVENV_ROOT" && exec python -m golem_distros.cli.main "$@"
  '';

  enterShell = ''
    echo "golem-distros  ·  python $(python --version | cut -d' ' -f2)  ·  qemu $(qemu-img --version | head -1 | cut -d' ' -f3)"
    echo "golemd   : $GOLEM_DISTROS_GOLEMD"
    echo "run      : golem-distros list   ·   golem-distros build golem-do   ·   golem-distros --help"
  '';
}
