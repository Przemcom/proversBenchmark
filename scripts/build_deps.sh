#!/bin/bash

# TODO: promopt for installation path

# bash 'strict' mode
set -euo pipefail

SPASS_LINK="http://www.spass-prover.org/download/sources/spass39.tgz"
PROVER9_LINK="https://www.cs.unm.edu/~mccune/prover9/download/LADR-2009-11A.tar.gz"

# name with extension
SPASS=$(basename ${SPASS_LINK})
PROVER9=$(basename ${PROVER9_LINK})

# paths
BUILD_DIR="provers"
SPASS_BUILD_TGZ=$BUILD_DIR/${SPASS}
PROVER9_BUILD_TAR_GZ=$BUILD_DIR/${PROVER9}
SPASS_BUILD_DIR=$BUILD_DIR/${SPASS/.*/}
PROVER9_BUILD_DIR=$BUILD_DIR/${PROVER9/.*/}

install_prover9() {
  mkdir -p "$PROVER9_BUILD_DIR"
  if [ ! -f "$PROVER9_BUILD_TAR_GZ" ]; then
    wget -q --show-progress -O $PROVER9_BUILD_TAR_GZ $PROVER9_LINK
  fi
  # prover9 unpacks to new directory, thats why unpack it to BUILD_DIR, not PROVER9_BUILD_DIR
  tar -xf $PROVER9_BUILD_TAR_GZ -C $BUILD_DIR
  (cd "$PROVER9_BUILD_DIR" && make all)
}

install_spass() {
  mkdir -p "$SPASS_BUILD_DIR"
  if [ ! -f "$SPASS_BUILD_TGZ" ]; then
    wget -q --show-progress -O $SPASS_BUILD_TGZ $SPASS_LINK
  fi
  tar -xf $SPASS_BUILD_TGZ -C $SPASS_BUILD_DIR
  (cd "$SPASS_BUILD_DIR" && make)
}

echo "Building Prover9"
install_prover9
echo "Prover9 build finished"

echo "Building SPASS"
install_spass
echo "SPASS build finished"

echo
echo "All provers build successfully!!"
