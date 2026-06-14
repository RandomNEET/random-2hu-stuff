{
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
  inputs.systems.url = "github:nix-systems/default";
  inputs.flake-utils = {
    url = "github:numtide/flake-utils";
    inputs.systems.follows = "systems";
  };
  inputs.treefmt-nix = {
    url = "github:numtide/treefmt-nix";
    inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs =
    {
      nixpkgs,
      flake-utils,
      treefmt-nix,
      ...
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        pythonEnv = pkgs.python313.withPackages (ps: [
          ps.requests
          ps.yt-dlp
          ps.openpyxl
        ]);
        pyWrapper = pkgs.runCommand "py-wrapper" { } ''
          mkdir -p $out/bin
          ln -s ${pythonEnv}/bin/python $out/bin/py
        '';
        fmt = treefmt-nix.lib.evalModule pkgs {
          projectRootFile = "flake.nix";
          programs = {
            nixfmt.enable = true;
            shfmt.enable = true;
            isort.enable = true;
            black.enable = true;
            prettier.enable = true;
          };
        };
      in
      {
        devShells.default = pkgs.mkShell {
          packages = [
            pythonEnv
            pyWrapper
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
        formatter = fmt.config.build.wrapper;
      }
    );
}
