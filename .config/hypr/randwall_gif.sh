#/bin/bash
# swww img `find ~/Downloads/images_to_paper/| shuf -n 1` --transition-type none --transition-fps 144
image=$(find ~/images_to_paper/*.gif | shuf -n 1)
lastimage=$(cat ./lastimage)
while [[ $image = $lastimage ]]
do
    image=$(find ~/images_to_paper/*.gif | shuf -n 1)
done
echo $image > ./lastimage

swww img $image --transition-type random --transition-duration 1.5 --transition-fps 144
