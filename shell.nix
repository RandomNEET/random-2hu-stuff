# save this as shell.nix
{
  pkgs ? import <nixpkgs> { },
}:

pkgs.mkShell {
  packages = [
    pkgs.nodejs
    pkgs.sqlite
    pkgs.sqlitebrowser
    pkgs.python313
  ];
  shellHook = ''
    export NPM_CONFIG_CACHE=$PWD/.npm
    if [ ! -d .venv ]; then
      python -m venv .venv
    fi
    source .venv/bin/activate
  '';
}
