{
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
  inputs.systems.url = "github:nix-systems/default";
  inputs.flake-utils = {
    url = "github:numtide/flake-utils";
    inputs.systems.follows = "systems";
  };

  outputs =
    { nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        pythonEnv = pkgs.python313.withPackages (ps: [
          ps.requests
          ps.yt-dlp
          ps.openpyxl
        ]);
      in
      {
        devShells.default = pkgs.mkShell {
          packages = [
            pythonEnv
            pkgs.nodejs
            pkgs.sqlite
            pkgs.sqlitebrowser
            pkgs.deno
            pkgs.dolt
          ];
          shellHook = ''
            export PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
          '';
        };
      }
    );
}
