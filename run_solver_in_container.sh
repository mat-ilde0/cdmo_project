#!/bin/bash

MODEL_FILE=$1
DATA_FILE=$2
SOLVER=${3:-Gecode}

docker exec -it cdmo_solvers_container \
  minizinc /app/$MODEL_FILE /app/$DATA_FILE --solver $SOLVER