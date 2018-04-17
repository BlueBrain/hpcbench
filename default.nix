with import <BBPpkgs> {};
{
  hpcbench = python3Packages.hpcbench.overrideDerivation (oldAttr: rec {
    name = "hpcbench-DEV_ENV";
    src = ./.;
  });
}
