declare FPS_start=1
declare FPS_end=5
declare iteration=3

printf "Vehicle following:\n" >> result.txt
printf "Vehicle following:\n" >> result.csv
printf "Vehicle following:\n" >> result_min_d.csv
for (( i=$FPS_start; i<=$FPS_end; i++ ))
do
    echo $i
    printf "%s" $i >> result.csv
    printf "%s" $i >> result_min_d.csv
    for (( j=1; j<=$iteration; j++))
    do
        echo $j
        python3 ../safety-critical/vehicle_following.py $i $j
    done
    printf "\n" >> result.txt
    printf "\n" >> result.csv
    printf "\n" >> result_min_d.csv
done

printf "Cut-in:\n" >> result.txt
printf "Cut-in:\n" >> result.csv
printf "Cut-in:\n" >> result_min_d.csv
for (( i=$FPS_start; i<=$FPS_end; i++ ))
do
    echo $i
    printf "%s" $i >> result.csv
    printf "%s" $i >> result_min_d.csv
    for (( j=1; j<=$iteration; j++))
    do
        echo $j
        python3 ../safety-critical/cut-in.py $i $j
    done
    printf "\n" >> result.txt
    printf "\n" >> result.csv
    printf "\n" >> result_min_d.csv
done

printf "Cut-out:\n" >> result.txt
printf "Cut-out:\n" >> result.csv
printf "Cut-out:\n" >> result_min_d.csv
for (( i=$FPS_start; i<=$FPS_end; i++ ))
do
    echo $i
    printf "%s" $i >> result.csv
    printf "%s" $i >> result_min_d.csv
    for (( j=1; j<=$iteration; j++))
    do
        echo $j
        python3 ../safety-critical/cut-out.py $i $j
    done
    printf "\n" >> result.txt
    printf "\n" >> result.csv
    printf "\n" >> result_min_d.csv
done

