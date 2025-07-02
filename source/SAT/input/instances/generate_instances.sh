#!/bin/bash

# Create instances with even n from 4 up to 50 (adjust max as you want)
for n in {4..50..2}
do
  echo $n > instances${n}.txt
done
