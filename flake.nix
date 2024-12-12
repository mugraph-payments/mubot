{
  description = "A Muchat and SimpleX Chat compatible AI bot that connects to your Ollama instance and chats with you.";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-compat.url = "github:nix-community/flake-compat";
    flake-utils.url = "github:numtide/flake-utils";
    poetry2nix.url = "github:nix-community/poetry2nix";
  };

  outputs =
    {
      nixpkgs,
      poetry2nix,
      flake-utils,
      ...
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        inherit (builtins) attrValues;

        pkgs = import nixpkgs {
          inherit system;
          overlays = [ poetry2nix.overlays.default ];
        };
        inherit (pkgs.poetry2nix) mkPoetryApplication;

        mubot = mkPoetryApplication {
          projectDir = ./.;
          preferWheels = true;
          overrides = pkgs.poetry2nix.overrides.withDefaults (
            _: _: {
            }
          );
        };

        scripts = with pkgs; {
          run = writeShellApplication {
            name = "mubot";
            runtimeInputs = [ mubot.dependencyEnv ];
            text = ''
              # shellcheck disable=SC2068
              PYTHONPATH=".:$PYTHONPATH" python -m mubot $@
            '';
          };

          lint = writeShellApplication {
            name = "mubot-lint";
            runtimeInputs = [ mubot.dependencyEnv ];
            text = ./scripts/lint.sh;
          };
        };
      in
      {
        packages.default = mubot;

        devShells.default =
          with pkgs;
          mkShell {
            name = "mubot";

            inputsFrom = [
              mubot
            ];

            packages = [
              (attrValues scripts)
              poetry
            ];
          };
      }
    );
}
