#!/usr/bin/env bash

sleep 3

> square.out

while IFS= read -r x || [[ -n "$line" ]]; do
    echo $(($x**2)) >> square.out
done < "square.in"
