#### Currently only for local dev and general instructions on deployment to a server by ssh, no ref to the contents of the project
 TODO - when django-config is merged = say which env file and vars should be configed both in local and in deploy

# Local Setup
### Setup for development
1. Python virtual environment:   
We are using poetry to manage the projects dependencies.   
   **Install Poetry** - https://python-poetry.org/docs/#installation

2. Install dependencies:    
enter projects directory and install dependencies using Poetry. Poetry will look for pyproject.toml file
    ```
    cd Mindtools
    poetry install
    ```
   And enter the virtual env created by Poetry:
   ```
   poetry shell
   ```

4. Database:
   You can use the docker compose command:
    ```
    docker compose start postgres
    ```
   * Now you can migrate the data:
   ```   
   python manage.py migrate   
   ```
5. Setup Frontend requirements
   While at the root directory of the project
   ```
   nvm use
   npm install bower
   bower install
   npm install --prefix ./staticfiles/lib/ jsplumb@1.7.9
   mv ./staticfiles/lib/node_modules/jsplumb/ ./staticfiles/lib/jsplumb/
   rm ./staticfiles/lib/package.json ./staticfiles/lib/package-lock.json ./staticfiles/lib/node_modules/.package-lock.json
   rmdir ./staticfiles/lib/node_modules/
   ```
6. Create a superuser for yourself to start working
    ```
    python manage.py createsuperuser 
   ```
7. Start the redis server and the huey:
    ```
   docker compose start redis huey
   ```
8. Run the dev server
    ```
   python manage.py runserver
   ```


## Deployment

1. Copy files onto the server
2. Make sure you set two volumes on the server (postgresql-volume, static_data)
3. Define a .env file with all the relevant Secrets and Env Var values
4. If this isn't the first time before overwriting existing files run:
   ```
      docker-compose -f ./docker-compose-deploy.yml stop
   ```
5. After overwriting existing files / placing in the wanted dir run:
   ```
      docker-compose -f ./docker-compose-deploy.yml build
      docker-compose -f ./docker-compose-deploy.yml start
   ```


### CI
Depends on where you run, we support an initial github actions CI out of the box -declared [here](./.github/workflows/ci.yml)