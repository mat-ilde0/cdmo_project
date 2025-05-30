# cdmo_project
The repo contains the following folders:
- `source`: contains the source code organised in folders, one for each model type, as mentioned in the project description
- `res`: the other one mentioned in the assigment descripion: "Collect all the solutions under a res folder, by creating specific sub-folders (res/CP, res/SMT, res/MIP, etc.)".
- in `papers_and_docs` will be put all the useful papers we find

### Run the docker container
Once cloned the repo follow the following steps:
0. Open a terminal inside the root folder (where the Dockerfile is placed)
1. Run `docker compose up -d --build`
2. Then, to start the container, run `docker compose up -d`.
3. Run `docker exec -it cdmo_solvers_container bash` to access a bash in the container
8. `docker-compose down` when finished  



