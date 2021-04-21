# youtubetrendfastapi
description this api get us the trending videos on youtube for all the countries arround the world
the folder app contains the main code python. 
1. install the requirements via "pip install - r requirements.txt" so you can the project on local machine 
2. pull mongo docker image "docker pull mongo"
3. create new docker network for both youtube api and mongo containers "docker network inspect my-net"
4. create mongo container "docker run -it -v mongodata:/data/db --name mongodb --network my-net -d mongo"
5. create docker image via command "docker build -t youtubeapi ."
6. create youtube api container and link it with the network that we created via command "docker run -d --name youtubeapicontainer -p 80:80 --network my-net youtubeapi:latest"
