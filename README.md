# Installation Guide:
## Prerequisites:
  - Docker https://docs.docker.com/desktop/
## Step 1: Obtain an image
- Option 1: Download the image from the packages section of the About sidebar on the repository.
- Option 2: Create your own image
  - Download and extract the code.
  - Open a terminal or command prompt in the folder you've extracted the code to, and run the following command:
    - docker build -t "shooting-stars-server" .
## Step 2: Create a volume 
- A volume will serve as permanent storage where you will keep your database file. Docker instances are TEMPORARY meaning that whenever you shut down the program, it wipes all data you saved and starts from scratch when it starts up. Volumes will serve as our permanent storage that you can map to your docker instance. You can use the following command:
- docker volume create database-volume
## Step 3: Run your docker image
- On your terminal or command prompt, run the following:
  - docker run -p [your host comptuers port]:[port environment variable] -mount source=[your volume name],target=[your database folder] shooting-stars-server
    - e.g. docker run -p 8080:80 -mount source=database-volume,target=/var/www/html/database shooting-stars-server
    - to pass environment variables, you need to use the "-e" flag BEFORE the name of the image for each of your variables you want to set followed by your variablen names
      - e.g. docker run -p 8080:1234 -mount source=database-volume,target=/var/www/html/database -e PORT=1234 -e DATABASE=/database/database.db -e PASSWORD=TRUE shooting-stars-server
      - e.g. docker run -p 80:80 -mount source=database-volume,target=/var/www/html/database -e DATABASE=/home/username/database/mydata.db shooting-stars-server
- If you don't know what you want to use, I'd recommend the following:
  - docker run -p 80:80 source=database-volume,target=/var/www/html/database shooting-stars-server


# Environment Variables
## PORT 
- What port you want to use for your docker container. NOTE: Only exposes the port within your docker container's network.
- Must use -p in your docker run command to expose it map it to a port on your computer. You will most likely not need to change this variable.
- Default: 80
## DATABASE 
- Full path to your sqlite database file. e.g /my/database/patah/mydatabase.db. NOTE: unless you mount a drive to that file path, your database file will be wiped on program exit.
- Default: /var/www/html/database/main.db